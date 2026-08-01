"""Tests for the release version-consistency guard (#32).

The guard exists because releases 0.3.9-0.3.11 bumped only pyproject.toml,
leaving manifest.json at 0.3.8. The published Claude Desktop extension kept
installing 0.3.8 -- which predates the 0.3.10 Accessibility consent prompt --
so users had no update path to the version that could request the permission.

The regression test that matters is `test_catches_the_historical_drift`: it
reconstructs the exact 0.3.11 tree and asserts the guard would have blocked
that release.
"""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSIONED_FILES = (
    "pyproject.toml",
    "uv.lock",
    "manifest.json",
    "package.json",
    "server.json",
)


def _load_module():
    """Load scripts/check_versions.py, which is not an installed package."""
    path = REPO_ROOT / "scripts" / "check_versions.py"
    spec = importlib.util.spec_from_file_location("check_versions", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_versions = _load_module()


@pytest.fixture
def repo(tmp_path):
    """A throwaway copy of the repo's version-bearing files."""
    for filename in VERSIONED_FILES:
        shutil.copy(REPO_ROOT / filename, tmp_path / filename)
    return tmp_path


def _set_json_version(root: Path, filename: str, version: str) -> None:
    data = json.loads((root / filename).read_text())
    data["version"] = version
    for package in data.get("packages", []):
        package["version"] = version
    (root / filename).write_text(json.dumps(data, indent=2))


@pytest.mark.unit
class TestCollectVersions:
    """Tests for version extraction."""

    def test_collects_every_declared_version(self, repo):
        """All five files contribute, and server.json contributes twice."""
        versions = check_versions.collect_versions(repo)

        assert set(versions) == {
            "pyproject.toml:project.version",
            "uv.lock:macos-mcp",
            "manifest.json:version",
            "package.json:version",
            "server.json:version",
            "server.json:packages[0].version",
        }

    def test_missing_version_field_is_an_error(self, repo):
        """A dropped field is as much a packaging bug as a stale value."""
        data = json.loads((repo / "manifest.json").read_text())
        del data["version"]
        (repo / "manifest.json").write_text(json.dumps(data))

        with pytest.raises(ValueError, match="manifest.json"):
            check_versions.collect_versions(repo)

    def test_missing_uv_lock_entry_is_an_error(self, repo):
        """uv.lock without a macos-mcp package means the lock is stale."""
        (repo / "uv.lock").write_text('[[package]]\nname = "click"\nversion = "8.0.0"\n')

        with pytest.raises(ValueError, match="uv.lock"):
            check_versions.collect_versions(repo)


@pytest.mark.unit
class TestCheck:
    """Tests for the pass/fail decision."""

    def test_repo_is_currently_consistent(self):
        """The real tree must stay releasable -- this guards every future bump."""
        assert check_versions.check(None, REPO_ROOT) == []

    def test_consistent_repo_matches_its_own_version(self, repo):
        versions = check_versions.collect_versions(repo)
        current = next(iter(versions.values()))

        assert check_versions.check(current, repo) == []

    def test_v_prefixed_tag_is_accepted(self, repo):
        """publish.yml passes github.ref_name, which is tag-shaped."""
        versions = check_versions.collect_versions(repo)
        current = next(iter(versions.values()))

        assert check_versions.check(f"v{current}", repo) == []

    def test_catches_the_historical_drift(self, repo):
        """Reconstruct the 0.3.11 tree; the guard must block that release.

        This is the regression test for #32.
        """
        _set_json_version(repo, "manifest.json", "0.3.8")
        _set_json_version(repo, "package.json", "0.3.5")
        _set_json_version(repo, "server.json", "0.3.6")

        problems = check_versions.check("v0.3.11", repo)

        assert problems, "the guard must reject the release that shipped #32"
        assert any("disagree" in problem for problem in problems)

    def test_catches_single_stale_file(self, repo):
        """One forgotten file is enough to fail, even if the rest agree."""
        _set_json_version(repo, "manifest.json", "0.0.1")

        assert check_versions.check(None, repo) != []

    def test_catches_consistent_repo_not_matching_tag(self, repo):
        """Internally consistent but tagged wrong is still a bad release."""
        problems = check_versions.check("v99.0.0", repo)

        assert any("99.0.0" in problem for problem in problems)


@pytest.mark.unit
class TestMainExitCodes:
    """The workflow depends on the process exit status."""

    def test_exit_zero_on_consistent_repo(self, capsys):
        assert check_versions.main(["check_versions.py"]) == 0

    def test_exit_one_on_tag_mismatch(self, capsys):
        assert check_versions.main(["check_versions.py", "v99.0.0"]) == 1

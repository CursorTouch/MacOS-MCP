"""Every module must import on its own, whichever one is reached first.

`tree.service` reads `desktop.config` and `desktop.views`, so while
`desktop/__init__.py` re-exported `Desktop` -- which runs `desktop/service.py`,
which imports the tree -- reaching the tree first found the tree half built and
raised ImportError. The shipped server never hit it because `__main__` reaches
the desktop first, and the suite never hit it because `conftest.py` imports
`macos_mcp.desktop.views` on the line above `macos_mcp.tree.views`.

That masking is the point of these tests: an import run inside the suite proves
nothing, because conftest has already initialised both packages. Each case
therefore starts a fresh interpreter.
"""

import subprocess
import sys

import pytest


@pytest.mark.unit
@pytest.mark.parametrize(
    "module",
    [
        "macos_mcp.tree.service",
        "macos_mcp.desktop.service",
        "macos_mcp.desktop.config",
        "macos_mcp.desktop.views",
    ],
)
def test_imports_first_in_a_fresh_interpreter(module):
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"importing {module} first failed:\n{result.stderr}"

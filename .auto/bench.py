"""Shared harness for the desktop-state-capture benchmark.

Used by both .auto/measure.sh (timing) and .auto/checks.sh (correctness).

Why this shape:

* It drives `Tree.get_window_wise_nodes` with a **pinned** bundle list rather
  than `Desktop.get_state()`. `get_state` scans whichever app is frontmost,
  which during an agent session is always the editor -- results would depend on
  window focus and be unreproducible. The pinned list mirrors what `get_state`
  would pass for a browser plus the system UI, so the same code path is
  exercised deterministically.
* The captured node set is byte-stable: five consecutive runs produced an
  identical fingerprint including bounding boxes. That is what makes an
  exact-equality correctness gate possible, which matters because the goal
  explicitly forbids degrading capture quality.
* Timing is noisy (~14% spread), so callers take a median of several runs.

If the target UI genuinely changes (a page is scrolled, a different tab is
opened), the reference must be regenerated deliberately:

    uv run python .auto/bench.py --write-reference
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import macos_mcp.desktop  # noqa: F401 -- imported for its side effect: importing
# macos_mcp.tree.service directly hits a circular import via desktop.service.
from macos_mcp.tree.service import Tree

HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "reference.json"

# A browser plus the system UI: what get_state() assembles when a browser is
# frontmost. Pinned so the benchmark does not depend on focus.
SYSTEM_BUNDLES = [
    "com.apple.dock",
    "com.apple.controlcenter",
    "com.apple.systemuiserver",
    "com.apple.Spotlight",
]
TARGET_BUNDLE = "com.google.Chrome"
BUNDLES = [TARGET_BUNDLE] + SYSTEM_BUNDLES

# Below this, something is broken rather than merely slow -- fail loudly instead
# of reporting a fast, empty capture as an improvement.
MIN_EXPECTED_NODES = 50


def capture() -> tuple[float, list, list]:
    """One full capture. Returns (milliseconds, interactive nodes, scroll nodes)."""
    tree = Tree()
    started = time.perf_counter()
    interactive, scrollable, _dom = tree.get_window_wise_nodes(
        bundle_ids=BUNDLES,
        system_bundle_ids=SYSTEM_BUNDLES,
        desktop_only_bundle_ids=[],
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return elapsed_ms, interactive, scrollable


def fingerprint(interactive: list, scrollable: list) -> list[str]:
    """Canonical, order-independent description of what was captured.

    Includes geometry: a node that survives but lands in the wrong place is a
    regression too.
    """
    out = []
    for node in interactive:
        box = node.bounding_box
        out.append(
            f"I|{node.control_type}|{node.name}|"
            f"{box.left},{box.top},{box.right},{box.bottom}"
        )
    for node in scrollable:
        out.append(f"S|{getattr(node, 'control_type', '')}|{getattr(node, 'name', '')}")
    return sorted(out)


def _require_sane(interactive: list) -> None:
    if len(interactive) < MIN_EXPECTED_NODES:
        sys.exit(
            f"capture returned only {len(interactive)} interactive nodes "
            f"(expected >= {MIN_EXPECTED_NODES}). Is {TARGET_BUNDLE} running "
            "with a visible window?"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--write-reference", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--vision",
        action="store_true",
        help="benchmark the screenshot + annotation path instead of the tree walk",
    )
    args = parser.parse_args()

    if args.write_reference or args.check:
        _elapsed, interactive, scrollable = capture()
        _require_sane(interactive)
        current = fingerprint(interactive, scrollable)

        if args.write_reference:
            REFERENCE.write_text(json.dumps(current, indent=1))
            print(f"wrote {len(current)} entries to {REFERENCE.name}")
            return 0

        if not REFERENCE.exists():
            sys.exit(f"{REFERENCE} missing; run --write-reference first")
        expected = json.loads(REFERENCE.read_text())
        lost = sorted(set(expected) - set(current))
        gained = sorted(set(current) - set(expected))
        if lost or gained:
            print(f"capture changed: {len(lost)} lost, {len(gained)} gained")
            for entry in lost[:15]:
                print(f"  LOST   {entry}")
            for entry in gained[:15]:
                print(f"  GAINED {entry}")
            if len(lost) > 15 or len(gained) > 15:
                print("  ...")
            return 1
        print(f"capture unchanged: {len(current)} entries match reference")
        return 0

    if args.vision:
        # Screenshot + annotation, driven with a fixed node list so the
        # measurement isolates the vision path and does not re-time the tree
        # walk (already covered by the default mode).
        from macos_mcp.desktop.service import Desktop

        desktop = Desktop()
        _elapsed, interactive, _scroll = capture()
        _require_sane(interactive)

        timings = []
        image = None
        for _ in range(args.runs):
            started = time.perf_counter()
            image = desktop.get_annotated_screenshot(nodes=interactive)
            timings.append((time.perf_counter() - started) * 1000)
        if image is None:
            sys.exit("annotated screenshot returned None -- Screen Recording permission?")
        print(f"METRIC ms={statistics.median(timings):.1f}")
        print(f"METRIC min_ms={min(timings):.1f}")
        print(f"METRIC width={image.size[0]}")
        print(f"METRIC height={image.size[1]}")
        return 0

    # Timing mode.
    timings = []
    node_count = 0
    for _ in range(args.runs):
        elapsed_ms, interactive, scrollable = capture()
        _require_sane(interactive)
        timings.append(elapsed_ms)
        node_count = len(interactive)

    print(f"METRIC ms={statistics.median(timings):.1f}")
    print(f"METRIC min_ms={min(timings):.1f}")
    print(f"METRIC nodes={node_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

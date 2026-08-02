#!/usr/bin/env bash
# Correctness gate: capture quality must not degrade.
#
# The goal explicitly forbids trading fidelity for speed, so this compares the
# captured node set -- names, roles and bounding boxes -- against a reference
# recorded at baseline. Any node lost, moved or added fails the experiment.
#
# The capture is byte-stable across runs (verified: 5 consecutive runs produced
# an identical fingerprint), so an exact match is a fair gate rather than a
# flaky one. If the target UI genuinely changes -- a page scrolled, a tab
# switched -- regenerate the reference deliberately:
#
#     uv run python .auto/bench.py --write-reference
#
# and note in .auto/prompt.md that earlier numbers were taken against a
# different reference.
set -euo pipefail

cd "$(dirname "$0")/.."

# The unit tests guard the code paths the traversal depends on; a caching bug
# that breaks them should fail here rather than surface as a subtly wrong tree.
uv run pytest -q > /tmp/ar-checks-tests.txt 2>&1 || {
    echo "unit tests failed:"
    tail -25 /tmp/ar-checks-tests.txt
    exit 1
}

uv run python .auto/bench.py --check

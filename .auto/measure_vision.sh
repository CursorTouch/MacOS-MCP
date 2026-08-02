#!/usr/bin/env bash
# Screenshot + annotation benchmark (the use_vision=True path).
#
# Driven with a fixed node list so it isolates the vision cost rather than
# re-timing the tree walk, which .auto/measure.sh already covers. Lower is
# better. Exits non-zero before printing a metric if the capture fails.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python .auto/bench.py --vision --runs 5 > /tmp/ar-vision.txt 2>&1 || {
    echo "vision benchmark failed:"; tail -20 /tmp/ar-vision.txt; exit 1
}
grep '^METRIC ' /tmp/ar-vision.txt

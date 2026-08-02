#!/usr/bin/env bash
# Desktop-state capture benchmark.
#
# Median of 5 full captures of a browser window plus the system UI, driven
# through the real Tree.get_window_wise_nodes path. Lower is better.
#
# Exits non-zero (before printing any METRIC) if the workload is broken --
# Chrome not running, no visible window, or an implausibly small capture --
# so a fast-but-empty result can never be mistaken for an improvement.
set -euo pipefail

cd "$(dirname "$0")/.."

uv run python .auto/bench.py --runs 5 > /tmp/ar-desktop-state.txt 2>&1 || {
    echo "benchmark failed:"
    tail -20 /tmp/ar-desktop-state.txt
    exit 1
}

grep '^METRIC ' /tmp/ar-desktop-state.txt

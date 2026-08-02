# Autoresearch: cut desktop-state capture time

## Objective

Minimise the wall time of a desktop-state capture **without losing any capture
fidelity**. Degradation is explicitly not allowed: no node may be lost, moved,
renamed or gained.

## Command

```
bash .auto/measure.sh
```

Median of 5 full captures. Prints `METRIC ms=<median>`, plus `min_ms` and
`nodes` as secondary metrics.

## Metric

`ms` — **lower is better**. Baseline is around 680 ms.

Timing noise is roughly ±14% run to run, so a change under ~5% is inside the
noise. Re-run before believing anything small, and prefer changes with a
mechanistic explanation over ones that merely measured faster once.

## Correctness gate

`.auto/checks.sh` runs automatically after a passing benchmark. It:

1. runs the unit test suite (293 tests), then
2. compares the captured node set — role, name **and bounding box** — against
   `.auto/reference.json`.

Any lost, gained or moved node fails the experiment. This is a fair gate rather
than a flaky one: five consecutive captures produced a byte-identical
fingerprint before the session started.

If the target UI genuinely changes (page scrolled, tab switched, window moved),
regenerate the reference deliberately and note it here, because earlier numbers
were taken against the old one:

```
uv run python .auto/bench.py --write-reference
```

## Benchmark design

`Desktop.get_state()` scans whichever app is frontmost, which during an agent
session is always the editor — results would depend on window focus and be
unreproducible. The benchmark instead drives the same
`Tree.get_window_wise_nodes` path with a **pinned** bundle list: Chrome plus the
four system-UI bundles, exactly what `get_state` assembles when a browser is
frontmost.

Requires Chrome running with a visible window. The benchmark exits non-zero
before printing a metric if fewer than 50 interactive nodes come back, so a
fast-but-empty capture cannot be mistaken for a win.

## Scope

May change:

- `src/macos_mcp/ax/core.py` — attribute batching, AXValue parsing
- `src/macos_mcp/tree/service.py` — traversal, pruning, node building
- `src/macos_mcp/tree/config.py` — role sets
- `src/macos_mcp/ax/controls.py` — only if a hot path demands it

Must not change:

- `.auto/*` (except this file's log section)
- `tests/*` — the suite is part of the correctness gate; if a test must change,
  that is a signal the behaviour changed
- anything that alters captured output

## Where the time goes

`cProfile` over one capture, 0.722 s total:

| cost | detail |
|---|---|
| `GetEarlyTraversalBatch` | 738 calls, 0.552 s cumulative — the dominant path |
| `builtins.hasattr` | **6060 calls, 0.274 s self** — ~38% of total |
| `GetMultipleAttributeValues` | 894 calls, 0.270 s self |
| `_parse_ax_position` | 739 calls, 0.149 s |
| `_parse_ax_size` | 739 calls, 0.132 s |
| `builtins.isinstance` | 21573 calls, 0.072 s |

The `hasattr` figure is the striking one. `_parse_ax_position` and
`_parse_ax_size` probe PyObjC objects with `hasattr(v, "x")`,
`hasattr(v, "getValue_size_type_")` and similar before falling back to
`AXValueGetValue`. On bridge objects each probe is expensive, and the fallback
they are avoiding is the fast path.

Note this is Python-side overhead, not AX IPC wait — meaning it is genuinely
removable rather than a cost of talking to other processes.

## Ideas not yet tried

Ordered by expected value.

1. **Unpack AXValue directly instead of probing.** Call `AXValueGetValue` first
   in `_parse_ax_position`/`_parse_ax_size` and only fall back to the `hasattr`
   ladder if it fails. Targets the 0.274 s `hasattr` cost head-on.
2. **Cheaper per-value validation in `GetMultipleAttributeValues`.** 21.5 k
   `isinstance` calls and an `AXValueGetType` probe per returned value. Reorder
   so the common case (a real value) exits first.
3. **Defer geometry parsing.** Position and size are parsed for all 738
   elements, but elements pruned by role, or hidden, never need a rect. Check
   the cheap predicates before building `Rect`.
4. **Cache the bundle → running-application lookup.** `get_nodes` calls
   `GetRunningApplicationByBundleId` per bundle per capture.
5. **Reuse the thread pool / `Tree` instance** rather than constructing per
   capture, if construction shows up.
6. **Trim the phase-1 attribute list.** `AXIndex` and `AXHelp` were added for
   interactivity checks — measure whether they earn their place, but note that
   removing them changes behaviour, so the gate will catch it if they matter.
7. **Skip menu-bar traversal for system-UI bundles** that contribute nothing,
   if the gate confirms no node loss.
8. **Avoid the double fetch in `GetTraversalBatch`** (early + late again) used
   by correction helpers — only 16 calls, so small, but free.

## Log

| # | change | ms | status |
|---|---|---|---|
| — | baseline | *(pending)* | — |

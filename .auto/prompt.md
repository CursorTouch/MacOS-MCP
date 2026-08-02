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

`ms` — **lower is better**. Baseline was 695.7 ms; currently **103.6 ms**.

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

## What the profile looks like now

After experiments #2–#5 the Python-side overhead is essentially gone. Wrapping
the AX entry point shows **894 batched AX calls at ~339 us each** — that is
cross-process IPC, not Python. `cProfile` over one capture is now 0.117 s total
with nothing above 0.009 s except the AX call itself.

**Further gains require making fewer AX round-trips, or overlapping them.**
Micro-optimising Python will not move this number any more.

## The pattern that produced most of the win

Three separate functions probed a PyObjC bridge object with `hasattr`/`getattr`
*before* falling back to the correct unboxing call. On an `AXValueRef` a missing
attribute raises and unwinds through the bridge, costing ~178 us, while
`AXValueGetValue` costs ~0.8 us — about 200x cheaper. The expensive test was
guarding the cheap answer.

If you find another `hasattr(` or `getattr(` on an AX value in a hot path,
that is very likely the next win.

## Ideas not yet tried

Ordered by expected value.

1. **Parallelise the walk within one app.** The biggest remaining lever. The
   traversal is a serial stack walk and each element costs a blocking ~339 us
   round-trip; Chrome alone accounts for most of the 738 elements. Work is
   already threaded *per bundle*, but not *within* a bundle. Needs care: AX
   calls from multiple threads, and node ordering would change (the gate
   compares sorted sets, so it would **not** catch an ordering change — check
   that separately if output order matters to consumers).
2. **Traverse fewer elements.** 738 elements yield 137 nodes. Measure how many
   are pruned after being fetched, and whether a cheaper predicate could skip
   them before the batch call.
3. **Trim the phase-1 attribute list.** Nine attributes are fetched for every
   element. Fewer attributes may mean a cheaper round-trip — measure whether
   cost scales with attribute count before assuming it does. Removing one that
   is genuinely used changes behaviour, and the gate will catch it.
4. **Cache the bundle → running-application lookup**, and reuse the `Tree` /
   thread pool across captures rather than constructing per call.
5. **Skip menu-bar traversal for system-UI bundles** that contribute nothing,
   if the gate confirms no node loss.
6. **Avoid the double fetch in `GetTraversalBatch`** (early + late again) used
   by correction helpers — only 16 calls, so small, but free.
7. **Revisit the zero-area descend added in 17f46ca.** It walks subtrees under
   collapsed wrappers, which is expensive on DOM-heavy pages. A narrower rule
   (descend only when the *parent* box is non-degenerate) might recover time
   without losing the nodes it was added to rescue — the gate will verify.

## Log

| # | change | ms | status |
|---|---|---|---|
| 1 | baseline | 695.7 | keep |
| 2 | `AXValueGetValue` before `hasattr` in `_parse_ax_position`/`_parse_ax_size`; import hoisted to module level | 253.2 | keep (−63.6%) |
| 3 | `AXValueGetValue` before `getattr` in `ParseCFRange` — same trap | 178.2 | keep (−74.4%) |
| 4 | memoise the `isinstance` classification by concrete type in `GetMultipleAttributeValues` | 103.9 | keep (−85.1%) |
| 5 | materialise the children `NSArray` into a list once | 103.6 | keep — inside noise, retained for fewer bridge calls |

All experiments passed the correctness gate: 137 interactive nodes, fingerprint
identical to the reference including bounding boxes.

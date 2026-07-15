from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median, stdev
from typing import Iterable
from macos_mcp.desktop.service import Desktop
from PIL import Image
from tabulate import tabulate
import argparse
import threading
import time
import logging

DEFAULT_SCREENSHOT_NAME = "annotated_screenshot.png"

logger = logging.getLogger(__name__)

# Layers timed on every iteration, in execution order.
BASE_STEPS = ["get_windows", "get_foreground_window", "tree.get_state"]
# Extra layers timed only when use_vision=True.
VISION_STEPS = ["get_screenshot", "get_annotated_screenshot"]


@dataclass
class StepStats:
    name: str
    samples: list[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.samples)

    @property
    def total(self) -> float:
        return sum(self.samples)

    @property
    def mean(self) -> float:
        return mean(self.samples) if self.samples else 0.0

    @property
    def median(self) -> float:
        return median(self.samples) if self.samples else 0.0

    @property
    def stdev(self) -> float:
        return stdev(self.samples) if len(self.samples) > 1 else 0.0

    @property
    def min(self) -> float:
        return min(self.samples) if self.samples else 0.0

    @property
    def max(self) -> float:
        return max(self.samples) if self.samples else 0.0


@dataclass
class ProfileResult:
    iterations: int
    steps: dict[str, StepStats]
    # Per-bundle-id timing of Tree.get_nodes, populated only when
    # per_app_breakdown=True was requested. Useful for spotting which running
    # app is slow to scan, since tree.get_state fans out one scan per app.
    per_app: dict[str, StepStats] | None = None

    def as_table(self) -> str:
        return _stats_table(self.steps.values())

    def as_app_table(self, top: int = 10) -> str:
        if not self.per_app:
            return "(no per-app breakdown collected; pass per_app_breakdown=True)"
        ranked = sorted(self.per_app.values(), key=lambda s: s.mean, reverse=True)
        return _stats_table(ranked[:top], name_header="Bundle ID")


@dataclass
class VisionComparison:
    without_vision: ProfileResult
    with_vision: ProfileResult

    def as_table(self) -> str:
        rows = []
        for name in [*BASE_STEPS, "total"]:
            without = self.without_vision.steps[name]
            with_ = self.with_vision.steps[name]
            rows.append(
                [
                    name,
                    f"{without.mean * 1000:.2f}",
                    f"{with_.mean * 1000:.2f}",
                    f"{(with_.mean - without.mean) * 1000:+.2f}",
                ]
            )
        for name in VISION_STEPS:
            with_ = self.with_vision.steps[name]
            rows.append([name, "-", f"{with_.mean * 1000:.2f}", "-"])
        return tabulate(
            rows,
            headers=["Step", "Without vision (ms)", "With vision (ms)", "Delta (ms)"],
            tablefmt="github",
        )


def _stats_table(stats: Iterable[StepStats], name_header: str = "Step") -> str:
    rows = [
        [
            s.name,
            f"{s.mean * 1000:.2f}",
            f"{s.median * 1000:.2f}",
            f"{s.min * 1000:.2f}",
            f"{s.max * 1000:.2f}",
            f"{s.stdev * 1000:.2f}",
        ]
        for s in stats
    ]
    return tabulate(
        rows,
        headers=[name_header, "Mean (ms)", "Median (ms)", "Min (ms)", "Max (ms)", "Stdev (ms)"],
        tablefmt="github",
    )


def profile_desktop_state(
    iterations: int = 10,
    use_vision: bool = False,
    warmup: int = 1,
    per_app_breakdown: bool = False,
    save_screenshot_path: str | Path | None = None,
) -> ProfileResult:
    """
    Profile the speed of capturing the desktop state (`Desktop.get_state`) by
    timing each of its layers over a number of iterations:

      - get_windows            — enumerating running app windows
      - get_foreground_window  — resolving the active window
      - tree.get_state         — accessibility tree capture (usually the dominant cost)
      - get_screenshot         — raw desktop/screen capture (only with use_vision=True)
      - get_annotated_screenshot — full vision pipeline: capture + bounding box overlay

    Args:
        iterations: Number of timed iterations to run.
        use_vision: Whether to also profile screenshot capture and annotation.
        warmup: Number of untimed warmup iterations to run first (lets caches settle).
        per_app_breakdown: Whether to additionally time each app's accessibility
            tree scan individually (tree.get_state fans out one scan per running
            app), surfaced via ProfileResult.per_app / as_app_table().
        save_screenshot_path: When set (implies use_vision), saves the last
            iteration's annotated screenshot to this path.

    Returns:
        ProfileResult containing per-layer timing statistics.
    """
    if save_screenshot_path is not None:
        use_vision = True

    desktop = Desktop()
    step_names = list(BASE_STEPS)
    if use_vision:
        step_names.extend(VISION_STEPS)
    step_names.append("total")
    steps = {name: StepStats(name=name) for name in step_names}

    per_app: dict[str, StepStats] | None = None
    restore = None
    if per_app_breakdown:
        per_app = {}
        restore = _instrument_per_app(desktop, per_app)
    try:
        for _ in range(warmup):
            _run_iteration(desktop, use_vision, steps=None)

        last_screenshot = None
        for i in range(iterations):
            last_screenshot = _run_iteration(
                desktop, use_vision, steps=steps, capture_screenshot=save_screenshot_path is not None
            )
            logger.debug("Completed iteration %d/%d", i + 1, iterations)

        if save_screenshot_path is not None and isinstance(last_screenshot, Image.Image):
            last_screenshot.save(save_screenshot_path)
            logger.info("Saved annotated screenshot to %s", save_screenshot_path)
    finally:
        if restore is not None:
            restore()

    return ProfileResult(iterations=iterations, steps=steps, per_app=per_app)


def compare_vision(
    iterations: int = 10,
    warmup: int = 1,
) -> VisionComparison:
    """
    Profile desktop state capture with and without vision (screenshot + annotation)
    so the overhead vision adds on top of the base (windows/foreground/tree) layers
    is directly visible.

    Args:
        iterations: Number of timed iterations per mode.
        warmup: Number of untimed warmup iterations per mode.

    Returns:
        VisionComparison with both ProfileResults and a side-by-side delta table.
    """
    without_vision = profile_desktop_state(
        iterations=iterations, use_vision=False, warmup=warmup
    )
    with_vision = profile_desktop_state(
        iterations=iterations, use_vision=True, warmup=warmup
    )
    return VisionComparison(without_vision=without_vision, with_vision=with_vision)


def _instrument_per_app(desktop: Desktop, per_app: dict[str, StepStats]):
    """
    Wrap Tree.get_nodes on this instance so each per-app accessibility scan is
    timed individually. get_nodes runs concurrently across apps on a shared
    thread pool, so a lock guards the shared per_app dict.
    """
    tree = desktop.tree
    original_get_nodes = tree.get_nodes
    lock = threading.Lock()

    def timed_get_nodes(bundle_id: str, is_browser: bool, desktop_only: bool = False):
        start = time.perf_counter()
        result = original_get_nodes(bundle_id, is_browser, desktop_only)
        elapsed = time.perf_counter() - start
        with lock:
            per_app.setdefault(bundle_id, StepStats(name=bundle_id)).samples.append(elapsed)
        return result

    tree.get_nodes = timed_get_nodes

    def restore() -> None:
        del tree.get_nodes

    return restore


def _run_iteration(
    desktop: Desktop,
    use_vision: bool,
    steps: dict[str, StepStats] | None,
    capture_screenshot: bool = False,
):
    start = time.perf_counter()

    t0 = time.perf_counter()
    windows = desktop.get_windows()
    t1 = time.perf_counter()

    active_window = desktop.get_foreground_window()
    t2 = time.perf_counter()

    tree_state = desktop.tree.get_state(active_window=active_window)
    t3 = time.perf_counter()

    t4 = t5 = t3
    annotated: Image.Image | bytes | None = None
    if use_vision:
        desktop.get_screenshot()
        t4 = time.perf_counter()
        annotated = desktop.get_annotated_screenshot(nodes=tree_state.interactive_nodes or [])
        t5 = time.perf_counter()

    end = time.perf_counter()

    if steps is not None:
        del windows
        steps["get_windows"].samples.append(t1 - t0)
        steps["get_foreground_window"].samples.append(t2 - t1)
        steps["tree.get_state"].samples.append(t3 - t2)
        if use_vision:
            steps["get_screenshot"].samples.append(t4 - t3)
            steps["get_annotated_screenshot"].samples.append(t5 - t4)
        steps["total"].samples.append(end - start)

    return annotated if capture_screenshot else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile the speed of capturing the desktop state, layer by layer."
    )
    parser.add_argument(
        "-n", "--iterations", type=int, default=10, help="Number of timed iterations."
    )
    parser.add_argument(
        "--vision",
        action="store_true",
        help="Also profile screenshot capture and annotation.",
    )
    parser.add_argument(
        "--compare-vision",
        action="store_true",
        help="Run with and without vision and report the overhead vision adds.",
    )
    parser.add_argument(
        "--per-app",
        action="store_true",
        help="Additionally time each running app's accessibility tree scan.",
    )
    parser.add_argument(
        "--save-screenshot",
        nargs="?",
        const=DEFAULT_SCREENSHOT_NAME,
        default=None,
        metavar="PATH",
        help=(
            "Save the last iteration's annotated screenshot (implies --vision). "
            f"Defaults to ./{DEFAULT_SCREENSHOT_NAME} in the current directory "
            "if no path is given."
        ),
    )
    parser.add_argument(
        "--warmup", type=int, default=1, help="Number of untimed warmup iterations."
    )
    args = parser.parse_args()

    if args.compare_vision:
        comparison = compare_vision(iterations=args.iterations, warmup=args.warmup)
        print(f"\nVision overhead comparison ({args.iterations} iterations per mode)\n")
        print(comparison.as_table())
        return

    result = profile_desktop_state(
        iterations=args.iterations,
        use_vision=args.vision,
        warmup=args.warmup,
        per_app_breakdown=args.per_app,
        save_screenshot_path=args.save_screenshot,
    )
    print(f"\nDesktop state capture profile ({result.iterations} iterations)\n")
    print(result.as_table())
    if args.per_app:
        print("\nPer-app tree scan breakdown (slowest first)\n")
        print(result.as_app_table())
    if args.save_screenshot:
        print(f"\nAnnotated screenshot saved to {Path(args.save_screenshot).resolve()}")


if __name__ == "__main__":
    main()

"""Tests for profiling/desktop_state.py module."""

import pytest
from macos_mcp.profiling.desktop_state import (
    StepStats,
    ProfileResult,
    VisionComparison,
    profile_desktop_state,
    compare_vision,
)


@pytest.mark.unit
class TestStepStats:
    """Tests for StepStats aggregate properties."""

    def test_stats_empty(self):
        stats = StepStats(name="step")
        assert stats.count == 0
        assert stats.total == 0.0
        assert stats.mean == 0.0
        assert stats.median == 0.0
        assert stats.stdev == 0.0
        assert stats.min == 0.0
        assert stats.max == 0.0

    def test_stats_single_sample(self):
        stats = StepStats(name="step", samples=[0.5])
        assert stats.count == 1
        assert stats.mean == 0.5
        assert stats.median == 0.5
        assert stats.stdev == 0.0
        assert stats.min == 0.5
        assert stats.max == 0.5

    def test_stats_multiple_samples(self):
        stats = StepStats(name="step", samples=[1.0, 2.0, 3.0])
        assert stats.count == 3
        assert stats.total == 6.0
        assert stats.mean == 2.0
        assert stats.median == 2.0
        assert stats.min == 1.0
        assert stats.max == 3.0
        assert stats.stdev == pytest.approx(1.0)


@pytest.mark.unit
class TestProfileResult:
    """Tests for ProfileResult.as_table rendering."""

    def test_as_table_contains_step_names_and_headers(self):
        steps = {
            "get_windows": StepStats(name="get_windows", samples=[0.01, 0.02]),
            "total": StepStats(name="total", samples=[0.03, 0.04]),
        }
        result = ProfileResult(iterations=2, steps=steps)
        table = result.as_table()
        assert "get_windows" in table
        assert "total" in table
        assert "Mean (ms)" in table
        assert "Median (ms)" in table

    def test_as_table_empty_steps(self):
        result = ProfileResult(iterations=0, steps={})
        table = result.as_table()
        assert "Step" in table

    def test_as_app_table_without_breakdown(self):
        result = ProfileResult(iterations=1, steps={}, per_app=None)
        assert "per_app_breakdown=True" in result.as_app_table()

    def test_as_app_table_ranked_by_mean_descending(self):
        per_app = {
            "com.apple.fast": StepStats(name="com.apple.fast", samples=[0.01]),
            "com.apple.slow": StepStats(name="com.apple.slow", samples=[0.5]),
        }
        result = ProfileResult(iterations=1, steps={}, per_app=per_app)
        table = result.as_app_table()
        assert table.index("com.apple.slow") < table.index("com.apple.fast")

    def test_as_app_table_respects_top_limit(self):
        per_app = {
            f"bundle.{i}": StepStats(name=f"bundle.{i}", samples=[i * 0.01])
            for i in range(5)
        }
        result = ProfileResult(iterations=1, steps={}, per_app=per_app)
        table = result.as_app_table(top=2)
        assert table.count("bundle.") == 2


@pytest.mark.unit
class TestProfileDesktopState:
    """Tests for profile_desktop_state orchestration."""

    def test_profile_without_vision(self, mocker, mock_window, mock_tree_state):
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_windows",
            return_value=[mock_window],
        )
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_foreground_window",
            return_value=mock_window,
        )
        mock_tree_get_state = mocker.patch(
            "macos_mcp.tree.service.Tree.get_state", return_value=mock_tree_state
        )
        mock_screenshot = mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_annotated_screenshot"
        )

        result = profile_desktop_state(iterations=3, use_vision=False, warmup=1)

        assert result.iterations == 3
        assert set(result.steps.keys()) == {
            "get_windows",
            "get_foreground_window",
            "tree.get_state",
            "total",
        }
        for step in result.steps.values():
            assert step.count == 3
        # Warmup + timed iterations both invoke the underlying calls.
        assert mock_tree_get_state.call_count == 4
        mock_screenshot.assert_not_called()

    def test_profile_with_vision(self, mocker, mock_window, mock_tree_state):
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_windows",
            return_value=[mock_window],
        )
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_foreground_window",
            return_value=mock_window,
        )
        mocker.patch(
            "macos_mcp.tree.service.Tree.get_state", return_value=mock_tree_state
        )
        mock_raw_screenshot = mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_screenshot"
        )
        mock_annotated_screenshot = mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_annotated_screenshot"
        )

        result = profile_desktop_state(iterations=2, use_vision=True, warmup=0)

        assert "get_screenshot" in result.steps
        assert "get_annotated_screenshot" in result.steps
        assert result.steps["get_screenshot"].count == 2
        assert result.steps["get_annotated_screenshot"].count == 2
        assert mock_raw_screenshot.call_count == 2
        assert mock_annotated_screenshot.call_count == 2

    def test_profile_zero_warmup(self, mocker, mock_window, mock_tree_state):
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_windows",
            return_value=[mock_window],
        )
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_foreground_window",
            return_value=mock_window,
        )
        mock_tree_get_state = mocker.patch(
            "macos_mcp.tree.service.Tree.get_state", return_value=mock_tree_state
        )

        result = profile_desktop_state(iterations=5, use_vision=False, warmup=0)

        assert mock_tree_get_state.call_count == 5
        assert result.steps["total"].count == 5


@pytest.mark.unit
class TestPerAppBreakdown:
    """Tests for profile_desktop_state(per_app_breakdown=True)."""

    def test_per_app_breakdown_times_each_bundle(
        self, mocker, mock_window, mock_tree_state
    ):
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_windows",
            return_value=[mock_window],
        )
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_foreground_window",
            return_value=mock_window,
        )

        def fake_get_state(self, active_window=None):
            # Exercises the real get_state -> get_nodes call path so the
            # per-app instrumentation wrapper actually fires.
            self.get_nodes("com.apple.finder", False)
            self.get_nodes("com.example.app", False)
            return mock_tree_state

        mocker.patch("macos_mcp.tree.service.Tree.get_state", fake_get_state)
        mocker.patch(
            "macos_mcp.tree.service.Tree.get_nodes",
            return_value=([], [], []),
        )

        result = profile_desktop_state(
            iterations=3, use_vision=False, warmup=0, per_app_breakdown=True
        )

        assert result.per_app is not None
        assert set(result.per_app.keys()) == {"com.apple.finder", "com.example.app"}
        for stats in result.per_app.values():
            assert stats.count == 3

    def test_per_app_breakdown_none_when_not_requested(
        self, mocker, mock_window, mock_tree_state
    ):
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_windows",
            return_value=[mock_window],
        )
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_foreground_window",
            return_value=mock_window,
        )
        mocker.patch(
            "macos_mcp.tree.service.Tree.get_state", return_value=mock_tree_state
        )

        result = profile_desktop_state(iterations=2, use_vision=False, warmup=0)

        assert result.per_app is None

    def test_instrumentation_restored_after_profiling(
        self, mocker, mock_window, mock_tree_state
    ):
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_windows",
            return_value=[mock_window],
        )
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_foreground_window",
            return_value=mock_window,
        )
        mocker.patch(
            "macos_mcp.tree.service.Tree.get_state", return_value=mock_tree_state
        )

        from macos_mcp.desktop.service import Desktop

        desktop = Desktop()
        bound_before = desktop.tree.get_nodes
        # Reuse the same Desktop instance profile_desktop_state would create
        # internally by calling the private instrumentation helper directly.
        from macos_mcp.profiling.desktop_state import _instrument_per_app

        restore = _instrument_per_app(desktop, {})
        assert desktop.tree.get_nodes is not bound_before
        restore()
        assert "get_nodes" not in vars(desktop.tree)


@pytest.mark.unit
class TestCompareVision:
    """Tests for compare_vision orchestration."""

    def test_compare_vision_runs_both_modes(self, mocker, mock_window, mock_tree_state):
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_windows",
            return_value=[mock_window],
        )
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_foreground_window",
            return_value=mock_window,
        )
        mocker.patch(
            "macos_mcp.tree.service.Tree.get_state", return_value=mock_tree_state
        )
        mocker.patch("macos_mcp.profiling.desktop_state.Desktop.get_screenshot")
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_annotated_screenshot"
        )

        result = compare_vision(iterations=2, warmup=0)

        assert isinstance(result, VisionComparison)
        assert result.without_vision.steps["total"].count == 2
        assert result.with_vision.steps["total"].count == 2
        assert "get_screenshot" not in result.without_vision.steps
        assert "get_screenshot" in result.with_vision.steps

    def test_compare_vision_as_table(self, mocker, mock_window, mock_tree_state):
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_windows",
            return_value=[mock_window],
        )
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_foreground_window",
            return_value=mock_window,
        )
        mocker.patch(
            "macos_mcp.tree.service.Tree.get_state", return_value=mock_tree_state
        )
        mocker.patch("macos_mcp.profiling.desktop_state.Desktop.get_screenshot")
        mocker.patch(
            "macos_mcp.profiling.desktop_state.Desktop.get_annotated_screenshot"
        )

        result = compare_vision(iterations=1, warmup=0)
        table = result.as_table()

        assert "Without vision (ms)" in table
        assert "With vision (ms)" in table
        assert "Delta (ms)" in table
        assert "tree.get_state" in table
        assert "get_screenshot" in table

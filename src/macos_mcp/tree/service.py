from macos_mcp.tree.config import (
    INTERACTIVE_ROLES,
    SCROLLABLE_ROLES,
    WINDOW_CONTROL_SUBROLES,
    PRUNABLE_ROLES,
)
from macos_mcp.tree.views import (
    TreeState,
    TreeElementNode,
    ScrollElementNode,
    TextElementNode,
    BoundingBox,
)
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
from macos_mcp.desktop.config import BROWSER_BUNDLE_IDS, SYSTEM_UI_BUNDLE_IDS
from macos_mcp.desktop.views import Window
import macos_mcp.ax as ax
import logging

logger = logging.getLogger(__name__)

THREAD_MAX_RETRIES = 3


class Tree:
    def on_focus_changed(self, element, notification: str, pid: int) -> None:
        """
        Callback invoked by WatchDog when focus changes (FocusedUIElementChanged,
        FocusedWindowChanged, MainWindowChanged). Can be used to invalidate caches
        or trigger fresh tree reads to overcome macOS accessibility tree laziness.
        """

        logger.debug("Focus changed: notification=%s pid=%d", notification, pid)

    def get_state(self, active_window: Window | None) -> TreeState:
        FINDER_BUNDLE_ID = "com.apple.finder"
        bundle_ids: list[str] = []
        system_bundle_ids: list[str] = []
        desktop_only_bundle_ids: list[str] = []
        for bundle_id in SYSTEM_UI_BUNDLE_IDS:
            if app := ax.GetRunningApplicationByBundleId(bundle_id):
                system_bundle_ids.append(app.BundleIdentifier)
                bundle_ids.append(app.BundleIdentifier)
        if active_window:
            if app := ax.GetRunningApplicationByBundleId(active_window.bundle_id):
                ax.SetAttribute(app.Element, "AXEnhancedUserInterface", True)
            bundle_ids.append(active_window.bundle_id)
            # When a non-Finder app is active but has no visible window (e.g. minimized),
            # also scan Finder's desktop icons — but skip Finder's menu bar so we don't
            # show Finder menus while another app owns the menu bar.
            is_windowless = (
                active_window.bundle_id != FINDER_BUNDLE_ID
                and active_window.bounding_box.width == 0
                and active_window.bounding_box.height == 0
            )
            if is_windowless:
                desktop_only_bundle_ids.append(FINDER_BUNDLE_ID)

        interactive_nodes, scrollable_nodes, dom_informative_nodes = (
            self.get_window_wise_nodes(
                bundle_ids=bundle_ids,
                system_bundle_ids=system_bundle_ids,
                desktop_only_bundle_ids=desktop_only_bundle_ids,
            )
        )

        return TreeState(
            status=True,
            interactive_nodes=interactive_nodes,
            scrollable_nodes=scrollable_nodes,
            dom_informative_nodes=dom_informative_nodes,
        )

    def get_window_wise_nodes(
        self,
        bundle_ids: list[str],
        system_bundle_ids: list[str] | None = None,
        desktop_only_bundle_ids: list[str] | None = None,
    ) -> tuple[list[TreeElementNode], list[ScrollElementNode], list[TextElementNode]]:
        interactive_nodes: list[TreeElementNode] = []
        scrollable_nodes: list[ScrollElementNode] = []
        dom_informative_nodes: list[TextElementNode] = []

        if system_bundle_ids is None:
            system_bundle_ids = []
        if desktop_only_bundle_ids is None:
            desktop_only_bundle_ids = []

        task_inputs: list[tuple[str, bool, bool]] = []
        for bundle_id in bundle_ids:
            is_browser = bundle_id in BROWSER_BUNDLE_IDS
            task_inputs.append((bundle_id, is_browser, False))
        for bundle_id in desktop_only_bundle_ids:
            if bundle_id not in bundle_ids:
                is_browser = bundle_id in BROWSER_BUNDLE_IDS
                task_inputs.append((bundle_id, is_browser, True))

        with ThreadPoolExecutor() as executor:
            retry_counts: dict[str, int] = {bid: 0 for bid, _, __ in task_inputs}
            future_to_bundle_id: dict = {}
            for bid, is_browser, desktop_only in task_inputs:
                future = executor.submit(self.get_nodes, bid, is_browser, desktop_only)
                future_to_bundle_id[future] = bid

            while future_to_bundle_id:
                for future in as_completed(list(future_to_bundle_id)):
                    bundle_id = future_to_bundle_id.pop(future)
                    try:
                        result = future.result()
                        if result:
                            element_nodes, scroll_nodes, info_nodes = result
                            interactive_nodes.extend(element_nodes)
                            scrollable_nodes.extend(scroll_nodes)
                            dom_informative_nodes.extend(info_nodes)
                    except Exception as e:
                        retry_counts[bundle_id] = retry_counts.get(bundle_id, 0) + 1
                        logger.debug(
                            "Error processing bundle %s, retry %d: %s",
                            bundle_id,
                            retry_counts[bundle_id],
                            e,
                        )
                        if retry_counts[bundle_id] < THREAD_MAX_RETRIES:
                            is_browser = next(
                                (ib for b, ib, _ in task_inputs if b == bundle_id), False
                            )
                            desktop_only = next(
                                (do for b, _, do in task_inputs if b == bundle_id), False
                            )
                            new_future = executor.submit(
                                self.get_nodes, bundle_id, is_browser, desktop_only
                            )
                            future_to_bundle_id[new_future] = bundle_id
                        else:
                            logger.error(
                                "Task failed for bundle %s after %d retries. Exact error: %s",
                                bundle_id,
                                THREAD_MAX_RETRIES,
                                e,
                                exc_info=True,
                            )
        return interactive_nodes, scrollable_nodes, dom_informative_nodes

    def get_nodes(
        self, bundle_id: str, is_browser: bool, desktop_only: bool = False
    ) -> tuple[list[TreeElementNode], list[ScrollElementNode], list[TextElementNode]]:
        """
        Get interactive and scrollable nodes for an app by bundle_id.
        Tree traversal begins here: starts from each window and recurses via tree_traversal.

        Args:
            bundle_id: Application bundle identifier.
            is_browser: Whether the app is a browser.
            desktop_only: When True, skip menu bar scanning (used for Finder desktop
                          items when another app owns the menu bar).
        """
        app = ax.GetRunningApplicationByBundleId(bundle_id)
        if not app:
            return [], [], []

        # Optimization: Set a short timeout for AX messaging to prevent hanging on slow/unresponsive apps
        # Default is usually around 6 seconds; 0.5s is plenty for most well-behaved apps.
        ax.SetMessagingTimeout(app.Element, 0.5)

        app_name = app.Name or bundle_id
        interactive_nodes: list[TreeElementNode] = []
        scrollable_nodes: list[ScrollElementNode] = []
        dom_informative_nodes: list[TextElementNode] = []

        if not desktop_only:
            if menubar := app.MenuBar:
                self.tree_traversal(
                    menubar,
                    app_name,
                    interactive_nodes,
                    scrollable_nodes,
                    [],
                    is_browser=is_browser,
                )
            if extras_menubar := app.ExtrasMenuBar:
                self.tree_traversal(
                    extras_menubar,
                    app_name,
                    interactive_nodes,
                    scrollable_nodes,
                    [],
                    is_browser=is_browser,
                )
        if main_window := app.MainWindow:
            if main_window_rect := main_window.BoundingRectangle:
                main_window_bounding_box = BoundingBox.from_bounding_rectangle(
                    main_window_rect
                )
                self.tree_traversal(
                    main_window,
                    app_name,
                    interactive_nodes,
                    scrollable_nodes,
                    dom_informative_nodes,
                    main_window_bounding_box=main_window_bounding_box,
                    is_browser=is_browser,
                )
        else:
            # MainWindow is None. Distinguish three cases:
            # 1. App has visible non-minimized windows (e.g. Finder desktop) — scan them.
            # 2. All windows are minimized — skip to avoid scanning invisible content.
            # 3. App has no windows at all (e.g. Dock) — scan children as fallback.
            all_windows = app.Windows
            visible_windows = [
                w for w in all_windows
                if not ax.GetAttribute(w.Element, "AXMinimized")
            ]
            if visible_windows:
                for window in visible_windows:
                    window_rect = window.BoundingRectangle
                    window_bbox = (
                        BoundingBox.from_bounding_rectangle(window_rect)
                        if window_rect
                        else None
                    )
                    self.tree_traversal(
                        window,
                        app_name,
                        interactive_nodes,
                        scrollable_nodes,
                        dom_informative_nodes,
                        main_window_bounding_box=window_bbox,
                        is_browser=is_browser,
                    )
            elif not all_windows:
                for child in app.GetChildren():
                    self.tree_traversal(
                        child,
                        app_name,
                        interactive_nodes,
                        scrollable_nodes,
                        dom_informative_nodes,
                        is_browser=is_browser,
                    )
        return interactive_nodes, scrollable_nodes, dom_informative_nodes

    def iou_bounding_box(
        self, window_box: BoundingBox, element_box: BoundingBox
    ) -> BoundingBox:
        left = max(window_box.left, element_box.left)
        top = max(window_box.top, element_box.top)
        right = min(window_box.right, element_box.right)
        bottom = min(window_box.bottom, element_box.bottom)

        if right > left and bottom > top:
            return BoundingBox(
                left=left,
                top=top,
                right=right,
                bottom=bottom,
                width=right - left,
                height=bottom - top,
            )
        return BoundingBox(left=0, top=0, right=0, bottom=0, width=0, height=0)

    def _dom_correction(
        self,
        attrs: dict,
        interactive_nodes: list[TreeElementNode],
        window_name: str,
        main_window_bounding_box: BoundingBox | None = None,
    ):
        if attrs["role"] == "AXLink":
            children = attrs.get("children", [])
            if children:
                first_child_element = children[0]
                # Single batch call: check role and get display attrs in one IPC round-trip.
                child_attrs = ax.GetTraversalBatch(first_child_element)
                if child_attrs["role"] == "AXHeading":
                    interactive_nodes.pop()
                    if child_attrs["rect"]:
                        bounding_box = BoundingBox.from_bounding_rectangle(
                            child_attrs["rect"]
                        )
                        if main_window_bounding_box:
                            bounding_box = self.iou_bounding_box(
                                main_window_bounding_box, bounding_box
                            )
                        center = bounding_box.get_center()
                        metadata = {}
                        if child_attrs["identifier"]:
                            metadata["axidentifier"] = child_attrs["identifier"]
                        interactive_nodes.append(
                            TreeElementNode(
                                bounding_box=bounding_box,
                                center=center,
                                name=child_attrs["label"] or "",
                                control_type=child_attrs["role"] or "",
                                window_name=window_name,
                                metadata=metadata,
                            )
                        )

    def _desktop_correction(
        self,
        attrs: dict,
        interactive_nodes: list[TreeElementNode],
        window_name: str,
        main_window_bounding_box: BoundingBox | None = None,
    ):
        role = attrs["role"]
        rect = attrs["rect"]
        if role in ["AXCell", "AXGroup"]:
            children = attrs.get("children", [])
            current_element = children[0] if children else None
            found_static_text_value = None

            while current_element:
                # Optimization: Single IPC call for Role, Value, and Children to continue traversal
                batch = ax.GetMultipleAttributeValues(
                    current_element,
                    [ax.Attribute.Role, ax.Attribute.Value, ax.Attribute.Children],
                )

                if batch.get(ax.Attribute.Role) == "AXStaticText":
                    found_static_text_value = batch.get(ax.Attribute.Value) or ""
                    break

                next_children = batch.get(ax.Attribute.Children)
                current_element = next_children[0] if next_children else None

            if found_static_text_value is not None:
                node = interactive_nodes.pop()
                metadata = node.metadata
                bounding_box = BoundingBox.from_bounding_rectangle(rect)
                if main_window_bounding_box:
                    bounding_box = self.iou_bounding_box(
                        main_window_bounding_box, bounding_box
                    )
                center = bounding_box.get_center()
                interactive_nodes.append(
                    TreeElementNode(
                        bounding_box=bounding_box,
                        center=center,
                        name=found_static_text_value,
                        control_type=role,
                        window_name=window_name,
                        metadata=metadata,
                    )
                )
        elif role == "AXButton":
            subrole = attrs["subrole"]
            if subrole in WINDOW_CONTROL_SUBROLES:
                node = interactive_nodes.pop()
                metadata = node.metadata
                element_bounding_box = BoundingBox.from_bounding_rectangle(rect)
                if main_window_bounding_box:
                    element_bounding_box = self.iou_bounding_box(
                        main_window_bounding_box, element_bounding_box
                    )
                center = element_bounding_box.get_center()
                interactive_nodes.append(
                    TreeElementNode(
                        bounding_box=element_bounding_box,
                        center=center,
                        name=WINDOW_CONTROL_SUBROLES[subrole] or "",
                        control_type=role,
                        window_name=window_name,
                        metadata=metadata,
                    )
                )

    def tree_traversal(
        self,
        root_control: ax.Control,
        window_name: str,
        interactive_nodes: list[TreeElementNode],
        scrollable_nodes: list[ScrollElementNode],
        dom_informative_nodes: list[TextElementNode],
        main_window_bounding_box: BoundingBox | None = None,
        is_browser: bool = False,
    ) -> None:
        """
        Traverse the accessibility tree iteratively and collect interactive and scrollable nodes.

        Uses a two-phase attribute fetch strategy to minimise cross-process IPC cost:
          Phase 1 (every element): 8 cheap attributes — role, visibility, bounds, children.
          Phase 2 (interactive elements only, ~5-10%): 9 display/metadata attributes.
        This avoids marshalling string attributes for the ~90% of non-interactive nodes.
        """
        stack = deque([(root_control.Element, is_browser)])

        while stack:
            element, current_is_browser = stack.pop()

            # --- Phase 1: minimal batch for all elements ---
            early = ax.GetEarlyTraversalBatch(element)

            role = early["role"]
            rect = early["rect"]
            children = early["children"]

            if early["hidden"] or role in PRUNABLE_ROLES:
                continue

            if rect is None:
                for child_element in reversed(children):
                    stack.append((child_element, current_is_browser))
                continue

            is_visible = rect.width > 1 and rect.height > 1
            has_roles = (role in INTERACTIVE_ROLES) or (role == "AXImage")
            has_title_ui_element = bool(early["title_ui_element"])
            is_interactive = (
                (has_roles and early["enabled"])
                or bool(early["help"])
                or early["has_popup"]
                or has_title_ui_element
            ) and is_visible

            bounding_box = BoundingBox.from_bounding_rectangle(rect)
            if main_window_bounding_box:
                bounding_box = self.iou_bounding_box(
                    main_window_bounding_box, bounding_box
                )
                if bounding_box.width == 0 or bounding_box.height == 0:
                    continue

            if is_interactive:
                # --- Phase 2: display/metadata attributes, only for interactive elements ---
                late = ax.GetLateTraversalBatch(element)

                # Resolve TitleUIElement ref (fetched in phase 1) to its display text.
                title_ui_element_text = None
                if early["title_ui_element"] is not None:
                    ref_raw = ax.GetMultipleAttributeValues(
                        early["title_ui_element"],
                        [
                            ax.Attribute.Title,
                            ax.Attribute.Value,
                            ax.Attribute.Description,
                        ],
                    )
                    title_ui_element_text = (
                        ref_raw.get(ax.Attribute.Title)
                        or ref_raw.get(ax.Attribute.Value)
                        or ref_raw.get(ax.Attribute.Description)
                        or None
                    )

                label = late["label"] or (
                    str(title_ui_element_text) if title_ui_element_text else ""
                )
                attrs = {**early, **late, "title_ui_element": title_ui_element_text}

                center = bounding_box.get_center()
                metadata = {}

                if role == "AXTextField":
                    if placeholder := late["placeholder"]:
                        metadata["placeholder"] = placeholder
                    if value := late["value"]:
                        metadata["value"] = value

                elif role == "AXComboBox" or role == "AXTextArea":
                    if placeholder := late["placeholder"]:
                        metadata["placeholder"] = placeholder
                    if value := late["value"]:
                        metadata["value"] = value
                    if late["expanded"]:
                        metadata["expanded"] = late["expanded"]
                    if early["has_popup"]:
                        metadata["has_popup"] = early["has_popup"]

                elif role == "AXRadioButton":
                    if value := late["value"]:
                        metadata["selected"] = value

                elif role == "AXPopUpButton":
                    if title_ui_element_text:
                        metadata["title"] = title_ui_element_text

                elif role == "AXLink":
                    if url := late["url"]:
                        if url.startswith(("file://", "http://", "https://")):
                            metadata["url"] = url

                elif role == "AXImage":
                    if filename := late["filename"]:
                        metadata["filename"] = filename
                    if url := late["url"]:
                        if url.startswith(("file://", "http://", "https://")):
                            metadata["url"] = url

                if late.get("identifier"):
                    metadata["axidentifier"] = late["identifier"]

                interactive_nodes.append(
                    TreeElementNode(
                        bounding_box=bounding_box,
                        center=center,
                        name=label,
                        control_type=role,
                        window_name=window_name,
                        metadata=metadata,
                    )
                )
                if current_is_browser:
                    self._dom_correction(
                        attrs, interactive_nodes, window_name, main_window_bounding_box
                    )
                else:
                    self._desktop_correction(
                        attrs, interactive_nodes, window_name, main_window_bounding_box
                    )

            if role in SCROLLABLE_ROLES and is_visible:
                first_child = children[0] if children else None
                scroll_label = ""
                if first_child is not None:
                    child_late = ax.GetLateTraversalBatch(first_child)
                    scroll_label = child_late["label"]
                scrollable_nodes.append(
                    ScrollElementNode(
                        name=scroll_label,
                        control_type=role,
                        window_name=window_name,
                        bounding_box=bounding_box,
                        center=bounding_box.get_center(),
                    )
                )

            for child_element in reversed(children):
                stack.append((child_element, current_is_browser))

from macos_mcp.tree.config import INTERACTIVE_ACTIONS, INTERACTIVE_ROLES, CONTAINER_ROLES, SCROLLABLE_ROLES, WINDOW_CONTROL_SUBROLES
from macos_mcp.tree.views import TreeState, TreeElementNode, ScrollElementNode, TextElementNode, BoundingBox, Center
from concurrent.futures import ThreadPoolExecutor, as_completed
from macos_mcp.desktop.config import BROWSER_BUNDLE_IDS, SYSTEM_UI_BUNDLE_IDS
from macos_mcp.desktop.views import Status, Window
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
        bundle_ids: list[str] = []
        for bundle_id in SYSTEM_UI_BUNDLE_IDS:
            if app := ax.GetRunningApplicationByBundleId(bundle_id):
                bundle_ids.append(app.BundleIdentifier)
        if active_window:
            bundle_ids.append(active_window.bundle_id)

        # Get active window's rect to filter elements during tree traversal
        active_window_rect = None
        if active_window and (active_window.bounding_box.width > 0 and
                              active_window.bounding_box.height > 0):
            bbox = active_window.bounding_box
            active_window_rect = ax.Rect(
                left=bbox.left,
                top=bbox.top,
                right=bbox.right,
                bottom=bbox.bottom
            )

        interactive_nodes, scrollable_nodes, dom_informative_nodes = (
            self.get_window_wise_nodes(
                bundle_ids=bundle_ids,
                active_window_rect=active_window_rect
            )
        )

        return TreeState(
            status=True,
            interactive_nodes=interactive_nodes,
            scrollable_nodes=scrollable_nodes,
            dom_informative_nodes=dom_informative_nodes,
        )

    def get_window_wise_nodes(self, bundle_ids: list[str], active_window_rect=None) -> tuple[list[TreeElementNode], list[ScrollElementNode], list[TextElementNode]]:
        interactive_nodes: list[TreeElementNode] = []
        scrollable_nodes: list[ScrollElementNode] = []
        dom_informative_nodes: list[TextElementNode] = []

        task_inputs: list[tuple[str, bool]] = []
        for bundle_id in bundle_ids:
            is_browser = bundle_id in BROWSER_BUNDLE_IDS
            task_inputs.append((bundle_id, is_browser))

        with ThreadPoolExecutor() as executor:
            retry_counts: dict[str, int] = {bid: 0 for bid, _ in task_inputs}
            future_to_bundle_id: dict = {
                executor.submit(self.get_nodes, bid, is_browser, active_window_rect): bid
                for bid, is_browser in task_inputs
            }
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
                                (ib for b, ib in task_inputs if b == bundle_id), False
                            )
                            new_future = executor.submit(
                                self.get_nodes, bundle_id, is_browser, active_window_rect
                            )
                            future_to_bundle_id[new_future] = bundle_id
                        else:
                            logger.error(
                                "Task failed for bundle %s after %d retries",
                                bundle_id,
                                THREAD_MAX_RETRIES,
                            )
        return interactive_nodes, scrollable_nodes, dom_informative_nodes

    def get_nodes(self, bundle_id: str, is_browser: bool, window_rect=None) -> tuple[list[TreeElementNode], list[ScrollElementNode], list[TextElementNode]]:
        """
        Get interactive and scrollable nodes for an app by bundle_id.
        Tree traversal begins here: starts from each window and recurses via tree_traversal.

        Args:
            bundle_id: Application bundle identifier.
            is_browser: Whether the app is a browser.
            window_rect: Optional window bounds for filtering nodes (active window only).
        """
        app = ax.GetRunningApplicationByBundleId(bundle_id)
        if not app:
            return [], [], []
        app_name = app.Name or bundle_id
        interactive_nodes: list[TreeElementNode] = []
        scrollable_nodes: list[ScrollElementNode] = []
        dom_informative_nodes: list[TextElementNode] = []

        if menubar:=app.MenuBar:
            self.tree_traversal(menubar, app_name, interactive_nodes, scrollable_nodes, [], is_browser, window_rect)
        if extras_menubar:=app.ExtrasMenuBar:
            self.tree_traversal(extras_menubar, app_name, interactive_nodes, scrollable_nodes, [], is_browser, window_rect)
        if main_window := app.MainWindow:
            self.tree_traversal(main_window, app_name, interactive_nodes, scrollable_nodes, dom_informative_nodes, is_browser, window_rect)
        else:
            # Fallback for apps like Dock: content is under app root (e.g. AXList child)
            for child in app.GetChildren():
                self.tree_traversal(child, app_name, interactive_nodes, scrollable_nodes, dom_informative_nodes, is_browser, window_rect)
        return interactive_nodes, scrollable_nodes, dom_informative_nodes

    def _dom_correction(self, control: ax.Control, attrs: dict, interactive_nodes: list[TreeElementNode], window_name: str):
        if attrs['role'] == "AXLink":
            first_child = control.GetFirstChildControl()
            if first_child is not None and first_child.Role == "AXHeading":
                interactive_nodes.pop()
                child_attrs = ax.GetTraversalBatch(first_child.Element)
                if child_attrs['rect']:
                    bounding_box = BoundingBox.from_bounding_rectangle(child_attrs['rect'])
                    center = bounding_box.get_center()
                    metadata = {}
                    if child_attrs['identifier']:
                        metadata['axidentifier'] = child_attrs['identifier']
                    interactive_nodes.append(TreeElementNode(
                        bounding_box=bounding_box,
                        center=center,
                        name=child_attrs['label'] or "",
                        control_type=child_attrs['role'] or "",
                        window_name=window_name,
                        metadata=metadata,
                    ))

    def _desktop_correction(self, control: ax.Control, attrs: dict, interactive_nodes: list[TreeElementNode], window_name: str):
        role = attrs['role']
        rect = attrs['rect']
        if role == "AXCell":
            first_child = control.GetFirstChildControl()
            if first_child is not None and first_child.Role == "AXStaticText":
                interactive_nodes.pop()
                bounding_box = BoundingBox.from_bounding_rectangle(rect)
                center = bounding_box.get_center()
                metadata = {}
                if attrs['identifier']:
                    metadata['axidentifier'] = attrs['identifier']
                interactive_nodes.append(TreeElementNode(
                    bounding_box=bounding_box,
                    center=center,
                    name=first_child.Label or "",
                    control_type=role,
                    window_name=window_name,
                    metadata=metadata,
                ))
        elif role == "AXButton" and not attrs['label']:
            subrole = attrs['subrole']
            if subrole in WINDOW_CONTROL_SUBROLES:
                interactive_nodes.pop()
                bounding_box = BoundingBox.from_bounding_rectangle(rect)
                center = bounding_box.get_center()
                metadata = {}
                if attrs['identifier']:
                    metadata['axidentifier'] = attrs['identifier']
                interactive_nodes.append(TreeElementNode(
                    bounding_box=bounding_box,
                    center=center,
                    name=WINDOW_CONTROL_SUBROLES[subrole] or "",
                    control_type=role,
                    window_name=window_name,
                    metadata=metadata,
                ))

    def tree_traversal(self, control: ax.Control, window_name: str, interactive_nodes: list[TreeElementNode], scrollable_nodes: list[ScrollElementNode], dom_informative_nodes: list[TextElementNode], is_browser: bool, window_rect=None) -> None:
        """
        Traverse the accessibility tree and collect interactive and scrollable nodes.

        All element attributes are fetched in a single batch call per element via
        AXUIElementCopyMultipleAttributeValues, replacing the previous approach of
        making individual GetAttribute calls for each property.

        Args:
            window_rect: Optional bounding rectangle to filter elements within bounds.
        """
        attrs = ax.GetTraversalBatch(control.Element)

        rect = attrs['rect']
        if rect is None:
            for child in control.GetChildren():
                self.tree_traversal(child, window_name, interactive_nodes, scrollable_nodes, dom_informative_nodes, is_browser, window_rect)
            return

        # Check if element is within window bounds (if window_rect provided)
        if window_rect and not ax.IsElementWithinWindowBounds(rect, window_rect):
            for child in control.GetChildren():
                self.tree_traversal(child, window_name, interactive_nodes, scrollable_nodes, dom_informative_nodes, is_browser, window_rect)
            return

        role = attrs['role']
        is_visible = not attrs['hidden'] and (rect.width > 0 and rect.height > 0)
        is_enabled = attrs['enabled']
        has_help_text = bool(attrs['help'])
        has_roles = (role in INTERACTIVE_ROLES) or (role == "AXImage" and attrs['label'])
        is_interactive = ((has_roles and is_enabled) or has_help_text) and is_visible

        if is_interactive:
            bounding_box = BoundingBox.from_bounding_rectangle(rect)
            center = bounding_box.get_center()
            interactive_nodes.append(
                TreeElementNode(
                    bounding_box=bounding_box,
                    center=center,
                    name=attrs['label'],
                    control_type=role,
                    window_name=window_name,
                )
            )
            if is_browser:
                self._dom_correction(control, attrs, interactive_nodes, window_name)
            else:
                self._desktop_correction(control, attrs, interactive_nodes, window_name)

        for child in control.GetChildren():
            self.tree_traversal(child, window_name, interactive_nodes, scrollable_nodes, dom_informative_nodes, is_browser, window_rect)
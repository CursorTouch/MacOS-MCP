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

    def get_state(self,active_window: Window | None) -> TreeState:
        bundle_ids: list[str] = []
        for bundle_id in SYSTEM_UI_BUNDLE_IDS:
            if app := ax.GetRunningApplicationByBundleId(bundle_id):
                bundle_ids.append(app.BundleIdentifier)
        bundle_ids.append(active_window.bundle_id)

        interactive_nodes, scrollable_nodes, dom_informative_nodes = self.get_window_wise_nodes(bundle_ids=bundle_ids)

        return TreeState(
            status=True,
            interactive_nodes=interactive_nodes,
            scrollable_nodes=scrollable_nodes,
            dom_informative_nodes=dom_informative_nodes,
        )

    def get_window_wise_nodes(self,bundle_ids: list[str]) -> tuple[list[TreeElementNode], list[ScrollElementNode], list[TextElementNode]]:
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
                executor.submit(self.get_nodes, bid, is_browser): bid
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
                                self.get_nodes, bundle_id, is_browser
                            )
                            future_to_bundle_id[new_future] = bundle_id
                        else:
                            logger.error(
                                "Task failed for bundle %s after %d retries",
                                bundle_id,
                                THREAD_MAX_RETRIES,
                            )
        return interactive_nodes, scrollable_nodes, dom_informative_nodes

    def get_nodes(self,bundle_id: str, is_browser: bool) -> tuple[list[TreeElementNode], list[ScrollElementNode], list[TextElementNode]]:
        """
        Get interactive and scrollable nodes for an app by bundle_id.
        Tree traversal begins here: starts from each window and recurses via tree_traversal.
        """
        app = ax.GetRunningApplicationByBundleId(bundle_id)
        if not app:
            return [], [], []
        app_name = app.Name or bundle_id
        interactive_nodes: list[TreeElementNode] = []
        scrollable_nodes: list[ScrollElementNode] = []
        dom_informative_nodes: list[TextElementNode] = []

        if menubar:=app.MenuBar:
            self.tree_traversal(menubar, app_name, interactive_nodes, scrollable_nodes, [], is_browser)
        if extras_menubar:=app.ExtrasMenuBar:
            self.tree_traversal(extras_menubar, app_name, interactive_nodes, scrollable_nodes, [], is_browser)
        if main_window := app.MainWindow:
            self.tree_traversal(main_window, app_name, interactive_nodes, scrollable_nodes, dom_informative_nodes, is_browser)
        else:
            # Fallback for apps like Dock: content is under app root (e.g. AXList child)
            for child in app.GetChildren():
                self.tree_traversal(child, app_name, interactive_nodes, scrollable_nodes, dom_informative_nodes, is_browser)
        return interactive_nodes, scrollable_nodes, dom_informative_nodes

    def element_has_child_element(self, node: ax.Control, control_type: str, child_control_type: str):
        if node.Role == control_type:
            first_child = node.GetFirstChildControl()
            if first_child is None:
                return False
            return first_child.Role == child_control_type

    def _dom_correction(self,control: ax.Control, interactive_nodes: list[TreeElementNode], window_name: str):
        if self.element_has_child_element(control, "AXLink", "AXHeading"):
            interactive_nodes.pop()
            control=control.GetFirstChildControl()
            bounding_box=BoundingBox.from_bounding_rectangle(control.BoundingRectangle)
            center=bounding_box.get_center()
            metadata = {}
            if identifier := control.Identifier:
                metadata['axidentifier'] = identifier
            interactive_nodes.append(TreeElementNode(
                bounding_box=bounding_box,
                center=center,
                name=control.Label or "",
                control_type=control.Role or "",
                window_name=window_name,
                metadata=metadata,
            ))

    def _desktop_correction(self,control: ax.Control, interactive_nodes: list[TreeElementNode], window_name: str):
        if self.element_has_child_element(control, "AXCell", "AXStaticText"):
            interactive_nodes.pop()
            child=control.GetFirstChildControl()
            bounding_box=BoundingBox.from_bounding_rectangle(control.BoundingRectangle)
            center=bounding_box.get_center()
            metadata = {}
            if identifier := control.Identifier:
                metadata['axidentifier'] = identifier
            interactive_nodes.append(TreeElementNode(
                bounding_box=bounding_box,
                center=center,
                name=child.Label or "",
                control_type=control.Role or "",
                window_name=window_name,
                metadata=metadata,
            ))
        elif control.Role=="AXButton" and  not control.Label:
            if control.Subrole in WINDOW_CONTROL_SUBROLES:
                interactive_nodes.pop()
                bounding_box=BoundingBox.from_bounding_rectangle(control.BoundingRectangle)
                center=bounding_box.get_center()
                metadata = {}
                if identifier := control.Identifier:
                    metadata['axidentifier'] = identifier
                interactive_nodes.append(TreeElementNode(
                    bounding_box=bounding_box,
                    center=center,
                    name=WINDOW_CONTROL_SUBROLES[control.Subrole] or "",
                    control_type=control.Role or "",
                    window_name=window_name,
                    metadata=metadata,
                ))


    def tree_traversal(self,control: ax.Control, window_name: str, interactive_nodes: list[TreeElementNode], scrollable_nodes: list[ScrollElementNode], dom_informative_nodes: list[TextElementNode], is_browser: bool) -> None:
        """
        Traverse the accessibility tree and collect interactive and scrollable nodes.
        - Skip hidden elements
        - Skip zero-size elements
        - Containers (AXGroup, AXList, etc.) are not added as interactive
        - Interactive elements must have content (title/description/value/actions/subrole)
        - Interactive leaf elements: add and do not recurse into children
        """

        element_bounding_box=control.BoundingRectangle
        width=element_bounding_box.width
        height=element_bounding_box.height

        is_visible=not control.IsHidden and (width>0 and height>0)

        is_enabled=control.IsEnabled

        has_help_text=control.Help!=""

        # has_actions=any(action in INTERACTIVE_ACTIONS for action in control.ActionNames)

        has_roles=(control.Role in INTERACTIVE_ROLES) or (control.Role=="AXImage" and control.Label)
        
        is_interactive=((has_roles and is_enabled) or has_help_text) and is_visible

        if is_interactive:
            label=control.Label
            control_type=control.Role
            bounding_box=BoundingBox.from_bounding_rectangle(element_bounding_box)
            center=bounding_box.get_center()
            interactive_nodes.append(
                TreeElementNode(
                        bounding_box=bounding_box,
                        center=center,
                        name= label,
                        control_type=control_type,
                        window_name=window_name,
                    )
                )
            if is_browser:
                self._dom_correction(control, interactive_nodes, window_name)
            else:
                self._desktop_correction(control, interactive_nodes, window_name)

        for child in control.GetChildren():
            self.tree_traversal(child, window_name, interactive_nodes, scrollable_nodes, dom_informative_nodes, is_browser)
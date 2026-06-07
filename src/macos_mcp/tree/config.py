# Interactive roles - elements that users can interact with
INTERACTIVE_ROLES = {
    "AXButton",
    "AXCheckBox",
    "AXRadioButton",
    "AXTextField",
    "AXTextArea",
    "AXComboBox",
    "AXPopUpButton",
    "AXSlider",
    "AXIncrementor",
    # 'AXImage',
    "AXLink",
    "AXMenuItem",
    "AXMenuButton",
    "AXMenuBarItem",
    "AXTab",
    "AXDockItem",
    "AXCell",
    # 'AXRow',
    "AXToggle",
    "AXSwitch",
    "AXDisclosureTriangle",
    "AXColorWell",
    "AXLevelIndicator",
    "AXValueIndicator",
}

# Container roles - elements that hold other elements
CONTAINER_ROLES = {
    "AXWindow",
    "AXToolbar",
    "AXGroup",
    "AXScrollArea",
    "AXSplitGroup",
    "AXList",
    "AXTabGroup",
    "AXWebArea",
    "AXPopover",
    "AXSheet",
    "AXLayoutArea",
    "AXLayoutItem",
}

# Text roles - roles that carry readable textual content for UI context
TEXT_ROLES = {
    "AXStaticText",
    "AXHeading",
}

# Roles whose child static text is their own label, not independent context
TEXT_OWNING_ROLES = {
    "AXLink",
    "AXButton",
    "AXMenuItem",
    "AXMenuButton",
    "AXMenuBarItem",
    "AXTab",
    "AXDockItem",
    "AXCheckBox",
    "AXRadioButton",
    "AXCell",
}

# Non-interactive roles - informational elements
NON_INTERACTIVE_ROLES = {
    "AXList",
    "AXMenuBar",
    "AXMenu",
    "AXGroup",
    "AXScrollArea",
    "AXStaticText",
    "AXRadioGroup",
    "AXGrid",
    "AXApplication",
    "AXWindow",
    "AXToolbar",
    "AXSplitGroup",
    "AXTabGroup",
    "AXWebArea",
}

# Scrollable roles - elements that can be scrolled
SCROLLABLE_ROLES = {
    "AXScrollArea",
    "AXScrollView",
    "AXWebArea",
    # 'AXTable',
    # 'AXList',
    # 'AXOutline',
    "AXBrowser",
    # 'AXTextArea',
}

# Actions that indicate an element is interactive
INTERACTIVE_ACTIONS = {
    "AXPress",
    "AXConfirm",
    "AXCancel",
    "AXIncrement",
    "AXDecrement",
    "AXShowMenu",
    "AXPick",
    "AXRaise",
}

# Window control subroles with friendly names
WINDOW_CONTROL_SUBROLES = {
    "AXCloseButton": "Close Button",
    "AXMinimizeButton": "Minimize Button",
    "AXZoomButton": "Zoom Button",
    "AXFullScreenButton": "Full Screen Button",
}
# Roles that should be skipped during tree traversal to improve performance.
# These are either pure decorative/structural elements with no interactive children
# or elements whose subtrees never yield actionable nodes.
PRUNABLE_ROLES = {
    "AXScrollBar",
    "AXGrowArea",
    "AXUnknown",
    "AXValueIndicator",
    "AXLevelIndicator",
    "AXProgressIndicator",
    "AXSeparator",
    "AXSplitter",
    "AXHandle",
    "AXRuler",
    "AXRulerMarker",
    "AXBusyIndicator",
    "AXRelevanceIndicator",
    "AXSizeHandle",
    "AXResizeIndicator",
}

"""
macOS Accessibility API constants and enumerations.
Provides comprehensive definitions for roles, subroles, attributes, actions,
notifications, key codes, and error codes used by the macOS Accessibility (AX) framework.

Equivalent to the Windows UIA enums.py module, adapted for macOS.
"""


# =============================================================================
# Error Codes
# =============================================================================

class AXError:
    """
    Error codes returned by AXUIElement functions.
    Refer: ApplicationServices/HIServices/AXError.h
    """
    Success = 0
    Failure = -25200
    IllegalArgument = -25201
    InvalidUIElement = -25202
    InvalidUIElementObserver = -25203
    CannotComplete = -25204
    AttributeUnsupported = -25205
    ActionUnsupported = -25206
    NotificationUnsupported = -25207
    NotImplemented = -25208
    NotificationAlreadyRegistered = -25209
    NotificationNotRegistered = -25210
    APIDisabled = -25211
    NoValue = -25212
    ParameterizedAttributeUnsupported = -25213
    NotEnoughPrecision = -25214


AXErrorNames = {
    AXError.Success: 'Success',
    AXError.Failure: 'Failure',
    AXError.IllegalArgument: 'IllegalArgument',
    AXError.InvalidUIElement: 'InvalidUIElement',
    AXError.InvalidUIElementObserver: 'InvalidUIElementObserver',
    AXError.CannotComplete: 'CannotComplete',
    AXError.AttributeUnsupported: 'AttributeUnsupported',
    AXError.ActionUnsupported: 'ActionUnsupported',
    AXError.NotificationUnsupported: 'NotificationUnsupported',
    AXError.NotImplemented: 'NotImplemented',
    AXError.NotificationAlreadyRegistered: 'NotificationAlreadyRegistered',
    AXError.NotificationNotRegistered: 'NotificationNotRegistered',
    AXError.APIDisabled: 'APIDisabled',
    AXError.NoValue: 'NoValue',
    AXError.ParameterizedAttributeUnsupported: 'ParameterizedAttributeUnsupported',
    AXError.NotEnoughPrecision: 'NotEnoughPrecision',
}


# =============================================================================
# Roles
# =============================================================================

class Role:
    """
    Accessibility roles representing the type of UI element.
    Equivalent to Windows UIA ControlType, but using macOS AX role strings.
    Refer: HIServices/AXRoleConstants.h
    """
    # Standard UI Controls
    Application = 'AXApplication'
    Browser = 'AXBrowser'
    BusyIndicator = 'AXBusyIndicator'
    Button = 'AXButton'
    Cell = 'AXCell'
    CheckBox = 'AXCheckBox'
    ColorWell = 'AXColorWell'
    Column = 'AXColumn'
    ComboBox = 'AXComboBox'
    DateField = 'AXDateField'
    DisclosureTriangle = 'AXDisclosureTriangle'
    Dock = 'AXDock'
    DockItem = 'AXDockItem'
    Drawer = 'AXDrawer'
    Grid = 'AXGrid'
    Group = 'AXGroup'
    GrowArea = 'AXGrowArea'
    Handle = 'AXHandle'
    HelpTag = 'AXHelpTag'
    Image = 'AXImage'
    Incrementor = 'AXIncrementor'
    LayoutArea = 'AXLayoutArea'
    LayoutItem = 'AXLayoutItem'
    LevelIndicator = 'AXLevelIndicator'
    Link = 'AXLink'
    List = 'AXList'
    Matte = 'AXMatte'
    Menu = 'AXMenu'
    MenuBar = 'AXMenuBar'
    MenuBarItem = 'AXMenuBarItem'
    MenuButton = 'AXMenuButton'
    MenuItem = 'AXMenuItem'
    Outline = 'AXOutline'
    OutlineRow = 'AXOutlineRow'
    PageRole = 'AXPage'
    Popover = 'AXPopover'
    PopUpButton = 'AXPopUpButton'
    ProgressIndicator = 'AXProgressIndicator'
    RadioButton = 'AXRadioButton'
    RadioGroup = 'AXRadioGroup'
    RelevanceIndicator = 'AXRelevanceIndicator'
    Row = 'AXRow'
    Ruler = 'AXRuler'
    RulerMarker = 'AXRulerMarker'
    ScrollArea = 'AXScrollArea'
    ScrollBar = 'AXScrollBar'
    ScrollView = 'AXScrollView'
    Sheet = 'AXSheet'
    Slider = 'AXSlider'
    SortButton = 'AXSortButton'
    SplitGroup = 'AXSplitGroup'
    Splitter = 'AXSplitter'
    StaticText = 'AXStaticText'
    SystemWide = 'AXSystemWide'
    Tab = 'AXTab'
    TabGroup = 'AXTabGroup'
    Table = 'AXTable'
    TextArea = 'AXTextArea'
    TextField = 'AXTextField'
    Toggle = 'AXToggle'
    Toolbar = 'AXToolbar'
    Unknown = 'AXUnknown'
    ValueIndicator = 'AXValueIndicator'
    Window = 'AXWindow'

    # Web-specific roles
    WebArea = 'AXWebArea'

    # Modern/SwiftUI roles
    Switch = 'AXSwitch'


RoleNames = {v: k for k, v in vars(Role).items() if not k.startswith('_') and isinstance(v, str)}


# =============================================================================
# Subroles
# =============================================================================

class Subrole:
    """
    Accessibility subroles providing additional type information.
    Refer: HIServices/AXRoleConstants.h
    """
    # Window subroles
    CloseButton = 'AXCloseButton'
    MinimizeButton = 'AXMinimizeButton'
    ZoomButton = 'AXZoomButton'
    FullScreenButton = 'AXFullScreenButton'
    ToolbarButton = 'AXToolbarButton'
    StandardWindow = 'AXStandardWindow'
    Dialog = 'AXDialog'
    SystemDialog = 'AXSystemDialog'
    FloatingWindow = 'AXFloatingWindow'
    SystemFloatingWindow = 'AXSystemFloatingWindow'
    FullScreenWindow = 'AXFullScreenWindow'

    # Text subroles
    SecureTextField = 'AXSecureTextField'
    SearchField = 'AXSearchField'

    # Button subroles
    IncrementArrow = 'AXIncrementArrow'
    DecrementArrow = 'AXDecrementArrow'
    IncrementPage = 'AXIncrementPage'
    DecrementPage = 'AXDecrementPage'

    # Table/List subroles
    ContentList = 'AXContentList'
    DefinitionList = 'AXDefinitionList'
    SortButton = 'AXSortButton'
    TableRow = 'AXTableRow'
    OutlineRow = 'AXOutlineRow'

    # Other subroles
    ApplicationDockItem = 'AXApplicationDockItem'
    DocumentDockItem = 'AXDocumentDockItem'
    FolderDockItem = 'AXFolderDockItem'
    MinimizedWindowDockItem = 'AXMinimizedWindowDockItem'
    URLDockItem = 'AXURLDockItem'
    DockExtraDockItem = 'AXDockExtraDockItem'
    TrashDockItem = 'AXTrashDockItem'
    SeparatorDockItem = 'AXSeparatorDockItem'
    ProcessSwitcherList = 'AXProcessSwitcherList'
    TabButton = 'AXTabButton'
    CollectionList = 'AXCollectionList'
    SectionList = 'AXSectionList'
    Timeline = 'AXTimeline'
    RatingIndicator = 'AXRatingIndicator'
    Toggle = 'AXToggle'
    Switch = 'AXSwitch'
    DescriptionList = 'AXDescriptionList'


SubroleNames = {v: k for k, v in vars(Subrole).items() if not k.startswith('_') and isinstance(v, str)}


# =============================================================================
# Attributes
# =============================================================================

class Attribute:
    """
    Accessibility attributes for querying element properties.
    Equivalent to Windows UIA PropertyId.
    Refer: HIServices/AXAttributeConstants.h
    """
    # Standard attributes (available on most elements)
    Role = 'AXRole'
    Subrole = 'AXSubrole'
    RoleDescription = 'AXRoleDescription'
    Title = 'AXTitle'
    Description = 'AXDescription'
    Help = 'AXHelp'
    Value = 'AXValue'
    MinValue = 'AXMinValue'
    MaxValue = 'AXMaxValue'
    ValueDescription = 'AXValueDescription'
    Enabled = 'AXEnabled'
    Focused = 'AXFocused'
    Parent = 'AXParent'
    Children = 'AXChildren'
    SelectedChildren = 'AXSelectedChildren'
    VisibleChildren = 'AXVisibleChildren'
    Window = 'AXWindow'
    TopLevelUIElement = 'AXTopLevelUIElement'
    Position = 'AXPosition'
    Size = 'AXSize'
    Frame = 'AXFrame'
    Contents = 'AXContents'
    Identifier = 'AXIdentifier'
    Hidden = 'AXHidden'
    Selected = 'AXSelected'

    # Text-specific attributes
    NumberOfCharacters = 'AXNumberOfCharacters'
    SelectedText = 'AXSelectedText'
    SelectedTextRange = 'AXSelectedTextRange'
    SelectedTextRanges = 'AXSelectedTextRanges'
    VisibleCharacterRange = 'AXVisibleCharacterRange'
    InsertionPointLineNumber = 'AXInsertionPointLineNumber'
    SharedTextUIElements = 'AXSharedTextUIElements'
    SharedCharacterRange = 'AXSharedCharacterRange'

    # Window-specific attributes
    Main = 'AXMain'
    Minimized = 'AXMinimized'
    CloseButton = 'AXCloseButton'
    ZoomButton = 'AXZoomButton'
    MinimizeButton = 'AXMinimizeButton'
    ToolbarButton = 'AXToolbarButton'
    FullScreenButton = 'AXFullScreenButton'
    Proxy = 'AXProxy'
    GrowArea = 'AXGrowArea'
    Modal = 'AXModal'
    DefaultButton = 'AXDefaultButton'
    CancelButton = 'AXCancelButton'
    FullScreen = 'AXFullScreen'

    # Application-specific attributes
    MenuBar = 'AXMenuBar'
    Windows = 'AXWindows'
    FocusedWindow = 'AXFocusedWindow'
    MainWindow = 'AXMainWindow'
    FrontmostApplication = 'AXFrontmostApplication'
    FocusedApplication = 'AXFocusedApplication'
    FocusedUIElement = 'AXFocusedUIElement'
    ExtrasMenuBar = 'AXExtrasMenuBar'
    Enhanced = 'AXEnhancedUserInterface'

    # Menu-specific attributes
    MenuItemCmdChar = 'AXMenuItemCmdChar'
    MenuItemCmdVirtualKey = 'AXMenuItemCmdVirtualKey'
    MenuItemCmdGlyph = 'AXMenuItemCmdGlyph'
    MenuItemCmdModifiers = 'AXMenuItemCmdModifiers'
    MenuItemMarkChar = 'AXMenuItemMarkChar'
    MenuItemPrimaryUIElement = 'AXMenuItemPrimaryUIElement'

    # Table/Grid-specific attributes
    Rows = 'AXRows'
    VisibleRows = 'AXVisibleRows'
    SelectedRows = 'AXSelectedRows'
    Columns = 'AXColumns'
    VisibleColumns = 'AXVisibleColumns'
    SelectedColumns = 'AXSelectedColumns'
    Header = 'AXHeader'
    ColumnCount = 'AXColumnCount'
    RowCount = 'AXRowCount'
    Index = 'AXIndex'
    ColumnHeaderUIElements = 'AXColumnHeaderUIElements'
    RowHeaderUIElements = 'AXRowHeaderUIElements'

    # Scroll-specific attributes
    HorizontalScrollBar = 'AXHorizontalScrollBar'
    VerticalScrollBar = 'AXVerticalScrollBar'
    Orientation = 'AXOrientation'

    # Outline/Disclosure attributes
    DisclosedRows = 'AXDisclosedRows'
    DisclosedByRow = 'AXDisclosedByRow'
    DisclosureLevel = 'AXDisclosureLevel'
    Expanded = 'AXExpanded'

    # Misc attributes
    Document = 'AXDocument'
    URL = 'AXURL'
    LabelValue = 'AXLabelValue'
    LabelUIElements = 'AXLabelUIElements'
    PlaceholderValue = 'AXPlaceholderValue'
    Actions = 'AXActions'
    ColumnTitles = 'AXColumnTitles'
    EditableAncestor = 'AXEditableAncestor'
    LinkedUIElements = 'AXLinkedUIElements'
    TitleUIElement = 'AXTitleUIElement'
    ServesAsTitleForUIElements = 'AXServesAsTitleForUIElements'
    IsApplicationRunning = 'AXIsApplicationRunning'

    # Parameterized attributes (text)
    LineForIndex = 'AXLineForIndexParameterized'
    RangeForLine = 'AXRangeForLineParameterized'
    StringForRange = 'AXStringForRangeParameterized'
    RangeForPosition = 'AXRangeForPositionParameterized'
    RangeForIndex = 'AXRangeForIndexParameterized'
    BoundsForRange = 'AXBoundsForRangeParameterized'
    AttributedStringForRange = 'AXAttributedStringForRangeParameterized'
    RTFForRange = 'AXRTFForRangeParameterized'
    StyleRangeForIndex = 'AXStyleRangeForIndexParameterized'

    # Date/Time field attributes
    AMPMField = 'AXAMPMField'
    DayField = 'AXDayField'
    HourField = 'AXHourField'
    MinuteField = 'AXMinuteField'
    SecondField = 'AXSecondField'
    MonthField = 'AXMonthField'
    YearField = 'AXYearField'
    IncrementorElement = 'AXIncrementor'

    # Additional documented attributes
    AllowedValues = 'AXAllowedValues'
    ValueIncrement = 'AXValueIncrement'
    ColumnTitle = 'AXColumnTitle'


# =============================================================================
# Actions
# =============================================================================

class Action:
    """
    Accessibility actions that can be performed on elements.
    Equivalent to Windows UIA patterns (InvokePattern.Invoke, etc.).
    Refer: HIServices/AXActionConstants.h
    """
    Press = 'AXPress'
    Increment = 'AXIncrement'
    Decrement = 'AXDecrement'
    Confirm = 'AXConfirm'
    Cancel = 'AXCancel'
    ShowMenu = 'AXShowMenu'
    Pick = 'AXPick'
    Raise = 'AXRaise'
    ShowAlternateUI = 'AXShowAlternateUI'
    ShowDefaultUI = 'AXShowDefaultUI'
    ScrollLeftByPage = 'AXScrollLeftByPage'
    ScrollRightByPage = 'AXScrollRightByPage'
    ScrollUpByPage = 'AXScrollUpByPage'
    ScrollDownByPage = 'AXScrollDownByPage'


ActionNames = {v: k for k, v in vars(Action).items() if not k.startswith('_') and isinstance(v, str)}


# =============================================================================
# Notifications
# =============================================================================

class Notification:
    """
    Accessibility notifications (events) that can be observed.
    Equivalent to Windows UIA EventId.
    Refer: HIServices/AXNotificationConstants.h
    """
    # Focus notifications
    FocusedUIElementChanged = 'AXFocusedUIElementChanged'
    FocusedWindowChanged = 'AXFocusedWindowChanged'
    ApplicationActivated = 'AXApplicationActivated'
    ApplicationDeactivated = 'AXApplicationDeactivated'
    ApplicationHidden = 'AXApplicationHidden'
    ApplicationShown = 'AXApplicationShown'

    # Window notifications
    WindowCreated = 'AXWindowCreated'
    WindowMoved = 'AXWindowMoved'
    WindowResized = 'AXWindowResized'
    WindowMiniaturized = 'AXWindowMiniaturized'
    WindowDeminiaturized = 'AXWindowDeminiaturized'
    MainWindowChanged = 'AXMainWindowChanged'

    # Element lifecycle notifications
    Created = 'AXCreated'
    UIElementDestroyed = 'AXUIElementDestroyed'

    # Menu notifications
    MenuOpened = 'AXMenuOpened'
    MenuClosed = 'AXMenuClosed'
    MenuItemSelected = 'AXMenuItemSelected'

    # Value/Selection notifications
    ValueChanged = 'AXValueChanged'
    TitleChanged = 'AXTitleChanged'
    SelectedTextChanged = 'AXSelectedTextChanged'
    SelectedChildrenChanged = 'AXSelectedChildrenChanged'
    SelectedChildrenMoved = 'AXSelectedChildrenMoved'
    SelectedRowsChanged = 'AXSelectedRowsChanged'
    SelectedColumnsChanged = 'AXSelectedColumnsChanged'
    SelectedCellsChanged = 'AXSelectedCellsChanged'
    RowCountChanged = 'AXRowCountChanged'
    UnitsChanged = 'AXUnitsChanged'

    # Layout notifications
    Moved = 'AXMoved'
    Resized = 'AXResized'
    LayoutChanged = 'AXLayoutChanged'

    # Drawer/Sheet notifications
    DrawerCreated = 'AXDrawerCreated'
    SheetCreated = 'AXSheetCreated'
    HelpTagCreated = 'AXHelpTagCreated'

    # Expanded/Collapsed notifications
    RowExpanded = 'AXRowExpanded'
    RowCollapsed = 'AXRowCollapsed'

    # Announcement notifications
    AnnouncementRequested = 'AXAnnouncementRequested'


# Notification categories for easy filtering
FOCUS_NOTIFICATIONS = {
    Notification.FocusedUIElementChanged,
    Notification.FocusedWindowChanged,
    Notification.MainWindowChanged,
}

STRUCTURE_NOTIFICATIONS = {
    Notification.Created,
    Notification.UIElementDestroyed,
    Notification.WindowCreated,
    Notification.MenuOpened,
    Notification.MenuClosed,
    Notification.RowCountChanged,
}

PROPERTY_NOTIFICATIONS = {
    Notification.ValueChanged,
    Notification.TitleChanged,
    Notification.SelectedTextChanged,
    Notification.SelectedChildrenChanged,
    Notification.SelectedChildrenMoved,
    Notification.SelectedRowsChanged,
    Notification.SelectedColumnsChanged,
    Notification.SelectedCellsChanged,
    Notification.UnitsChanged,
    Notification.Moved,
    Notification.Resized,
}

ALL_NOTIFICATIONS = list(
    FOCUS_NOTIFICATIONS | STRUCTURE_NOTIFICATIONS | PROPERTY_NOTIFICATIONS
)


NotificationNames = {v: k for k, v in vars(Notification).items() if not k.startswith('_') and isinstance(v, str)}


# =============================================================================
# Notification Info Keys
# =============================================================================

class NotificationKey:
    """
    Keys used in notification info dictionaries.
    Passed to AXObserverCallbackWithInfo callbacks.
    Refer: HIServices/AXNotificationConstants.h
    """
    Announcement = 'AXAnnouncementKey'
    Priority = 'AXPriorityKey'
    UIElements = 'AXUIElementsKey'


# =============================================================================
# Virtual Key Codes (macOS)
# =============================================================================

class KeyCode:
    """
    macOS virtual key codes for keyboard events.
    Used with CGEventCreateKeyboardEvent.
    Refer: Carbon/HIToolbox/Events.h
    """
    # Letters
    A = 0x00
    S = 0x01
    D = 0x02
    F = 0x03
    H = 0x04
    G = 0x05
    Z = 0x06
    X = 0x07
    C = 0x08
    V = 0x09
    B = 0x0B
    Q = 0x0C
    W = 0x0D
    E = 0x0E
    R = 0x0F
    Y = 0x10
    T = 0x11
    O = 0x1F
    U = 0x20
    I = 0x22
    P = 0x23
    L = 0x25
    J = 0x26
    K = 0x28
    N = 0x2D
    M = 0x2E

    # Numbers
    Num1 = 0x12
    Num2 = 0x13
    Num3 = 0x14
    Num4 = 0x15
    Num5 = 0x17
    Num6 = 0x16
    Num7 = 0x1A
    Num8 = 0x1C
    Num9 = 0x19
    Num0 = 0x1D

    # Special keys
    Return = 0x24
    Tab = 0x30
    Space = 0x31
    Delete = 0x33
    Escape = 0x35
    ForwardDelete = 0x75

    # Modifier keys
    Command = 0x37
    Shift = 0x38
    CapsLock = 0x39
    Option = 0x3A
    Control = 0x3B
    RightCommand = 0x36
    RightShift = 0x3C
    RightOption = 0x3D
    RightControl = 0x3E
    Function = 0x3F

    # Arrow keys
    LeftArrow = 0x7B
    RightArrow = 0x7C
    DownArrow = 0x7D
    UpArrow = 0x7E

    # Function keys
    F1 = 0x7A
    F2 = 0x78
    F3 = 0x63
    F4 = 0x76
    F5 = 0x60
    F6 = 0x61
    F7 = 0x62
    F8 = 0x64
    F9 = 0x65
    F10 = 0x6D
    F11 = 0x67
    F12 = 0x6F
    F13 = 0x69
    F14 = 0x6B
    F15 = 0x71
    F16 = 0x6A
    F17 = 0x40
    F18 = 0x4F
    F19 = 0x50
    F20 = 0x5A

    # Navigation keys
    Home = 0x73
    End = 0x77
    PageUp = 0x74
    PageDown = 0x79

    # Symbols
    Equal = 0x18
    Minus = 0x1B
    LeftBracket = 0x21
    RightBracket = 0x1E
    Quote = 0x27
    Semicolon = 0x29
    Backslash = 0x2A
    Comma = 0x2B
    Slash = 0x2C
    Period = 0x2F
    Grave = 0x32

    # Numpad
    KeypadDecimal = 0x41
    KeypadMultiply = 0x43
    KeypadPlus = 0x45
    KeypadClear = 0x47
    KeypadDivide = 0x4B
    KeypadEnter = 0x4C
    KeypadMinus = 0x4E
    KeypadEquals = 0x51
    Keypad0 = 0x52
    Keypad1 = 0x53
    Keypad2 = 0x54
    Keypad3 = 0x55
    Keypad4 = 0x56
    Keypad5 = 0x57
    Keypad6 = 0x58
    Keypad7 = 0x59
    Keypad8 = 0x5B
    Keypad9 = 0x5C

    # Media keys
    VolumeUp = 0x48
    VolumeDown = 0x49
    Mute = 0x4A


# Key name to key code mapping for string-based key input
KEY_NAME_TO_CODE = {
    # Letters (lowercase)
    'a': KeyCode.A, 'b': KeyCode.B, 'c': KeyCode.C, 'd': KeyCode.D,
    'e': KeyCode.E, 'f': KeyCode.F, 'g': KeyCode.G, 'h': KeyCode.H,
    'i': KeyCode.I, 'j': KeyCode.J, 'k': KeyCode.K, 'l': KeyCode.L,
    'm': KeyCode.M, 'n': KeyCode.N, 'o': KeyCode.O, 'p': KeyCode.P,
    'q': KeyCode.Q, 'r': KeyCode.R, 's': KeyCode.S, 't': KeyCode.T,
    'u': KeyCode.U, 'v': KeyCode.V, 'w': KeyCode.W, 'x': KeyCode.X,
    'y': KeyCode.Y, 'z': KeyCode.Z,
    # Numbers
    '1': KeyCode.Num1, '2': KeyCode.Num2, '3': KeyCode.Num3,
    '4': KeyCode.Num4, '5': KeyCode.Num5, '6': KeyCode.Num6,
    '7': KeyCode.Num7, '8': KeyCode.Num8, '9': KeyCode.Num9,
    '0': KeyCode.Num0,
    # Special keys
    'return': KeyCode.Return, 'enter': KeyCode.Return,
    'tab': KeyCode.Tab, 'space': KeyCode.Space,
    'delete': KeyCode.Delete, 'backspace': KeyCode.Delete,
    'forwarddelete': KeyCode.ForwardDelete,
    'escape': KeyCode.Escape, 'esc': KeyCode.Escape,
    # Modifiers
    'command': KeyCode.Command, 'cmd': KeyCode.Command,
    'shift': KeyCode.Shift, 'option': KeyCode.Option,
    'alt': KeyCode.Option, 'control': KeyCode.Control,
    'ctrl': KeyCode.Control, 'fn': KeyCode.Function,
    'capslock': KeyCode.CapsLock,
    # Arrow keys
    'left': KeyCode.LeftArrow, 'right': KeyCode.RightArrow,
    'up': KeyCode.UpArrow, 'down': KeyCode.DownArrow,
    # Function keys
    'f1': KeyCode.F1, 'f2': KeyCode.F2, 'f3': KeyCode.F3,
    'f4': KeyCode.F4, 'f5': KeyCode.F5, 'f6': KeyCode.F6,
    'f7': KeyCode.F7, 'f8': KeyCode.F8, 'f9': KeyCode.F9,
    'f10': KeyCode.F10, 'f11': KeyCode.F11, 'f12': KeyCode.F12,
    # Navigation
    'home': KeyCode.Home, 'end': KeyCode.End,
    'pageup': KeyCode.PageUp, 'pagedown': KeyCode.PageDown,
    # Symbols
    '=': KeyCode.Equal, '-': KeyCode.Minus,
    '[': KeyCode.LeftBracket, ']': KeyCode.RightBracket,
    "'": KeyCode.Quote, ';': KeyCode.Semicolon,
    '\\': KeyCode.Backslash, ',': KeyCode.Comma,
    '/': KeyCode.Slash, '.': KeyCode.Period,
    '`': KeyCode.Grave,
    # Volume
    'volumeup': KeyCode.VolumeUp, 'volumedown': KeyCode.VolumeDown,
    'mute': KeyCode.Mute,
}


# =============================================================================
# CGEvent Types (Mouse)
# =============================================================================

class MouseEventType:
    """
    CGEvent types for mouse events.
    Used with CGEventCreateMouseEvent.
    """
    LeftMouseDown = 1
    LeftMouseUp = 2
    RightMouseDown = 3
    RightMouseUp = 4
    MouseMoved = 5
    LeftMouseDragged = 6
    RightMouseDragged = 7
    OtherMouseDown = 25
    OtherMouseUp = 26
    OtherMouseDragged = 27
    ScrollWheel = 22


class MouseButton:
    """Mouse button identifiers for CGEvent."""
    Left = 0
    Right = 1
    Center = 2


# =============================================================================
# CGEvent Flags (Modifier keys)
# =============================================================================

class EventFlag:
    """
    CGEvent flags for modifier keys.
    Used with CGEventSetFlags.
    """
    MaskAlphaShift = 0x00010000
    MaskShift = 0x00020000
    MaskControl = 0x00040000
    MaskAlternate = 0x00080000  # Option key
    MaskCommand = 0x00100000
    MaskNumericPad = 0x00200000
    MaskHelp = 0x00400000
    MaskSecondaryFn = 0x00800000


# Modifier key mapping for shortcut parsing
MODIFIER_KEY_MAP = {
    'command': EventFlag.MaskCommand,
    'cmd': EventFlag.MaskCommand,
    'shift': EventFlag.MaskShift,
    'option': EventFlag.MaskAlternate,
    'alt': EventFlag.MaskAlternate,
    'control': EventFlag.MaskControl,
    'ctrl': EventFlag.MaskControl,
    'fn': EventFlag.MaskSecondaryFn,
}


# =============================================================================
# Orientation
# =============================================================================

class Orientation:
    """Orientation values for scroll bars and other oriented elements."""
    Horizontal = 'AXHorizontalOrientation'
    Vertical = 'AXVerticalOrientation'
    Unknown = 'AXUnknownOrientation'


# =============================================================================
# Sort Direction
# =============================================================================

class SortDirection:
    """Sort direction values for table columns."""
    Ascending = 'AXAscendingSortDirection'
    Descending = 'AXDescendingSortDirection'
    Unknown = 'AXUnknownSortDirection'


# =============================================================================
# Units
# =============================================================================

class Units:
    """Units for text ranges and other measurements."""
    Points = 'AXPointsUnit'
    Characters = 'AXCharactersUnit'
    Words = 'AXWordsUnit'
    Lines = 'AXLinesUnit'
    Sentences = 'AXSentencesUnit'
    Paragraphs = 'AXParagraphsUnit'
    Pages = 'AXPagesUnit'
    Document = 'AXDocumentUnit'


# =============================================================================
# AXValue Types
# =============================================================================

class AXValueType:
    """
    Types of data stored in an AXValueRef.
    Used with AXValueCreate and AXValueGetValue.
    Refer: HIServices/AXValue.h
    """
    CGPoint = 1   # kAXValueCGPointType
    CGSize = 2    # kAXValueCGSizeType
    CGRect = 3    # kAXValueCGRectType
    CFRange = 4   # kAXValueCFRangeType
    AXError = 5   # kAXValueAXErrorType
    Illegal = 0   # kAXValueIllegalType


# =============================================================================
# Text Attributed String Keys
# =============================================================================

class TextAttribute:
    """
    Keys for dictionaries describing attributed strings in the accessibility API.
    Used with parameterized attributes like AXAttributedStringForRange.
    Refer: HIServices/AXTextAttributedString.h
    """
    # Font attributes
    Font = 'AXFontText'
    FontFamily = 'AXFontFamily'
    FontName = 'AXFontName'
    FontSize = 'AXFontSize'
    VisibleName = 'AXVisibleName'

    # Color attributes
    ForegroundColor = 'AXForegroundColorText'
    BackgroundColor = 'AXBackgroundColorText'
    UnderlineColor = 'AXUnderlineColorText'
    StrikethroughColor = 'AXStrikethroughColorText'

    # Style attributes
    Underline = 'AXUnderlineText'
    Strikethrough = 'AXStrikethroughText'
    Shadow = 'AXShadowText'
    Superscript = 'AXSuperscriptText'

    # Content attributes
    Attachment = 'AXAttachmentText'
    Link = 'AXLinkText'
    NaturalLanguage = 'AXNaturalLanguageText'
    ReplacementString = 'AXReplacementStringText'

    # Spell-check attributes
    Misspelled = 'AXMisspelledText'
    MarkedMisspelled = 'AXMarkedMisspelledText'
    Autocorrected = 'AXAutocorrectedText'


# =============================================================================
# Activation Policy
# =============================================================================

class ActivationPolicy:
    """
    Application activation policies from NSApplicationActivationPolicy.
    Determines how an application appears in the Dock and App Switcher.
    """
    Regular = 0       # Appears in Dock and App Switcher (normal apps)
    Accessory = 1     # Does not appear in Dock, may appear in App Switcher
    Prohibited = 2    # Does not appear in Dock or App Switcher (background agents)


# Reverse lookup: int → human-readable name
ActivationPolicyNames = {
    0: 'Regular',
    1: 'Accessory',
    2: 'Prohibited',
}

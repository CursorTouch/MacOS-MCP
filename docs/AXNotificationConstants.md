# AXNotificationConstants.h Documentation

## Overview
This header defines the string constants used to specify notifications sent by accessibility objects.

## Constants

### Notifications

| Constant Name | Description |
| :--- | :--- |
| `kAXAnnouncementRequestedNotification` | Request an announcement to be spoken. |
| `kAXApplicationActivatedNotification` | The application was activated. |
| `kAXApplicationDeactivatedNotification` | The application was deactivated. |
| `kAXApplicationHiddenNotification` | The application was hidden. |
| `kAXApplicationShownNotification` | The application was shown. |
| `kAXCreatedNotification` | An accessibility object was created. |
| `kAXDrawerCreatedNotification` | A drawer was created. |
| `kAXFocusedUIElementChangedNotification` | The focused accessibility object has changed. |
| `kAXFocusedWindowChangedNotification` | The focused window has changed. |
| `kAXHelpTagCreatedNotification` | A help tag is now visible. |
| `kAXLayoutChangedNotification` | The layout of the UI elements changed. |
| `kAXMainWindowChangedNotification` | The main window has changed. |
| `kAXMenuClosedNotification` | A menu was closed. |
| `kAXMenuItemSelectedNotification` | A menu item was selected. |
| `kAXMenuOpenedNotification` | A menu was opened. |
| `kAXMovedNotification` | The position of an accessibility object changed. |
| `kAXResizedNotification` | The window has changed size. |
| `kAXRowCollapsedNotification` | A row in an outline has been collapsed. |
| `kAXRowCountChangedNotification` | The number of rows in a table changed. |
| `kAXRowExpandedNotification` | A row in an outline has been expanded. |
| `kAXSelectedCellsChangedNotification` | The selected cells in a table changed. |
| `kAXSelectedChildrenChangedNotification` | The selected children changed. |
| `kAXSelectedChildrenMovedNotification` | The selected children moved. |
| `kAXSelectedColumnsChangedNotification` | The set of selected columns changed. |
| `kAXSelectedRowsChangedNotification` | The set of selected rows changed. |
| `kAXSelectedTextChangedNotification` | A different set of text was selected. |
| `kAXSheetCreatedNotification` | A sheet was created. |
| `kAXTitleChangedNotification` | The title of an accessibility object changed. |
| `kAXUIElementDestroyedNotification` | An accessibility object was disposed of. |
| `kAXUnitsChangedNotification` | The units have changed. |
| `kAXValueChangedNotification` | The value of an attribute changed. |
| `kAXWindowCreatedNotification` | A window was created. |
| `kAXWindowDeminiaturizedNotification` | The window was moved out of the Dock. |
| `kAXWindowMiniaturizedNotification` | The window was moved into the Dock. |
| `kAXWindowMovedNotification` | The window move operation completed. |
| `kAXWindowResizedNotification` | The window resize operation completed. |

### Notification Keys

| Constant Name | Description |
| :--- | :--- |
| `kAXAnnouncementKey` | Info key used to specify an announcement to be spoken. |
| `kAXPriorityKey` | Info key used to specify a priority for the notification. |
| `kAXUIElementsKey` | Info key used to specify an array of elements. |

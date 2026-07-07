# AXUIElement.h Documentation

## Overview
This header file defines the functions and data types used to communicate with and control accessible applications in macOS.

## Data Types

### AXUIElementRef
`typedef const struct __AXUIElement *AXUIElementRef;`
A reference to an accessibility object (a `CFTypeRef`).

### AXObserverRef
`typedef const struct __AXObserver *AXObserverRef;`
A reference to an accessibility observer object.

## Callbacks

### AXObserverCallback
```c
void (*AXObserverCallback)(
    AXUIElementRef element, 
    CFStringRef notification, 
    void *refcon
);
```
Callback function called when a notification is received.

### AXObserverCallbackWithInfo
```c
void (*AXObserverCallbackWithInfo)(
    AXUIElementRef element, 
    CFStringRef notification, 
    CFDictionaryRef info, 
    void *refcon
);
```
Callback function called when a notification is received, including an information dictionary.

## Functions

### Notification API

#### AXObserverAddNotification
```c
AXError AXObserverAddNotification(
    AXObserverRef observer, 
    AXUIElementRef element, 
    CFStringRef notification, 
    void *refcon
);
```
Registers the observer to receive a specific notification from an accessibility element.

#### AXObserverCreate
```c
AXError AXObserverCreate(
    pid_t pid, 
    AXObserverCallback callback, 
    AXObserverRef *outObserver
);
```
Creates a new observer for an application with the specified process ID.

#### AXObserverCreateWithInfoCallback
```c
AXError AXObserverCreateWithInfoCallback(
    pid_t pid, 
    AXObserverCallbackWithInfo callback, 
    AXObserverRef *outObserver
);
```
Creates a new observer for an application that provides an information dictionary to the callback.

#### AXObserverGetRunLoopSource
```c
CFRunLoopSourceRef AXObserverGetRunLoopSource(AXObserverRef observer);
```
Returns the Core Foundation run loop source for the observer, which must be added to a run loop.

#### AXObserverGetTypeID
```c
CFTypeID AXObserverGetTypeID(void);
```
Returns the unique type identifier for the AXObserver class.

#### AXObserverRemoveNotification
```c
AXError AXObserverRemoveNotification(
    AXObserverRef observer, 
    AXUIElementRef element, 
    CFStringRef notification
);
```
Unregisters the observer from receiving a specific notification.

### UI Element API

#### AXIsProcessTrusted
```c
Boolean AXIsProcessTrusted(void);
```
Returns whether the current process is a "trusted" accessibility client.

#### AXIsProcessTrustedWithOptions
```c
Boolean AXIsProcessTrustedWithOptions(CFDictionaryRef options);
```
Returns whether the current process is trusted, with an option to prompt the user for permission.

#### AXUIElementCopyActionDescription
```c
AXError AXUIElementCopyActionDescription(
    AXUIElementRef element, 
    CFStringRef action, 
    CFStringRef *description
);
```
Returns a localized description of a specified action.

#### AXUIElementCopyActionNames
```c
AXError AXUIElementCopyActionNames(
    AXUIElementRef element, 
    CFArrayRef *names
);
```
Returns a list of actions that the element can perform.

#### AXUIElementCopyAttributeNames
```c
AXError AXUIElementCopyAttributeNames(
    AXUIElementRef element, 
    CFArrayRef *names
);
```
Returns a list of attributes supported by the element.

#### AXUIElementCopyAttributeValue
```c
AXError AXUIElementCopyAttributeValue(
    AXUIElementRef element, 
    CFStringRef attribute, 
    CFTypeRef *value
);
```
Returns the value of a specific attribute.

#### AXUIElementCopyAttributeValues
```c
AXError AXUIElementCopyAttributeValues(
    AXUIElementRef element, 
    CFStringRef attribute, 
    CFIndex index, 
    CFIndex maxValues, 
    CFArrayRef *values
);
```
Returns an array of attribute values for a multi-valued attribute.

#### AXUIElementCopyElementAtPosition
```c
AXError AXUIElementCopyElementAtPosition(
    AXUIElementRef application, 
    float x, 
    float y, 
    AXUIElementRef *element
);
```
Returns the accessibility element at the specified screen coordinates.

#### AXUIElementCopyMultipleAttributeValues
```c
AXError AXUIElementCopyMultipleAttributeValues(
    AXUIElementRef element, 
    CFArrayRef attributes, 
    AXCopyMultipleAttributeOptions options, 
    CFArrayRef *values
);
```
Returns the values for multiple attributes in a single call.

#### AXUIElementCreateApplication
```c
AXUIElementRef AXUIElementCreateApplication(pid_t pid);
```
Creates an accessibility object representing an application.

#### AXUIElementCreateSystemWide
```c
AXUIElementRef AXUIElementCreateSystemWide(void);
```
Creates an accessibility object that provides information about the system as a whole.

#### AXUIElementGetMessagingTimeout
```c
AXError AXUIElementGetMessagingTimeout(
    AXUIElementRef element, 
    float *timeout
);
```
Returns the current messaging timeout value for the accessibility object.

#### AXUIElementGetPid
```c
AXError AXUIElementGetPid(
    AXUIElementRef element, 
    pid_t *pid
);
```
Returns the process ID of the application that the element belongs to.

#### AXUIElementGetTypeID
```c
CFTypeID AXUIElementGetTypeID(void);
```
Returns the unique type identifier for the AXUIElement class.

#### AXUIElementPerformAction
```c
AXError AXUIElementPerformAction(
    AXUIElementRef element, 
    CFStringRef action
);
```
Requests that the element perform the specified action.

#### AXUIElementPostKeyboardEvent
```c
AXError AXUIElementPostKeyboardEvent(
    AXUIElementRef application, 
    CGCharCode keyChar, 
    CGKeyCode keyCode, 
    Boolean keyDown
);
```
Posts a keyboard event to the specified application.

#### AXUIElementSetAttributeValue
```c
AXError AXUIElementSetAttributeValue(
    AXUIElementRef element, 
    CFStringRef attribute, 
    CFTypeRef value
);
```
Sets the value of a specific attribute.

#### AXUIElementSetMessagingTimeout
```c
AXError AXUIElementSetMessagingTimeout(
    AXUIElementRef element, 
    float timeout
);
```
Sets the messaging timeout value for the accessibility object.

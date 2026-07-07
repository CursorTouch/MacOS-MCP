# AXError.h Documentation

## Overview
This header defines the error codes returned by all functions in the Accessibility API.

## Enumerations

### AXError
`typedef int32_t AXError;`

| Enumerator | Value | Description |
| :--- | :--- | :--- |
| `kAXErrorSuccess` | 0 | No error. |
| `kAXErrorFailure` | -25200 | A fundamental error occurred (e.g., memory failure). |
| `kAXErrorIllegalArgument` | -25201 | One or more arguments are invalid. |
| `kAXErrorInvalidUIElement` | -25202 | The `AXUIElementRef` passed is invalid. |
| `kAXErrorInvalidUIElementObserver` | -25203 | The observer passed is invalid. |
| `kAXErrorCannotComplete` | -25204 | The function could not complete (e.g., the target application is busy). |
| `kAXErrorAttributeUnsupported` | -25205 | The attribute is not supported by the element. |
| `kAXErrorActionUnsupported` | -25206 | The action is not supported by the element. |
| `kAXErrorNotificationUnsupported` | -25207 | The notification is not supported by the element. |
| `kAXErrorNotImplemented` | -25208 | The function or process does not support the accessibility API. |
| `kAXErrorNotificationAlreadyRegistered` | -25209 | The notification has already been registered. |
| `kAXErrorNotificationNotRegistered` | -25210 | The notification has not been registered. |
| `kAXErrorAPIDisabled` | -25211 | The Accessibility API is disabled in System Settings. |
| `kAXErrorNoValue` | -25212 | The requested attribute value does not exist. |
| `kAXErrorParameterizedAttributeUnsupported` | -25213 | The parameterized attribute is not supported. |
| `kAXErrorNotEnoughPrecision` | -25214 | The requested value does not have enough precision. |

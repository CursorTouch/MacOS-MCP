# AXValue.h Documentation

## Overview
This header defines functions to wrap various data types (like points, sizes, and rectangles) into a `CFTypeRef` so they can be passed across the accessibility API.

## Data Types

### AXValueRef
`typedef const struct __AXValue *AXValueRef;`
A reference to a value object.

### AXValueType
An enumeration specifying the type of data stored in an `AXValueRef`.

| Enumerator | Description |
| :--- | :--- |
| `kAXValueCGPointType` | A `CGPoint` structure. |
| `kAXValueCGSizeType` | A `CGSize` structure. |
| `kAXValueCGRectType` | A `CGRect` structure. |
| `kAXValueCFRangeType` | A `CFRange` structure. |
| `kAXValueAXErrorType` | An `AXError` value. |
| `kAXValueIllegalType` | An illegal type. |

## Functions

### AXValueCreate
```c
AXValueRef AXValueCreate(
    AXValueType type, 
    const void *valuePtr
);
```
Creates a new `AXValueRef` from the provided data.

### AXValueGetType
```c
AXValueType AXValueGetType(AXValueRef value);
```
Returns the type of data contained in the value object.

### AXValueGetTypeID
```c
CFTypeID AXValueGetTypeID(void);
```
Returns the unique type identifier for the AXValue class.

### AXValueGetValue
```c
Boolean AXValueGetValue(
    AXValueRef value, 
    AXValueType type, 
    void *valuePtr
);
```
Copies the data from the value object into the provided buffer.

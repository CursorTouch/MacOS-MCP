# Pi integration notes

This repo can be installed as a Pi package and also includes a project-local Pi extension at `.pi/extensions/macos-mcp/` for local checkout development.

## What the Pi package does

Pi does not include built-in MCP support. The Pi package in this repo starts the existing `macos-mcp` server over stdio and exposes a small set of Pi-native tools that forward to the existing MCP tools.

This PR intentionally keeps macOS-MCP server internals unchanged. It does not add new MCP server tools or alter the desktop/tree/AX modules.

## Pi tools exposed

- `mac_snapshot` -> `Snapshot`
- `mac_app` -> `App`
- `mac_click` -> `Click`
- `mac_type` -> `Type`
- `mac_shortcut` -> `Shortcut`
- `mac_scroll` -> `Scroll`
- `mac_wait` -> `Wait`

## Enable in Pi

One-line global setup:

```bash
pi install git:github.com/CursorTouch/MacOS-MCP
```

Try without installing:

```bash
pi -e git:github.com/CursorTouch/MacOS-MCP
```

Local checkout setup:

```bash
git clone https://github.com/CursorTouch/MacOS-MCP.git
cd MacOS-MCP
uv sync
npm install
pi
```

Pi auto-discovers project extensions under `.pi/extensions/*/index.ts` when run from a local checkout. If Pi is already running, use `/reload`.

If you manually copy the extension somewhere else, set:

```bash
export MACOS_MCP_ROOT=/path/to/MacOS-MCP
```

## Recommended agent pattern

- Use `mac_snapshot` before operating a visible app.
- Use the coordinates returned by Snapshot with `mac_click`, `mac_type`, and `mac_scroll`.
- Use `mac_shortcut` for keyboard workflows such as `command+l`, `command+c`, or `command+space`.
- Use `use_vision=true` only when Accessibility text/coordinates are missing or ambiguous.

## Future work

Native element-id actions can be explored separately after the macOS-MCP server internals have had careful review.

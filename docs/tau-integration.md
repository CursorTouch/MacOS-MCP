# Tau integration notes

This repo includes a project-local Tau extension at `.tau/extensions/macos-mcp/` for
local checkout development.

## What the extension does

Tau does not include built-in MCP support. The extension starts the existing
`macos-mcp` server over stdio (via `uv run macos-mcp`) and exposes a small set of
Tau-native tools that forward to the existing MCP tools.

This integration intentionally keeps macOS-MCP server internals unchanged. It does
not add new MCP server tools or alter the desktop/tree/AX modules.

## Tau tools exposed

- `mac_snapshot` -> `Snapshot`
- `mac_app` -> `App`
- `mac_click` -> `Click`
- `mac_type` -> `Type`
- `mac_shortcut` -> `Shortcut`
- `mac_scroll` -> `Scroll`
- `mac_wait` -> `Wait`

## Enable in Tau

Local checkout setup:

```bash
git clone https://github.com/CursorTouch/MacOS-MCP.git
cd MacOS-MCP
uv sync
tau
```

Tau auto-discovers project extensions under `.tau/extensions/*/manifest.json` when
run from a local checkout, and installs each extension's declared dependencies
(`mcp` here) into the project's `.venv` on first load. If Tau is already running,
use `/reload`.

`/extensions` won't list `macos-mcp` — that picker only shows extensions with an
explicit entry in `settings.json`'s `extensions.list`, not ones auto-discovered from
`.tau/extensions/`. Don't add one manually either: Tau's extension loader treats
`settings.json` entries as a separate, unranked source that loads *in addition to*
an auto-discovered copy rather than replacing it, so doing so would load this
extension twice and collide on tool names. To confirm the tools are registered,
check `/reload` output or ask the agent to list its available tools.

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

Native element-id actions can be explored separately after the macOS-MCP server
internals have had careful review.

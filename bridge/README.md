# mcp-stdio-bridge

A lightweight stdio-to-HTTP bridge for MCP servers, replacing `npx mcp-remote`.

## Why

Claude Desktop only supports stdio MCP servers in its config file. When your
MCP server runs as a shared HTTP daemon (as macOS-MCP does), you need a bridge
process to translate between stdio and HTTP. The standard solution is
`npx mcp-remote`, which spawns a Node.js process (~100 MB RSS each). With
multiple Claude Desktop instances, that adds up fast.

This directory provides two purpose-built alternatives:

| Bridge | Binary size | RSS per instance | Dependencies |
|--------|------------|-----------------|--------------|
| **Swift** (`mcp-stdio-bridge`) | 90 KB | ~3-5 MB | None (native macOS) |
| **Python** (`mcp-stdio-bridge.py`) | 8 KB | ~15-20 MB | Python 3.11+ (already required by macOS-MCP) |
| `npx mcp-remote` | 788 KB + Node.js | ~100 MB | Node.js 18+ |

## Features

Both bridges implement the same design (baseline: mootx01-ce proxy.rs):

- Concurrent frame forwarding (slow tool calls don't block other requests)
- MCP Streamable HTTP session management (MCP-Session-Id tracking)
- SSE response parsing (text/event-stream data: lines)
- Synthesized JSON-RPC errors with id echo on failure (Claude Desktop
  rejects id:null error frames)
- 4 MB frame cap, 16 concurrent request cap (configurable)
- Startup health check with 30s wait for server readiness
- All logging to stderr; stdout reserved for JSON-RPC frames only

## Build (Swift)

```bash
swiftc -O -o mcp-stdio-bridge MCPStdioBridge.swift
```

## Claude Desktop config

### Swift (recommended)

```json
{
  "mcpServers": {
    "macos-mcp": {
      "command": "/path/to/bridge/mcp-stdio-bridge",
      "args": ["--url", "http://127.0.0.1:8765/mcp"]
    }
  }
}
```

### Python

```json
{
  "mcpServers": {
    "macos-mcp": {
      "command": "python3",
      "args": ["/path/to/bridge/mcp-stdio-bridge.py",
               "--url", "http://127.0.0.1:8765/mcp"]
    }
  }
}
```

## Options

```
--url URL              MCP endpoint (default: http://127.0.0.1:8765/mcp)
--timeout SECONDS      Per-request timeout (default: 3600)
--max-concurrent N     Max in-flight frames (default: 16)
```

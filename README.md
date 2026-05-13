<div align="center">
  <h1>🍎 macOS-MCP</h1>

  <a href="https://github.com/Jeomon/macos-mcp/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  </a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/platform-macOS%2012%2B-blue" alt="Platform: macOS 12+">
  <img src="https://img.shields.io/github/last-commit/Jeomon/macos-mcp" alt="Last Commit">

</div>

## Overview

**macOS-MCP** is a lightweight, open-source Model Context Protocol server that bridges AI agents and the macOS operating system. It enables seamless automation of macOS through LLMs via tasks such as **file navigation, application control, UI interaction, browser automation**, and system operations.

## Supported Operating Systems

- macOS 12 (Monterey)
- macOS 13 (Ventura)
- macOS 14 (Sonoma)
- macOS 15 (Sequoia)

## Key Features

- **Works with Any LLM** (Vision Optional)  
  Unlike traditional automation tools, macOS-MCP doesn't require computer vision, fine-tuned models, or specialized setup. Works seamlessly with any LLM—Claude, GPT, Gemini, or others.

- **Native macOS Integration**  
  Interacts natively with macOS UI elements using the Accessibility API. Opens apps, controls windows, simulates user input, and captures desktop state without workarounds.

- **Rich Toolset for Automation**  
  Complete toolkit for keyboard/mouse operations, window management, UI state capture, interactive element extraction from the accessibility tree, and AppleScript execution.

- **Lightweight and Open-Source**  
  Minimal dependencies with full source code available under MIT license. Easy setup and deployment.

- **Smart Context Awareness**  
  Automatically detects application state (Launchpad, Control Center, Spotlight). Scans menu bar, dock, desktop, and system UI elements intelligently.

- **Customizable and Extensible**  
  Easily extend with custom tools or modify behavior to suit your specific automation needs.

## Installation

### Prerequisites

- **Python**: 3.11 or later
- **UV Package Manager**: Install with `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **macOS**: 12 (Monterey) or later
- **Accessibility Permissions**: Required for UI element interaction

### Quick Start

Run the server directly:

```shell
uvx macos-mcp

# Or with SSE/Streamable HTTP for network access
uvx macos-mcp --transport sse --host localhost --port 8000
uvx macos-mcp --transport streamable-http --host localhost --port 8000
```

Run it as a background service that starts now and at every login:

```shell
macos-mcp install

# Or choose the HTTP transport and bind address explicitly
macos-mcp install --transport sse --host 127.0.0.1 --port 8000
```

This installs a `launchd` Launch Agent at `~/Library/LaunchAgents/com.macos-mcp.server.plist`.
Use `macos-mcp uninstall` to remove it. Logs are written to `~/.macos-mcp/server.log`
and `~/.macos-mcp/server.error.log`.

### Transport Options

| Transport | Flag | Use Case |
|---|---|---|
| `stdio` (default) | `--transport stdio` | Direct connection from MCP clients like Claude Desktop, Cursor, etc. |
| `sse` | `--transport sse --host HOST --port PORT` | Network-accessible via Server-Sent Events |
| `streamable-http` | `--transport streamable-http --host HOST --port PORT` | Network-accessible via HTTP streaming (recommended for production) |

### Grant Required Permissions

macOS-MCP requires **Accessibility** and **Screen Recording** permissions to function properly.

#### Accessibility Permissions

1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Click the lock icon and authenticate
3. Add the following applications:
   - Your terminal application (Terminal, iTerm2, VS Code, etc.)
   - Python (typically `/usr/bin/python3` or the Python version managed by UV)
   - UV (`~/.local/bin/uv` if installed locally, or the Python environment UV manages)
4. Restart the terminal after granting permissions

**For `uvx` users:** Grant permissions to your terminal application and Python, as `uvx` runs Python packages from UV's cache.

#### Screen Recording Permissions

The `Snapshot` tool requires Screen Recording permissions to capture screenshots:

1. Open **System Settings** → **Privacy & Security** → **Screen Recording**
2. Click the lock icon and authenticate
3. Add the same applications as above (terminal, Python, UV)
4. Restart the terminal after granting permissions

**Note:** If the `Snapshot` tool fails, verify both permissions are granted in System Settings.

### Integration Options

<details>
  <summary><strong>Claude Desktop</strong></summary>

  1. Install [Claude Desktop](https://claude.ai/download)

  2. Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:
  ```json
  {
    "mcpServers": {
      "macos-mcp": {
        "command": "uvx",
        "args": ["macos-mcp"]
      }
    }
  }
  ```

  3. Restart Claude Desktop

</details>

<details>
  <summary><strong>Gemini CLI</strong></summary>

  1. Install Gemini CLI:
  ```shell
  npm install -g @google/gemini-cli
  ```

  2. Navigate to `~/.gemini` and open `settings.json`

  3. Add the server config:
  ```json
  {
    "theme": "Default",
    "mcpServers": {
      "macos-mcp": {
        "command": "uvx",
        "args": ["macos-mcp"]
      }
    }
  }
  ```

  4. Restart Gemini CLI

</details>

<details>
  <summary><strong>Claude Code</strong></summary>

  1. Install [Claude Code](https://claude.com/claude-code)

  2. Add to your project configuration or use the MCP marketplace integration

</details>

<details>
  <summary><strong>Pi Agent</strong></summary>

  Pi does not ship with built-in MCP support, but macOS-MCP can be installed as a Pi package. The package starts this MCP server over stdio and exposes convenient Pi tools that wrap the existing macOS-MCP tools.

  **One-line global setup:**

  ```shell
  pi install git:github.com/CursorTouch/MacOS-MCP
  ```

  After install, restart Pi or run:

  ```text
  /reload
  ```

  **Try without installing:**

  ```shell
  pi -e git:github.com/CursorTouch/MacOS-MCP
  ```

  **Local checkout setup:**

  ```shell
  git clone https://github.com/CursorTouch/MacOS-MCP.git
  cd MacOS-MCP
  uv sync
  npm install
  pi
  ```

  If you copied only the extension into another Pi project, run Pi from the macOS-MCP checkout or set:

  ```shell
  export MACOS_MCP_ROOT=/path/to/MacOS-MCP
  ```

  The extension exposes these Pi tools:

  | Pi Tool | Purpose |
  |---------|---------|
  | `mac_snapshot` | Read current macOS UI state through the existing Snapshot tool. |
  | `mac_app` | Launch, switch, move, or resize macOS applications/windows. |
  | `mac_click` | Click coordinates returned by `mac_snapshot`. |
  | `mac_type` | Type text at coordinates returned by `mac_snapshot`. |
  | `mac_shortcut` | Run keyboard shortcuts such as `command+c` or `command+space`. |
  | `mac_scroll` | Scroll at the current pointer or coordinates. |
  | `mac_wait` | Wait for UI changes/loading. |

  Recommended agent workflow:
  - Call `mac_snapshot` first.
  - Use the coordinates returned by Snapshot with `mac_click`, `mac_type`, and `mac_scroll`.
  - Use screenshots/vision only when Accessibility data is missing or ambiguous.

  The extension auto-detects the macOS-MCP checkout when installed as a Pi package. If you use a manually copied extension, set `MACOS_MCP_ROOT=/path/to/MacOS-MCP`.

</details>

<details>
  <summary><strong>Other Integrations</strong></summary>

  Any client supporting the Model Context Protocol can integrate macOS-MCP by configuring the `uvx macos-mcp` command in their MCP server settings.

</details>

---

## MCP Tools

macOS-MCP provides a comprehensive toolset for desktop automation:

| Tool | Purpose |
|------|---------|
| **Click** | Click at coordinates with support for left, right, and double-click |
| **Type** | Type text at cursor position, optionally clearing existing text |
| **Scroll** | Scroll vertically or horizontally in focused window or regions |
| **Move** | Move mouse pointer or drag to coordinates |
| **Shortcut** | Press keyboard shortcuts (Cmd+C, Cmd+Tab, etc.) |
| **App** | Launch applications, manage windows (resize/move), switch between apps. Supports app names and bundle IDs |
| **Shell** | Execute commands or AppleScript. Use `mode='osascript'` for AppleScript |
| **Scrape** | Extract and convert webpage content to Markdown format |
| **Wait** | Pause execution for a defined duration |

## Limitations

- **Accessibility Requirements**: Manual permission grant required in System Preferences
- **App Compatibility**: Some applications have limited or no Accessibility API support
- **Performance Variance**: Complex UIs with many elements may have slower traversal
- **Text Input**: Some specialized input fields may not properly receive keystrokes
- **Authentication**: Cannot interact with system authentication dialogs

## Security & Access Control

### Authentication
```shell
macos-mcp --transport sse --host 0.0.0.0 --auth-key "your_token"
```
Requires `Authorization: Bearer your_token` header on all requests.

### IP Allowlist
```shell
macos-mcp --auth-key "token" --ip-allowlist "203.0.113.0/24,198.51.100.5"
```
Restricts connections to specified CIDR ranges.

### TLS/HTTPS
```shell
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

macos-mcp --ssl-certfile cert.pem --ssl-keyfile key.pem
```

### OAuth 2.0 + PKCE

For MCP clients that use OAuth (e.g. Claude Desktop) instead of a static API key:

```shell
macos-mcp --transport streamable-http --host 0.0.0.0 \
  --ssl-certfile ~/.macos-mcp/cert.pem \
  --ssl-keyfile  ~/.macos-mcp/key.pem \
  --oauth-client-id my-client \
  --oauth-client-secret my-secret
```

**Claude Desktop config:**
```json
{
  "mcpServers": {
    "macos-mcp": {
      "type": "http",
      "url": "https://<host>:8000/mcp/",
      "oauth": {
        "clientId": "my-client",
        "clientSecret": "my-secret"
      }
    }
  }
}
```

The OAuth server exposes:
- `GET /.well-known/oauth-authorization-server` — server metadata (RFC 8414)
- `GET /oauth/authorize` — Authorization Code + PKCE (`S256` required)
- `POST /oauth/token` — token exchange (client secret required)
- `POST /oauth/register` — disabled; clients must be pre-provisioned

Dynamic client registration is disabled. Redirect URIs must be loopback `http(s)` only.
Auth key and OAuth can coexist — both are accepted as valid Bearer tokens.

### SSRF Protection
The `Scrape` tool blocks: private IPs, loopback, link-local, credentials-in-URLs, non-HTTP schemes.

### Config File (`~/.macos-mcp/config.toml`)

Instead of passing flags every time, store your configuration in `~/.macos-mcp/config.toml`. CLI flags always override config file values.

**Search order:**
1. `--config /path/to/config.toml`
2. `~/.macos-mcp/config.toml`

**stdio** — local only, no security needed:
```toml
[server]
transport = "stdio"
```

**SSE** — network access with auth and IP restriction:
```toml
[server]
transport = "sse"
host      = "0.0.0.0"
port      = 8000
auth_key  = "your-secret-key"

[security]
ip_allowlist = ["192.168.1.0/24"]
```

**Streamable HTTP** — network access with auth and TLS (recommended for production):
```toml
[server]
transport    = "streamable-http"
host         = "0.0.0.0"
port         = 8000
auth_key     = "your-secret-key"
ssl_certfile = "cert.pem"   # resolved relative to ~/.macos-mcp/
ssl_keyfile  = "key.pem"

[security]
ip_allowlist        = ["192.168.1.0/24"]
oauth_client_id     = "my-client"      # optional — enables OAuth 2.0 + PKCE
oauth_client_secret = "my-secret"

[tools]
exclude = ["Shell", "Scrape"]   # disable specific tools
```

Available tool names: `App`, `Shell`, `Snapshot`, `Click`, `Type`, `Scroll`, `Move`, `Shortcut`, `Wait`, `Scrape`, `Notification`

Place your cert and key files in the same directory:

```
~/.macos-mcp/
├── config.toml
├── cert.pem
└── key.pem
```

Generate a self-signed cert directly into that directory:

```shell
mkdir -p ~/.macos-mcp
openssl req -x509 -newkey rsa:4096 \
  -keyout ~/.macos-mcp/key.pem \
  -out ~/.macos-mcp/cert.pem \
  -days 365 -nodes
```

---

## Environment Variables

All variables are optional. Set them via the `env` key in `claude_desktop_config.json`.

| Variable | Default | Description |
|---|---|---|
| `ANONYMIZED_TELEMETRY` | `true` | Set to `false` to disable anonymous usage telemetry. No personal data, tool arguments, or outputs are ever collected. |
| `MACOS_MCP_AUTH_KEY` | _(none)_ | Bearer token required on all HTTP requests. Alternative to `--auth-key` CLI flag. |
| `MACOS_MCP_IP_ALLOWLIST` | _(none)_ | Comma-separated list of allowed client IPs or CIDR ranges. Alternative to `--ip-allowlist` CLI flag. |
| `MACOS_MCP_SSL_CERTFILE` | _(none)_ | Path to TLS certificate file (.pem). Must be provided with `MACOS_MCP_SSL_KEYFILE`. |
| `MACOS_MCP_SSL_KEYFILE` | _(none)_ | Path to TLS private key file (.pem). Must be provided with `MACOS_MCP_SSL_CERTFILE`. |

**Example `claude_desktop_config.json` (remote with auth + TLS):**
```json
{
  "mcpServers": {
    "macos-mcp": {
      "command": "uvx",
      "args": ["macos-mcp", "--transport", "sse", "--host", "0.0.0.0"],
      "env": {
        "MACOS_MCP_AUTH_KEY": "your_token",
        "MACOS_MCP_IP_ALLOWLIST": "203.0.113.0/24",
        "MACOS_MCP_SSL_CERTFILE": "/path/to/cert.pem",
        "MACOS_MCP_SSL_KEYFILE": "/path/to/key.pem"
      }
    }
  }
}
```

---

## Telemetry

macOS-MCP collects anonymous usage data to help improve the server. No personal information, tool arguments, or outputs are tracked.

To disable telemetry, set `ANONYMIZED_TELEMETRY` to `false`:

```json
{
  "mcpServers": {
    "macos-mcp": {
      "command": "uvx",
      "args": ["macos-mcp"],
      "env": { "ANONYMIZED_TELEMETRY": "false" }
    }
  }
}
```

---

## Security

⚠️ **Important Security Notice**: macOS-MCP operates with full Accessibility API permissions and executes real system operations without sandboxing. It can perform permanent, irreversible actions.

**Before using macOS-MCP:**

- ✅ Grant Accessibility permissions only to trusted applications
- ✅ Understand that Shell commands execute with full user privileges
- ✅ Review AI-generated action plans before execution
- ✅ Use only in virtual machines or isolated environments with valueless data
- ✅ Create backups before testing in production-like scenarios

**⛔ Do NOT use on:**
- Systems with irreplaceable data
- Production machines or shared systems
- Compliance-regulated environments (HIPAA, PCI, etc.)

For detailed security guidance, see [SECURITY.md](SECURITY.md).

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup and code standards
- Testing requirements
- Pull request process
- Coding conventions (Ruff formatting, 100 char line length)

## License

macOS-MCP is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgements

macOS-MCP is built with excellent open-source projects:

- [PyObjC](https://pyobjc.readthedocs.io/) - Python to Objective-C bridge
- [Pillow](https://pillow.readthedocs.io/) - Python Imaging Library
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP framework
- macOS Accessibility API (ApplicationServices)

## Citation

If you use macOS-MCP in your research or project, please cite:

```bibtex
@software{macos-mcp,
  author       = {Jeomon George},
  title        = {macOS-MCP: Lightweight MCP Server for macOS Automation},
  year         = {2025},
  publisher    = {GitHub},
  url          = {https://github.com/Jeomon/macos-mcp}
}
```

---

**Questions or Issues?** [Open an issue](https://github.com/Jeomon/macos-mcp/issues) or check [SECURITY.md](SECURITY.md) for security concerns.

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
```

### Grant Accessibility Permissions

macOS-MCP requires Accessibility permissions to interact with UI elements:

1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Click the lock icon and authenticate
3. Add your terminal application (Terminal, iTerm2, VS Code, etc.)
4. Restart the terminal after granting permissions

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
| **Snapshot** | Capture desktop state with interactive elements and coordinates. Set `use_vision=True` for annotated screenshots |
| **App** | Launch applications, manage windows (resize/move), switch between apps. Supports app names and bundle IDs |
| **Shell** | Execute shell commands or AppleScript. Use `mode='osascript'` for AppleScript |
| **Scrape** | Extract and convert webpage content to Markdown format |
| **Wait** | Pause execution for a defined duration |

## Limitations

- **Accessibility Requirements**: Manual permission grant required in System Preferences
- **App Compatibility**: Some applications have limited or no Accessibility API support
- **Performance Variance**: Complex UIs with many elements may have slower traversal
- **Text Input**: Some specialized input fields may not properly receive keystrokes
- **Authentication**: Cannot interact with system authentication dialogs

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

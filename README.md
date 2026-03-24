<div align="center">
  <h1>🍎 MacOS-MCP</h1>

  <a href="https://github.com/Jeomon/macos-mcp/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  </a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/platform-macOS%2012%2B-blue" alt="Platform: macOS 12+">
  <img src="https://img.shields.io/github/last-commit/Jeomon/macos-mcp" alt="Last Commit">

</div>

<br>

**macOS-MCP** is a lightweight, open-source project that enables seamless integration between AI agents and the macOS operating system. Acting as an MCP server, it bridges the gap between LLMs and macOS, allowing agents to perform tasks such as **file navigation, application control, UI interaction, browser automation,** and more.

## Supported Operating Systems

- macOS 12 (Monterey)
- macOS 13 (Ventura)
- macOS 14 (Sonoma)
- macOS 15 (Sequoia)

## Key Features

- **Seamless macOS Integration**  
  Interacts natively with macOS UI elements using the Accessibility API, opens apps, controls windows, simulates user input, and more.

- **Use Any LLM (Vision Optional)**  
  Unlike many automation tools, macOS-MCP doesn't rely on traditional computer vision techniques or specific fine-tuned models. It works with any LLM, reducing complexity and setup time.

- **Rich Toolset for UI Automation**  
  Includes tools for keyboard and mouse operations, capturing window/UI state, and extracting interactive elements from the accessibility tree.

- **Lightweight and Open-Source**  
  Minimal dependencies and easy setup with full source code available under MIT license.

- **Customizable and Extendable**  
  Easily adapt or extend tools to suit your unique automation or AI integration needs.

- **Support for Launchpad and System UI**  
  Automatically detects when Launchpad is open and adjusts scanning behavior accordingly. Scans Control Center, Spotlight, and menu bar elements.

## Installation

### Prerequisites

- Python 3.11+
- UV (Package Manager) from Astral, install with `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Accessibility permissions granted to the terminal or application running the MCP server

### Quick Start

Run the server directly with:

```shell
uvx macos-mcp
```

### Grant Accessibility Permissions

macOS-MCP requires Accessibility permissions to interact with UI elements:

1. Open **System Settings** > **Privacy & Security** > **Accessibility**
2. Click the lock icon and authenticate
3. Add your terminal application (Terminal, iTerm2, VS Code, etc.)
4. Restart the terminal after granting permissions

<details>
  <summary>Install in Claude Desktop</summary>

  1. Install [Claude Desktop](https://claude.ai/download)

  2. Add this to your `claude_desktop_config.json`:
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
  <summary>Install in Gemini CLI</summary>

  1. Install Gemini CLI:
  ```shell
  npm install -g @google/gemini-cli
  ```

  2. Navigate to `~/.gemini` and open `settings.json`

  3. Add the `macos-mcp` config:
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

---

## MCP Tools

MCP Client can access the following tools to interact with macOS:

| Tool | Description |
|------|-------------|
| `Click` | Click on the screen at the given coordinates. Supports left, right, and double-click. |
| `Type` | Type text at the current cursor position. Optionally clears existing text first. |
| `Scroll` | Scroll vertically or horizontally on the focused window or specific regions. |
| `Move` | Move mouse pointer or drag (set drag=True) to coordinates. |
| `Shortcut` | Press keyboard shortcuts (Cmd+C, Cmd+Tab, etc). |
| `Wait` | Pause execution for a defined duration. |
| `Snapshot` | Capture desktop state including active window, open applications, interactive elements with coordinates, and scrollable areas. Set `use_vision=True` to include annotated screenshots. |
| `App` | Launch an application, resize/move windows, or switch between apps. Supports bundle IDs and app names. |
| `Shell` | Execute shell commands or AppleScript. Use `mode='osascript'` for AppleScript execution. |
| `Scrape` | Extract and convert webpage content to Markdown format. |

## Architecture

```
macos-mcp/
├── src/
│   └── macos_mcp/
│       ├── __init__.py
│       ├── __main__.py          # MCP server entry point and tool definitions
│       ├── desktop/
│       │   ├── __init__.py
│       │   ├── service.py       # Desktop automation service
│       │   ├── views.py         # Data classes for desktop state
│       │   └── config.py        # Configuration constants
│       └── tree/
│           ├── __init__.py
│           ├── service.py       # Accessibility tree traversal
│           ├── views.py         # Data classes for tree elements
│           └── config.py        # Interactive roles and actions
├── pyproject.toml
└── README.md
```

## How It Works

1. **Accessibility Tree Traversal**: Uses macOS Accessibility API (`ApplicationServices`) to traverse UI elements and extract interactive components.

2. **Parallel Scanning**: Scans multiple sources concurrently:
   - Focused application window
   - Dock
   - Menu bar
   - Control Center
   - SystemUIServer
   - Spotlight
   - Desktop icons (when visible)

3. **Smart Context Awareness**:
   - Detects Launchpad state and adjusts scanning
   - Only shows desktop icons when no window is focused
   - Filters out background services to show only user-facing apps

4. **Screenshot Annotations**: When `use_vision=True`, generates screenshots with numbered bounding boxes on interactive elements for visual reference.

## Limitations

- Requires Accessibility permissions to be granted manually
- Some applications may have limited accessibility support
- Performance may vary based on the complexity of the UI and number of open applications

## Security

**Important**: macOS-MCP operates with accessibility access and can perform system-level operations. Please review the following before deployment:

- Grant accessibility permissions only to trusted applications
- Be cautious when using Shell tool with elevated commands
- Review and understand the actions being performed by AI agents

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

macOS-MCP makes use of several excellent open-source projects and macOS frameworks:

- [PyObjC](https://pyobjc.readthedocs.io/) - Python to Objective-C bridge
- [PyAutoGUI](https://github.com/asweigart/pyautogui) - Cross-platform GUI automation
- [Pillow](https://pillow.readthedocs.io/) - Python Imaging Library
- macOS Accessibility API (ApplicationServices)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Citation

```bibtex
@software{
  author       = {Jeomon},
  title        = {macOS-MCP: Lightweight open-source project for integrating LLM agents with macOS},
  year         = {2025},
  publisher    = {GitHub},
  url          = {https://github.com/Jeomon/macos-mcp}
}
```

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.11] - 2026-07-15

### Added
- Add a desktop-state capture profiling utility (`python -m macos_mcp.profiling.desktop_state`) with layer-by-layer, per-app, and vision-overhead timing breakdowns, plus `--save-screenshot` to save the last annotated capture to disk
- Add a desktop creation tool that opens a new Mission Control Space via Accessibility-based automation of the Dock's Mission Control UI

### Changed
- Speed up desktop state capture (roughly 3-4x locally, both with and without vision): skip re-scanning an app's menu bar when a windowless app (e.g. Spotlight) reports it again as a top-level child during the windowless fallback scan; skip descending into closed (0-size) `AXMenu` submenus since a closed menu can never contain a visible/interactive element; remove an unconditional 50ms sleep from `get_foreground_window`

### Fixed
- Notification tool no longer fails for non-ASCII text (CJK, emoji): pass `ensure_ascii=False` to `json.dumps` when building the `display notification` AppleScript, since AppleScript string literals don't support `\uXXXX` escapes (#27)
- Extension no longer exits at startup under Claude Desktop: `manifest.json`/`server.json` now set `MACOS_MCP_SKIP_PERMISSION_CHECK=1` by default so the published extension can reach the existing warn-instead-of-exit escape hatch when `AXIsProcessTrustedWithOptions()` reports false for a disclaimed subprocess even though the host's own grant is inherited; skip mode also suppresses the focus-stealing System Preferences popup (#26)

### Contributors
- Jeomon George (@jeomon) — desktop creation tool, notification/extension startup fixes, and release management
- claude — desktop-state capture profiling utility and the tree-traversal/focus-detection performance fixes in this release

## [0.3.10] - 2026-07-08

### Fixed
- Auto-register process for Accessibility permission via native `AXIsProcessTrustedWithOptions` prompt on startup, working around uv-managed Python interpreter binaries appearing greyed out/unselectable in the System Settings "+" picker (#22)

## [0.3.9] - 2026-07-07

### Added
- Implement Tau extension for macOS-MCP with comprehensive documentation structure
- Add support for macOS 26 (Tahoe) and macOS 27 (Golden Gate)
- Initialize tau settings configuration

### Fixed
- Fix screenshot capture on macOS 15+ by falling back to screencapture CLI (#24)
- Throttle EventObserver app re-scan to cut idle CPU usage (#20)
- Fix AXWindows/AXMainWindow/AXFocusedWindow role misclassification
- Drain autorelease pools on secondary AX threads to prevent memory leaks
- Add safe integer conversion to bounding box coordinates to handle non-finite values
- Plug AXObserver memory leak in EventObserver
- Resolve issues preventing v0.3.7 from running as a Claude Desktop extension

### Changed
- Refactor macOS-MCP extension removal
- Update entry point to serve and switch shell execution to bash
- Add permission check override for subprocess compatibility

### Contributors
- Jeomon George (@jeomon)
- Brendan Smith (@brendancsmith)
- Howie Levy IONQ IT
- kinjung
- claude
- Richardson Gunde (@Austin519)

## [0.3.8] - 2026-06-16

### Added
- Initial release with core macOS automation capabilities
- Accessibility API integration for native UI interaction
- Complete toolset for keyboard/mouse operations, window management
- UI state capture and interactive element extraction
- AppleScript execution support

[0.3.11]: https://github.com/Jeomon/MacOS-MCP/compare/v0.3.10...v0.3.11
[0.3.10]: https://github.com/Jeomon/MacOS-MCP/compare/v0.3.9...v0.3.10
[0.3.9]: https://github.com/Jeomon/MacOS-MCP/compare/v0.3.8...v0.3.9
[0.3.8]: https://github.com/Jeomon/MacOS-MCP/releases/tag/v0.3.8
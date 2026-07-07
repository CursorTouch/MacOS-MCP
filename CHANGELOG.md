# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[0.3.9]: https://github.com/Jeomon/MacOS-MCP/compare/v0.3.8...v0.3.9
[0.3.8]: https://github.com/Jeomon/MacOS-MCP/releases/tag/v0.3.8
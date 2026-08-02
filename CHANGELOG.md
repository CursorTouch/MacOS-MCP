# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Release builds now verify that every declared version string agrees before publishing. `scripts/check_versions.py` compares `pyproject.toml`, `uv.lock`, `manifest.json`, `package.json` and `server.json` (twice) against each other and against the release tag, and `publish.yml` runs it ahead of the build so a mismatched tag fails before anything reaches PyPI — the drift that caused #32 would have been blocked at 0.3.9
- Character-range access to text controls, the macOS counterpart to the Windows Text Object Model. `TextRange` (in `macos_mcp.ax.text`) exposes `text`, `attributed_text`, `bounds`, `expand_to_line`, `expand_to_style`, `select` and `replace`; `Control` gains `SupportsTextRanges`, `FullTextRange`, `SelectionRange`, `LineRange`, `RangeAtPoint` and `TextAround`. `bounds` converts a character offset into screen coordinates, so text can be located without a screenshot, and `TextAround` reads the text surrounding the caret directly. Support varies by application and is probed rather than assumed, with every accessor degrading to `None`/`""`
- Per-word bounding boxes for text controls via `Control.WordBoundingBoxes()`, the macOS counterpart to Windows-MCP's `GetAllWordBoundingBoxes`. Returns one entry per whitespace-delimited token with one `Rect` per line it occupies, so every word in an editable element becomes an addressable screen target without a screenshot. Words that soft-wrap are clipped per line first, because `AXBoundsForRange` otherwise collapses a multi-line range into a single union rectangle spanning the full column width. Boxes are trimmed from the line box down to the glyph height using the font size read from `AXAttributedStringForRange`; pass `shrink_to_font=False` to keep the raw line rects. Returns `None` where the control does not advertise `AXBoundsForRange`, rather than fabricating a zero-area box whose centre is a real screen coordinate
- 56 accessibility constants that live applications report but the enums never declared: 49 attributes, 4 subroles and 3 actions. Notably `AXDisclosing`, without which the already-declared `AXDisclosedRows`/`AXDisclosedByRow`/`AXDisclosureLevel` cannot be interpreted — it is the one that says whether an outline row is currently expanded. Also `AXActivationPoint`, `AXFrontmost`, `AXEdited`, `AXRequired`, `AXInvalid`, `AXCustomActions`, `AXSelectedCells`, `AXOwns`, the ARIA/DOM attributes, the `AXSegment`/`AXToggleButton`/`AXMenuExtra` subroles and the `AXOpen`/`AXZoomWindow`/`AXScrollToVisible` actions. Each is grouped by provenance — documented in ApplicationServices, documented via NSAccessibility, or observed on live elements but absent from any public header — since the last group is best-effort and will be missing more often

### Changed
- Accessibility permission failures now name the process that needs the grant (`sys.executable`) instead of just the permission. The message also points at the native "would like to control this computer" consent dialog as the reliable fix, and warns against adding the interpreter by hand in the System Settings "+" picker, which is greyed out for uv-managed Python and breaks on the next uv update (#32)

### Fixed
- Parameterized accessibility attributes now use their real names. All 13 values in `Attribute` carried a `Parameterized` suffix, which belongs to the constant name in Apple's headers (`kAXStringForRangeParameterizedAttribute`) but not to the string it expands to (`AXStringForRange`), so every parameterized call returned `kAXErrorParameterizedAttributeUnsupported` (-25213). `Control.GetTextFromMarkers` — the only caller — consequently always returned an empty string; against a live `AXWebArea` it now returns the page text instead of nothing
- Attributed-string keys now use their real names. 16 of the 20 values in `TextAttribute` carried a `Text` suffix which, as with the parameterized attributes, belongs to the constant name in Apple's headers (`kAXFontTextAttribute`) but not to the string it expands to (`AXFont`). Every lookup against them missed, so font, colour, underline, strikethrough, superscript, link and spell-check information was unreadable from `AXAttributedStringForRange`. The four font sub-keys (`AXFontFamily`, `AXFontName`, `AXFontSize`, `AXVisibleName`) index into the nested `AXFont` dictionary and were already correct. Adds `TextAlignment` (`AXATextAlignmentValue`), which was missing entirely
- Tabs are now identified correctly. `Role.Tab` was `"AXTab"`, a role macOS never reports — an individual tab is an `AXRadioButton` carrying the `AXTabButton` subrole — so `Control.TabControl()` could never match anything and the control factory mapped real tabs to `RadioButtonControl`. The finder now searches by subrole and the factory maps `AXRadioButton`/`AXTabButton` to `TabControl`; the subrole is only fetched for radio buttons, so traversal cost is unchanged for every other element. `Role.Tab` has been removed, since keeping an unusable constant only invites reuse

## [0.3.12] - 2026-08-01

### Fixed
- Packaging metadata no longer ships a stale version. `manifest.json` (0.3.8), `package.json` (0.3.5), and `server.json` (0.3.6) had drifted behind `pyproject.toml`, because the 0.3.9, 0.3.10, and 0.3.11 release commits bumped only the Python package version. The published Claude Desktop extension therefore kept advertising and installing 0.3.8 — which predates the 0.3.10 `AXIsProcessTrustedWithOptions` startup prompt — so affected users could never reach the version that requests Accessibility access, and had no update path short of installing from PyPI by hand (#32)

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
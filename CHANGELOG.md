# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-08-13

### Added
- A native stdio-to-HTTP bridge, in Swift and in Python, replacing `npx mcp-remote`. Claude Desktop's config only accepts stdio MCP servers, so reaching a running HTTP server needs a bridge, and mcp-remote costs a Node process at roughly 100 MB RSS for each one. The Swift bridge is a 90 KB binary at 3-5 MB RSS with no dependencies; the Python companion is an 8 KB stdlib-only script at 15-20 MB RSS, for machines without the Xcode command line tools. Both forward frames concurrently, so a slow tool call no longer blocks every other request, track `Mcp-Session-Id` for Streamable HTTP, parse SSE responses, and synthesise JSON-RPC errors with the request id echoed back. `scripts/stdio-to-http-reconfig.sh` configures the Swift bridge and compiles it with `--build`; `scripts/stdio-to-http-reconfig-python.sh` does the same for the Python one
- `macos-mcp install` chooses a free port instead of assuming 8000. That port is a common default for local inference servers such as LM Studio and oMLX, and when it was already taken the launchd service crashed on every KeepAlive restart with `EADDRINUSE`. Without an explicit `--port` the installer now probes upward from 8000 and says which port it settled on; `stdio-to-http-reconfig.sh --install-server` does the same and derives the bridge URL from the chosen port, so the two stay in sync. An explicit `--port N` is still honoured exactly as given
- `MacOS-MCP.app`, a frozen bundle that gives macOS one stable identity to attribute privacy grants to (#25). Claude Desktop launches the server through `uv`, and neither uv nor the interpreter it manages carries a Developer ID, so TCC cannot roll them up: Accessibility and Automation grants appear as separate icon-less `uv`, `python3` and `node` rows, and being ad-hoc signed they are re-signed on every upgrade, which invalidates the grants and leaves stale duplicates behind. Wrapping `uv` in a bundle does not work, because the first launch creates a `.venv` inside `Contents/Resources` and invalidates the signature — 2.1 MB becomes 321 MB and codesign reports hundreds of added files. Freezing does work: nothing is written at runtime, so the signature survives, and no uv or system python is left in the process tree. Built with `scripts/build/build_app.sh`, with `LSUIElement` configurable so the bundle can run without a Dock icon
- Menu items now report their keyboard shortcut. `AXMenuItemCmdChar`, `AXMenuItemCmdModifiers` and `AXMenuItemCmdVirtualKey` are fetched for menu roles alone, so every other element pays nothing for them, and `FormatMenuShortcut` renders them the way the menu does — including the keys that have no printable character, such as ↩, ⇥, ⌫, the arrows and the function keys
- Checkboxes, radio buttons and disclosure triangles report their state separately from their name. `AXValue` on these roles is the state rather than a label, so using it as the name produced a node called "1" — true, and no use to anyone deciding what to click. They now take their name from the linked title element, and a checkbox's value rides in metadata as `checked`, with the third state exposed as `"mixed"`: what a "select all" box shows when only some of its items are ticked
- Pop-up buttons report their current selection in metadata, and a list that carries a title is now treated as interactive
- Grouped notifications are captured. Several notifications from one application collapse into a stack under a second, undocumented subrole, `AXNotificationCenterBannerStack`. Without it only the newest banner of a stack reached a snapshot and the rest were invisible despite being on screen
- Search fields are interactive regardless of role. WhatsApp's chat search reports `AXStaticText`, because the role describes how an element was built while the subrole describes what it is for, so `AXSearchField` joins `INTERACTIVE_SUBROLES`
- `ax.HasAction(element, action)` reports whether an element advertises an action such as `AXPress`. It is a last-resort interactivity signal for web-based UIs, where a clickable control is often a plain `AXGroup` with no role or subrole to identify it. Errors count as "no action" rather than raising, since a dead element mid-traversal should not abort a capture

### Changed
- Every tool handler is now `async`. Under the streamable-http transport a synchronous handler blocks the uvicorn event loop for the whole call, which starves every other connected client and looks from the outside like a server crash — worst with `Shell`, and with anything slow such as `Snapshot` with vision, `Scrape`, `Wait` or desktop space creation. The conversion is three layers: `AsyncExecuteCommand` built on `asyncio.create_subprocess_exec`, keeping the existing safeguards (`DEVNULL` stdin, `start_new_session` for process-group kill, timeout handling); an async wrapper for every `Desktop` method, with PyObjC, AX and Pillow work offloaded to a worker thread; and all twelve tool handlers awaiting them. The synchronous API is untouched, so stdio users and anyone calling `Desktop` directly see no change
- The async `Desktop` wrappers are named `async_*` rather than `*_async`. No release shipped the earlier spelling
- Application packaging moved from a shell script and a C launcher to PyInstaller, under `scripts/build/`

### Fixed
- Objective-C objects no longer accumulate on the async worker threads. PyObjC only installs an autorelease pool automatically on the main thread, so the AX and Quartz work offloaded by the new async API had nothing to drain it, and the same applied to the per-application `get_windows` and menu-bar-extras probes introduced in 0.3.17. Measured over 300 `get_windows()` calls, the process grew 6.19 MB before the fix, linearly and without ever levelling off, against 0.05 MB after; 30 vision-less snapshots grew 1.39 MB against 0.20 MB. Thanks to @git-ksk (#54)
- `Shell` no longer returns less than the command produced. Four separate defects: stderr was discarded whenever stdout was non-empty, so a command that wrote partial output and then failed reported success with the error invisible — the reported case was a missing line whose real message was `md5: command not found`, and both streams are now returned. Output already written was thrown away on timeout and replaced with the bare timeout string, and is now appended under a marker with the original prefix preserved for callers that match on it. A timeout above the host's own ceiling produced no answer at all, since the host abandons the call and closes the stream while the server is still running, so timeouts are clamped to `MACOS_MCP_MAX_TIMEOUT` (240s by default) and the message says when a clamp applied. The async path still captured through pipes, where a backgrounded grandchild inherits the capture descriptors and holds the pipe open after the direct child exits: `echo done; ./sleeper.sh &` with an 8s timeout took the full 8.0s and reported a spurious timeout, and now returns `("done", 0)` immediately with the background job still running
- The bridge no longer drops a request. Any empty-bodied non-202 response was logged and returned without writing a frame, leaving the client waiting on an id that would never be answered — from the outside, the shell command completes and the assistant hangs. The usual way in is a server restart: the new process has never seen the cached `Mcp-Session-Id` and rejects everything after it, and the bridge deliberately survives stdin EOF, so nothing recycled it either. A measured two-second server bounce cost four minutes of dead client. A 400 or 404 with a session cached now clears it, re-handshakes and retries once, which turns that outage into a 15 ms retry; empty and non-2xx responses return a JSON-RPC error frame rather than silence; the log appends instead of truncating, so a respawn no longer erases the record of the failure that caused it; and the default timeout drops from 3600s to 300s, below the host's ceiling
- The bridge waits for in-flight work before exiting. Frames were dispatched to the worker queue asynchronously but stdin EOF exited immediately, so a fast EOF from a pipe close or short input dropped the responses. It also needs `codesign -s -`: swiftc ad-hoc signs its output, but copying the binary elsewhere invalidates that signature and macOS SIGKILLs it on launch. A `--log-file PATH` flag writes timestamped request and response traces — method, id, status, size, latency — without touching stdout

## [0.3.17] - 2026-08-03

### Changed
- The first capture in a process is about 3.2x faster, roughly 1290ms down to 420ms. The cost was first contact with each application: the first accessibility call to a process takes around 8ms because the connection has to be established, while later calls take microseconds, and two functions asked every one of the ~50 running applications in turn — `_bundles_with_menu_bar_extras` at 0.80s and `get_windows` at 0.46s. Both now probe concurrently. Captures after the first are unchanged at around 75ms, and the output is identical

## [0.3.16] - 2026-08-03

### Added
- Menu bar extras owned by background applications are now captured. Status icons for tools like Docker, Ollama, LM Studio and Claude belong to their own process, which is neither frontmost nor system UI, so nothing ever asked them and their icons never reached a snapshot. Applications owning a non-empty `AXExtrasMenuBar` are now discovered and scanned — only their extras menu bar, since walking their full window tree would cost far more than the single node they contribute. Discovery is cached against the set of running process ids, so a repeat capture pays 0.15 ms rather than 7.36 ms
- Menu bar extras with no name are labelled with the owning application's name. They are pure icons with no title, description, value or identifier, so name-based filtering removed them despite their being visible. Only unnamed items are affected, so an application's real menus keep their own titles, and Control Centre's disabled extras stay out because they are filtered on geometry — they sit at `(0, 900)` with zero size
- Notification Centre contents are now captured, including the notification banners themselves. It is owned by `com.apple.notificationcenterui`, which was not scanned at all. A banner is an `AXGroup` carrying the subrole `AXNotificationCenterBanner`, so a new `INTERACTIVE_SUBROLES` set makes it interactive regardless of role, and `Subrole` moved into the phase-1 batch since interactivity now depends on it

### Changed
- Phase 2 now asks only for the attributes a role can actually carry. An attribute an element cannot have still costs work, because the application has to answer "unsupported" for each one — against Control Centre's status items five of eleven were never answered, and dropping them halved that fetch. Which attributes can be answered is a property of the role rather than of the application: a menu bar item structurally has no URL, a link has no text selection. Control Centre's scan went from 25.5 ms to 19.4 ms

## [0.3.15] - 2026-08-03

### Changed
- Desktop state capture is roughly 10x faster, and far more than that on complex pages. A browser window plus the system UI went from 695.7 ms to about 69 ms; measured against the previous release on a heavy DOM page it went from 18.0 s to 0.83 s, a 21.8x improvement. The captured node set is unchanged — verified entry by entry, including bounding boxes, on both workloads
- Three AXValue parsers asked `hasattr`/`getattr` before falling back to the correct unboxing call. On an `AXValueRef` a missing attribute raises and unwinds through the PyObjC bridge at roughly 178 µs, while `AXValueGetValue` costs roughly 0.8 µs, so the expensive probe was guarding the cheap answer — twice per element. `_parse_ax_position`, `_parse_ax_size` and `ParseCFRange` now unbox first. This alone accounted for two thirds of capture time
- `GetMultipleAttributeValues` no longer runs `isinstance` against a six-type tuple for every returned value. That check costs about 3.6 µs on a PyObjC bridge type and ran roughly 8000 times per capture, but its answer depends only on the concrete type, of which PyObjC returns very few. The classification is memoised per type; semantics are unchanged, including `bool` being an `int` subclass
- Traversal no longer descends into every collapsed container. The zero-area rule added in 0.3.14 stopped a degenerate box from pruning its subtree, which fixed real node loss but walked every collapsed wrapper on a page — expensive on DOM-heavy sites. It now descends only when the parent had a usable box, which is the overlay pattern that needed rescuing, and not when a collapsed wrapper sits inside another. Elements walked dropped from 738 to 409 with no node lost, recovering the capture-time regression 0.3.14 introduced
- The children array from an accessibility batch is materialised into a list once, rather than being re-crossed over the PyObjC bridge by each `len()`, `reversed()` and index

## [0.3.14] - 2026-08-03

### Added
- Text-entry elements now report their selection state. `AXTextField`, `AXTextArea`, `AXComboBox` and the `AXSearchField` subrole carry `selected_text` in metadata, plus `all_selected` when the selection covers the whole value — so a caller can tell whether typing will replace existing content or insert at a caret. Clicking a browser address bar selects its full value, and that is now visible in a snapshot. `AXSelectedText` and `AXSelectedTextRange` ride along in the existing phase-2 batch rather than adding a round-trip, and only real selections are reported since a zero-length caret is the resting state of every focused field

### Changed
- `AXPlaceholderValue` now participates in an element's label, after `value` and ahead of `identifier`. Search fields and unlabelled inputs frequently expose nothing else — YouTube's search box is an `AXComboBox` whose only descriptive attribute is a placeholder of "Search" — and without this they were nameless, which also made them invisible to name-based filtering

### Fixed
- Window control buttons no longer disappear from browser windows. Close, minimise, zoom and full-screen buttons expose no title, description, value or identifier, and were named only by `_desktop_correction`, which runs for native windows; browsers take the `_dom_correction` path instead and so lost their window controls entirely once name-based filtering was introduced. They are now named from `WINDOW_CONTROL_SUBROLES` during traversal, before the browser/native split, so both paths keep them
- Elements inside a zero-area container are no longer pruned. Clipping an element's box against the window could produce a `0x0` result for a collapsed wrapper, and the traversal then skipped that element *and its whole subtree* — Instagram positions a floating button inside a zero-height wrapper at the page bottom, so the button vanished despite having a valid rect well inside the window. A degenerate box now suppresses only the element itself, and traversal descends into its children, matching how a `None` rect was already handled. Note this costs noticeably more on DOM-heavy pages, where collapsed wrappers are common: a Chrome window measured roughly 320ms before and 600ms after, for 10 additional nodes; native applications are essentially unaffected
## [0.3.13] - 2026-08-03

### Added
- Release builds now verify that every declared version string agrees before publishing. `scripts/check_versions.py` compares `pyproject.toml`, `uv.lock`, `manifest.json`, `package.json` and `server.json` (twice) against each other and against the release tag, and `publish.yml` runs it ahead of the build so a mismatched tag fails before anything reaches PyPI — the drift that caused #32 would have been blocked at 0.3.9
- Character-range access to text controls, the macOS counterpart to the Windows Text Object Model. `TextRange` (in `macos_mcp.ax.text`) exposes `text`, `attributed_text`, `bounds`, `expand_to_line`, `expand_to_style`, `select` and `replace`; `Control` gains `SupportsTextRanges`, `FullTextRange`, `SelectionRange`, `LineRange`, `RangeAtPoint` and `TextAround`. `bounds` converts a character offset into screen coordinates, so text can be located without a screenshot, and `TextAround` reads the text surrounding the caret directly. Support varies by application and is probed rather than assumed, with every accessor degrading to `None`/`""`
- Per-word bounding boxes for text controls via `Control.WordBoundingBoxes()`, the macOS counterpart to Windows-MCP's `GetAllWordBoundingBoxes`. Returns one entry per whitespace-delimited token with one `Rect` per line it occupies, so every word in an editable element becomes an addressable screen target without a screenshot. Words that soft-wrap are clipped per line first, because `AXBoundsForRange` otherwise collapses a multi-line range into a single union rectangle spanning the full column width. Boxes are trimmed from the line box down to the glyph height using the font size read from `AXAttributedStringForRange`; pass `shrink_to_font=False` to keep the raw line rects. Returns `None` where the control does not advertise `AXBoundsForRange`, rather than fabricating a zero-area box whose centre is a real screen coordinate
- 56 accessibility constants that live applications report but the enums never declared: 49 attributes, 4 subroles and 3 actions. Notably `AXDisclosing`, without which the already-declared `AXDisclosedRows`/`AXDisclosedByRow`/`AXDisclosureLevel` cannot be interpreted — it is the one that says whether an outline row is currently expanded. Also `AXActivationPoint`, `AXFrontmost`, `AXEdited`, `AXRequired`, `AXInvalid`, `AXCustomActions`, `AXSelectedCells`, `AXOwns`, the ARIA/DOM attributes, the `AXSegment`/`AXToggleButton`/`AXMenuExtra` subroles and the `AXOpen`/`AXZoomWindow`/`AXScrollToVisible` actions. Each is grouped by provenance — documented in ApplicationServices, documented via NSAccessibility, or observed on live elements but absent from any public header — since the last group is best-effort and will be missing more often
- Snapshots now emit one addressable node per word inside `AXTextArea` elements, with `control_type="Word"`, so individual words can be clicked without a screenshot. Capped by `MAX_WORD_NODES_PER_ELEMENT` (default 200; set to 0 to disable), because every word costs an `AXBoundsForRange` round-trip — a 400-word text area measures roughly 250ms on its own, against roughly 220ms for an entire snapshot. A word that soft-wraps contributes one node per line, since the box is what gets clicked
- `AXIndex` is now fetched during traversal and exposed on the phase-1 attribute batch, and elements reporting one are treated as interactive. This brings table and outline rows into snapshots

### Changed
- Accessibility permission failures now name the process that needs the grant (`sys.executable`) instead of just the permission. The message also points at the native "would like to control this computer" consent dialog as the reliable fix, and warns against adding the interpreter by hand in the System Settings "+" picker, which is greyed out for uv-managed Python and breaks on the next uv update (#32)
- Nodes whose name is blank after stripping are no longer emitted into snapshots
- `_dom_correction` and `_desktop_correction` are now pure transforms: they take the node and return it, a replacement, or `None`, and the caller performs the single append. Previously each popped the node the caller had just appended, which assumed the node of interest was last in a list the function did not own

### Fixed
- Parameterized accessibility attributes now use their real names. All 13 values in `Attribute` carried a `Parameterized` suffix, which belongs to the constant name in Apple's headers (`kAXStringForRangeParameterizedAttribute`) but not to the string it expands to (`AXStringForRange`), so every parameterized call returned `kAXErrorParameterizedAttributeUnsupported` (-25213). `Control.GetTextFromMarkers` — the only caller — consequently always returned an empty string; against a live `AXWebArea` it now returns the page text instead of nothing
- Attributed-string keys now use their real names. 16 of the 20 values in `TextAttribute` carried a `Text` suffix which, as with the parameterized attributes, belongs to the constant name in Apple's headers (`kAXFontTextAttribute`) but not to the string it expands to (`AXFont`). Every lookup against them missed, so font, colour, underline, strikethrough, superscript, link and spell-check information was unreadable from `AXAttributedStringForRange`. The four font sub-keys (`AXFontFamily`, `AXFontName`, `AXFontSize`, `AXVisibleName`) index into the nested `AXFont` dictionary and were already correct. Adds `TextAlignment` (`AXATextAlignmentValue`), which was missing entirely
- Tabs are now identified correctly. `Role.Tab` was `"AXTab"`, a role macOS never reports — an individual tab is an `AXRadioButton` carrying the `AXTabButton` subrole — so `Control.TabControl()` could never match anything and the control factory mapped real tabs to `RadioButtonControl`. The finder now searches by subrole and the factory maps `AXRadioButton`/`AXTabButton` to `TabControl`; the subrole is only fetched for radio buttons, so traversal cost is unchanged for every other element. `Role.Tab` has been removed, since keeping an unusable constant only invites reuse
- `expanded` is no longer collapsed to a plain boolean before it reaches the caller. `GetLateTraversalBatch` previously applied `is True`, so an element with no disclosure state and one that is present but collapsed both arrived as `False`, and snapshots then reported neither. The batch now preserves `None` for absent, and snapshots include the state whenever the element has one. Note that some applications answer `AXExpanded` with `False` even for elements that do not advertise it, so a collapsed control and a non-expandable one can still be indistinguishable in those apps

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
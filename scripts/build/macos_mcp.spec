import os
# PyInstaller spec for MacOS-MCP.app.
#
# The point of freezing is not distribution size -- it is that the bundle stops
# being written to at runtime. Running the server through `uv` from inside the
# bundle creates a .venv in Contents/Resources on first launch, which counts as
# modifying the bundle and invalidates its code signature. A notarized build
# would be rejected by Gatekeeper, and TCC grants keyed to the cdhash would
# break on first use -- reintroducing the very churn issue #25 is about.
#
# Freezing also collapses the process tree. There is no `uv` and no ad-hoc
# system python left in the chain, so the process making accessibility calls is
# the signed bundle itself rather than a grandchild of it.
#
# The collect_all entries below are not decorative. Each was added after the
# frozen binary crashed at startup for a data file PyInstaller does not find by
# static analysis:
#
#   rfc3987_syntax   syntax_rfc3987.lark   grammar loaded at import
#   lupa             lupa.lua51            runtime-selected extension module
#   fakeredis        commands.json         read relative to __file__
#
# Keep this file rather than a long command line: these break silently when a
# dependency changes, and the failure is a traceback at startup, not a build
# error.

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []

for package in (
    "macos_mcp",
    "fastmcp",
    "mcp",
    "rfc3987_syntax",
    "lark",
    "jsonschema",
    "lupa",
    "fakeredis",
):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# PyObjC dispatches through runtime lookups that static analysis cannot see.
hiddenimports += collect_submodules("objc")
hiddenimports += ["PIL"]

analysis = Analysis(
    [os.path.join(SPECPATH, "entry.py")],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="MacOS-MCP",
    debug=False,
    strip=False,
    upx=False,          # UPX rewrites the binary, which breaks code signing
    console=False,
)

collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="MacOS-MCP",
)

app = BUNDLE(
    collect,
    name="MacOS-MCP.app",
    icon=None,          # set by the build script, which generates the .icns
    bundle_identifier="com.cursortouch.macos-mcp",
    info_plist={
        # TCC keys grants on this, so it must not change between releases or
        # every user is prompted again.
        "CFBundleIdentifier": "com.cursortouch.macos-mcp",
        "CFBundleName": "MacOS-MCP",
        "CFBundleDisplayName": "macOS MCP",
        "LSMinimumSystemVersion": "13.0",
        # No interface of its own: the server is spawned by an MCP host and
        # speaks JSON-RPC over stdio. Only consulted when the bundle is opened
        # through LaunchServices, not when a host execs the binary directly.
        "LSBackgroundOnly": True,
        "NSAccessibilityUsageDescription":
            "macOS MCP reads the accessibility tree to describe what is on "
            "screen, and clicks and types on your behalf.",
        "NSAppleEventsUsageDescription":
            "macOS MCP sends Apple Events to control applications you ask it "
            "to act on.",
    },
)

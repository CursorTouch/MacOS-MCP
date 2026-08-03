#!/usr/bin/env bash
#
# Build MacOS-MCP.app -- a bundle whose only job is to give macOS one stable,
# named identity to attribute privacy grants to.
#
# The problem this solves: Claude Desktop launches the server as
# `uv --directory <ext> run macos-mcp serve`. Both `uv` and the interpreter it
# manages are ad-hoc, linker-signed and carry no Team ID:
#
#     uv                  flags=0x20002(adhoc,linker-signed)  TeamIdentifier=not set
#     uv-managed python   flags=0x20002(adhoc,linker-signed)  Identifier=-
#
# TCC cannot roll those up under one identity, so Accessibility and Automation
# grants appear as separate icon-less rows named `uv`, `python3`, `node`, and
# ad-hoc signatures are re-generated on upgrade, which invalidates the grants
# and leaves stale duplicates behind. See issue #25.
#
# Usage:
#     scripts/build_app.sh                     # ad-hoc signed, for local testing
#     CODESIGN_IDENTITY="Developer ID Application: Example (TEAMID)" \
#         scripts/build_app.sh                 # release build
#
# Notarization is a separate step; see scripts/notarize_app.sh.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="MacOS-MCP"
BUNDLE_ID="com.cursortouch.macos-mcp"
DIST="${ROOT}/dist"
APP="${DIST}/${APP_NAME}.app"
IDENTITY="${CODESIGN_IDENTITY:--}"   # "-" is ad-hoc

VERSION="$(grep -m1 '^version' "${ROOT}/pyproject.toml" | sed 's/.*= *//' | tr -d '"')"

echo "building ${APP_NAME}.app ${VERSION}"
rm -rf "${APP}"
mkdir -p "${APP}/Contents/MacOS" "${APP}/Contents/Resources"

# Background by default: the server is spawned by an MCP host and speaks over
# stdio, so it has no interface of its own. These keys are only consulted when
# the bundle is launched through LaunchServices (`open`), not when the host
# execs the binary directly.
#
#   (default)          LSBackgroundOnly -- no Dock icon, cannot show UI
#   APP_UI=agent       LSUIElement      -- no Dock icon, may show dialogs
#   APP_UI=foreground  neither          -- ordinary app, appears in the Dock
case "${APP_UI:-background}" in
    foreground) UI_KEY="<!-- foreground app: appears in the Dock -->" ;;
    agent)      UI_KEY="<key>LSUIElement</key>            <true/>" ;;
    *)          UI_KEY="<key>LSBackgroundOnly</key>       <true/>" ;;
esac

# --- Info.plist -------------------------------------------------------------
# CFBundleIdentifier is what TCC keys grants on, so it must not change between
# releases or every user is re-prompted. The usage descriptions are what the
# permission dialogs actually show.
cat > "${APP}/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>          <string>${BUNDLE_ID}</string>
    <key>CFBundleName</key>                <string>${APP_NAME}</string>
    <key>CFBundleDisplayName</key>         <string>macOS MCP</string>
    <key>CFBundleExecutable</key>          <string>macos-mcp</string>
    <key>CFBundleIconFile</key>            <string>icon</string>
    <key>CFBundlePackageType</key>         <string>APPL</string>
    <key>CFBundleShortVersionString</key>  <string>${VERSION}</string>
    <key>CFBundleVersion</key>             <string>${VERSION}</string>
    <key>LSMinimumSystemVersion</key>      <string>13.0</string>
    ${UI_KEY}
    <key>NSAccessibilityUsageDescription</key>
    <string>macOS MCP reads the accessibility tree to describe what is on screen, and clicks and types on your behalf.</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>macOS MCP sends Apple Events to control applications you ask it to act on.</string>
</dict>
</plist>
PLIST

# --- launcher ---------------------------------------------------------------
# Must be a compiled binary. A shell script runs as /bin/bash, and one that
# exec's is replaced by its target, so in both cases the process macOS sees is
# not this bundle and the signed identity is lost. Verified by testing.
cc -O2 -o "${APP}/Contents/MacOS/macos-mcp" "${ROOT}/scripts/launcher.c"
chmod +x "${APP}/Contents/MacOS/macos-mcp"

# --- icon -------------------------------------------------------------------
if [[ -f "${ROOT}/assets/logo.png" ]]; then
    ICONSET="$(mktemp -d)/icon.iconset"
    mkdir -p "${ICONSET}"
    for size in 16 32 128 256 512; do
        sips -z $size $size "${ROOT}/assets/logo.png" \
            --out "${ICONSET}/icon_${size}x${size}.png" >/dev/null 2>&1 || true
        sips -z $((size*2)) $((size*2)) "${ROOT}/assets/logo.png" \
            --out "${ICONSET}/icon_${size}x${size}@2x.png" >/dev/null 2>&1 || true
    done
    iconutil -c icns "${ICONSET}" -o "${APP}/Contents/Resources/icon.icns" 2>/dev/null \
        || echo "  warning: iconutil failed, bundle will have no icon"
fi

# --- payload ----------------------------------------------------------------
mkdir -p "${APP}/Contents/Resources/payload"
cp -R "${ROOT}/src" "${ROOT}/pyproject.toml" "${ROOT}/uv.lock" \
      "${APP}/Contents/Resources/payload/"
[[ -f "${ROOT}/README.md" ]] && cp "${ROOT}/README.md" "${APP}/Contents/Resources/payload/"

# --- sign -------------------------------------------------------------------
# Hardened runtime is required for notarization. It is only meaningful with a
# real identity, so it is skipped for ad-hoc test builds.
if [[ "${IDENTITY}" == "-" ]]; then
    echo "signing ad-hoc (local testing only -- will NOT fix TCC attribution)"
    codesign --force --sign - "${APP}"
else
    echo "signing as ${IDENTITY}"
    codesign --force --deep --options runtime --timestamp \
        --sign "${IDENTITY}" "${APP}"
fi

codesign --verify --strict --verbose=2 "${APP}" 2>&1 | sed 's/^/  /'
echo
codesign -dv --verbose=2 "${APP}" 2>&1 \
    | grep -E "Identifier|TeamIdentifier|Signature|flags" | sed 's/^/  /'
echo
echo "built ${APP}"

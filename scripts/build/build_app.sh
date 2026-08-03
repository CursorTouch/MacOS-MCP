#!/usr/bin/env bash
#
# Build MacOS-MCP.app -- a frozen, self-contained bundle that gives macOS one
# stable, named identity to attribute privacy grants to.
#
# The problem this solves (issue #25): Claude Desktop launches the server as
# `uv --directory <ext> run macos-mcp serve`. Neither uv nor the interpreter it
# manages carries a Developer ID:
#
#     uv                  flags=0x20002(adhoc,linker-signed)  TeamIdentifier=not set
#     uv-managed python   flags=0x20002(adhoc,linker-signed)  Identifier=-
#
# TCC cannot roll those up under one identity, so Accessibility and Automation
# grants show up as separate icon-less rows named `uv`, `python3`, `node`. Being
# ad-hoc, they are re-signed on every upgrade, which invalidates the grants and
# leaves stale duplicates behind.
#
# Two approaches were tried. Wrapping `uv` in a bundle does not work: the first
# launch creates a .venv inside Contents/Resources, which modifies the bundle
# and invalidates its signature -- verified, 2.1MB becomes 321MB and codesign
# reports hundreds of added files. Freezing does work: nothing is written at
# runtime, so the signature survives, and there is no uv or system python left
# in the process tree.
#
# Usage:
#     scripts/build/build_app.sh                     # ad-hoc signed, local testing
#     CODESIGN_IDENTITY="Developer ID Application: Example (TEAMID)" \
#         scripts/build/build_app.sh                 # release build
#
# An ad-hoc build is structurally correct but does NOT fix TCC attribution:
# codesign re-signs with a new cdhash each time, so grants break exactly as they
# do today. That needs a real Developer ID, which needs paid Apple enrolment.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_NAME="MacOS-MCP"
DIST="${ROOT}/dist"
BUILD="${ROOT}/build"
APP="${DIST}/${APP_NAME}.app"
IDENTITY="${CODESIGN_IDENTITY:--}"   # "-" is ad-hoc

VERSION="$(grep -m1 '^version' "${ROOT}/pyproject.toml" | sed 's/.*= *//' | tr -d '"')"
echo "building ${APP_NAME}.app ${VERSION}"

command -v uv >/dev/null || { echo "uv is required"; exit 1; }
uv run python -c "import PyInstaller" 2>/dev/null || {
    echo "installing pyinstaller"; uv pip install pyinstaller >/dev/null; }

# --- icon -------------------------------------------------------------------
ICON_ARG=""
if [[ -f "${ROOT}/assets/logo.png" ]]; then
    ICONSET="$(mktemp -d)/icon.iconset"
    mkdir -p "${ICONSET}"
    for size in 16 32 128 256 512; do
        sips -z $size $size "${ROOT}/assets/logo.png" \
            --out "${ICONSET}/icon_${size}x${size}.png" >/dev/null 2>&1 || true
        sips -z $((size*2)) $((size*2)) "${ROOT}/assets/logo.png" \
            --out "${ICONSET}/icon_${size}x${size}@2x.png" >/dev/null 2>&1 || true
    done
    if iconutil -c icns "${ICONSET}" -o "${BUILD}/icon.icns" 2>/dev/null; then
        ICON_ARG="--icon=${BUILD}/icon.icns"
    fi
fi

# --- freeze -----------------------------------------------------------------
rm -rf "${APP}"
mkdir -p "${BUILD}"
uv run pyinstaller --noconfirm --clean \
    --distpath "${DIST}" --workpath "${BUILD}" \
    ${ICON_ARG} \
    "${ROOT}/scripts/build/macos_mcp.spec"

# PyInstaller leaves the unbundled COLLECT directory next to the .app; it is
# the same payload again and only confuses whoever opens dist/.
rm -rf "${DIST:?}/${APP_NAME}"

# --- sign -------------------------------------------------------------------
# Hardened runtime is required for notarization, and is only meaningful with a
# real identity, so it is skipped for ad-hoc test builds.
if [[ "${IDENTITY}" == "-" ]]; then
    echo "signing ad-hoc (local testing only -- does NOT fix TCC attribution)"
    codesign --force --deep --sign - "${APP}"
else
    echo "signing as ${IDENTITY}"
    codesign --force --deep --options runtime --timestamp \
        --sign "${IDENTITY}" "${APP}"
fi

echo
codesign --verify --strict --verbose=2 "${APP}" 2>&1 | sed 's/^/  /'
codesign -dv --verbose=2 "${APP}" 2>&1 \
    | grep -E "Identifier|TeamIdentifier|Signature|flags" | sed 's/^/  /'
echo
echo "built ${APP}  ($(du -sh "${APP}" | cut -f1))"

if [[ "${IDENTITY}" != "-" ]]; then
    cat <<'NEXT'

next: notarize and staple, e.g.

    ditto -c -k --keepParent dist/MacOS-MCP.app /tmp/MacOS-MCP.zip
    xcrun notarytool submit /tmp/MacOS-MCP.zip \
        --apple-id "$APPLE_ID" --team-id "$TEAM_ID" \
        --password "$APP_SPECIFIC_PASSWORD" --wait
    xcrun stapler staple dist/MacOS-MCP.app
NEXT
fi

#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# stdio-to-http-reconfig.sh
#
# Reconfigure Claude Desktop to connect to a running macOS-MCP HTTP
# server via the native Swift stdio-to-HTTP bridge, replacing any
# existing mcp-remote (Node.js) or prior bridge entry.
#
# Works with multiple Claude Desktop instances (e.g. Parall clones).
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BRIDGE_DIR="$(cd "$SCRIPT_DIR/../bridge" && pwd)"
BRIDGE_BIN="$BRIDGE_DIR/mcp-stdio-bridge"

DEFAULT_PORT="8765"
DEFAULT_HOST="127.0.0.1"
DEFAULT_URL="http://${DEFAULT_HOST}:${DEFAULT_PORT}/mcp"
MCP_NAME="MacOS-MCP"

usage() {
  cat << EOF
Usage: $(basename "$0") [OPTIONS]

Reconfigure Claude Desktop's claude_desktop_config.json to connect to a
macOS-MCP HTTP server using the native Swift stdio-to-HTTP bridge.

Replaces npx mcp-remote (Node.js, ~100 MB RSS per instance) with a
90 KB native binary (~3-5 MB RSS per instance).

Options:
  --url URL         Server URL (default: $DEFAULT_URL)
  --name NAME       MCP server name in config (default: $MCP_NAME)
  --config PATH     Reconfigure a single config file instead of auto-detecting
  --dry-run         Show what would change without writing
  --install-server  Also install the launchd background service
  --transport TYPE  Transport for --install-server (default: streamable-http)
  --host HOST       Host for --install-server (default: 127.0.0.1)
  --port PORT       Port for --install-server (default: 8765)
  --build           Build the Swift bridge before reconfiguring
  -h, --help        Show this help

Examples:
  # Build bridge and reconfigure all detected Claude Desktop instances
  $(basename "$0") --build

  # Preview changes without writing
  $(basename "$0") --dry-run

  # Reconfigure a specific config file
  $(basename "$0") --config ~/Library/Application\ Support/Claude/claude_desktop_config.json
EOF
  exit 0
}

# ── Parse arguments ───────────────────────────────────────────────
URL=""
DRY_RUN=false
INSTALL_SERVER=false
BUILD=false
TRANSPORT="streamable-http"
HOST="$DEFAULT_HOST"
PORT="$DEFAULT_PORT"
PORT_EXPLICIT=false
URL_EXPLICIT=false
SINGLE_CONFIG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)         URL="$2"; URL_EXPLICIT=true; shift 2 ;;
    --name)        MCP_NAME="$2"; shift 2 ;;
    --config)      SINGLE_CONFIG="$2"; shift 2 ;;
    --dry-run)     DRY_RUN=true; shift ;;
    --install-server) INSTALL_SERVER=true; shift ;;
    --transport)   TRANSPORT="$2"; shift 2 ;;
    --host)        HOST="$2"; shift 2 ;;
    --port)        PORT="$2"; PORT_EXPLICIT=true; shift 2 ;;
    --build)       BUILD=true; shift ;;
    -h|--help)     usage ;;
    *)             echo "Unknown option: $1"; usage ;;
  esac
done

# ── Build the bridge if requested ─────────────────────────────────
if [ "$BUILD" = true ]; then
  echo "=== Building Swift bridge ==="
  if ! command -v swiftc &>/dev/null; then
    echo "ERROR: swiftc not found. Install Xcode Command Line Tools."
    exit 1
  fi
  swiftc -O -o "$BRIDGE_BIN" "$BRIDGE_DIR/MCPStdioBridge.swift"
  codesign -s - "$BRIDGE_BIN"
  echo "  Built: $BRIDGE_BIN ($(wc -c < "$BRIDGE_BIN" | tr -d ' ') bytes, ad-hoc signed)"
  echo ""
fi

# ── Verify bridge binary exists ───────────────────────────────────
if [ ! -x "$BRIDGE_BIN" ]; then
  echo "ERROR: Bridge binary not found at $BRIDGE_BIN"
  echo "Run with --build to compile it, or build manually:"
  echo "  swiftc -O -o $BRIDGE_BIN $BRIDGE_DIR/MCPStdioBridge.swift"
  exit 1
fi

# ── Port probing ─────────────────────────────────────────────────
find_free_port() {
  local start="${1:-8765}"
  local host="${2:-127.0.0.1}"
  local port="$start"
  local limit=$(( start + 100 ))
  while [ "$port" -lt "$limit" ]; do
    if ! lsof -i TCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "$port"
      return 0
    fi
    port=$(( port + 1 ))
  done
  echo "ERROR: No free port found in range $start-$(( limit - 1 )) on $host" >&2
  return 1
}

# ── Discover config files ────────────────────────────────────────
discover_configs() {
  local configs=()
  local app_support="$HOME/Library/Application Support"

  local main="$app_support/Claude/claude_desktop_config.json"
  if [ -f "$main" ]; then
    configs+=("$main")
  fi

  if [ -d "$app_support/Parall" ]; then
    for d in "$app_support/Parall"/*/; do
      local cfg="$d/claude_desktop_config.json"
      if [ -f "$cfg" ]; then
        configs+=("$cfg")
      fi
    done
  fi

  printf '%s\n' "${configs[@]}"
}

# ── Build the bridge entry ───────────────────────────────────────
build_entry() {
  local url="$1"
  python3 -c "
import json
entry = {
    'command': '$BRIDGE_BIN',
    'args': ['--url', '$url']
}
print(json.dumps(entry))
"
}

# ── Update a config file ─────────────────────────────────────────
update_config() {
  local config_file="$1"
  local entry_json="$2"
  local mcp_name="$3"
  local dry_run="$4"
  local label
  label=$(echo "$config_file" | sed "s|$HOME/Library/Application Support/||")

  python3 << PYEOF
import json, sys

config_file = """$config_file"""
mcp_name = "$mcp_name"
label = "$label"
new_entry = json.loads('$entry_json')
dry_run = $( [ "$dry_run" = "true" ] && echo "True" || echo "False" )

with open(config_file) as f:
    cfg = json.load(f)

old_entry = cfg.get("mcpServers", {}).get(mcp_name)
cfg.setdefault("mcpServers", {})
cfg["mcpServers"][mcp_name] = new_entry

if dry_run:
    if old_entry == new_entry:
        print(f"  {mcp_name} in {label}: already up to date")
    elif old_entry:
        print(f"  {mcp_name} in {label}: would replace existing entry")
        print(f"    old: {json.dumps(old_entry)}")
        print(f"    new: {json.dumps(new_entry)}")
    else:
        print(f"  {mcp_name} in {label}: would add new entry")
        print(f"    new: {json.dumps(new_entry)}")
else:
    with open(config_file, "w") as f:
        json.dump(cfg, f, indent=2)
    if old_entry and old_entry != new_entry:
        print(f"  Updated {mcp_name} in {label}")
    elif old_entry:
        print(f"  {mcp_name} in {label}: already up to date")
    else:
        print(f"  Added {mcp_name} to {label}")
PYEOF
}

# ── Main ─────────────────────────────────────────────────────────
echo "macOS-MCP: reconfigure to native Swift bridge"
echo ""

if [ "$INSTALL_SERVER" = true ]; then
  echo "=== Installing HTTP server ==="
  if [ "$PORT_EXPLICIT" = false ]; then
    PORT=$(find_free_port "$PORT" "$HOST")
    echo "  Selected port: $PORT"
  fi
  if command -v macos-mcp &>/dev/null; then
    macos-mcp install --transport "$TRANSPORT" --host "$HOST" --port "$PORT" --force
  elif command -v uvx &>/dev/null; then
    uvx macos-mcp install --transport "$TRANSPORT" --host "$HOST" --port "$PORT" --force
  else
    echo "ERROR: Cannot find macos-mcp or uvx in PATH."
    exit 1
  fi
  echo ""
  sleep 2
fi

if [ "$URL_EXPLICIT" = false ]; then
  URL="http://${HOST}:${PORT}/mcp"
fi

ENTRY_JSON=$(build_entry "$URL")

echo "=== Updating Claude Desktop configurations ==="
echo "  Bridge: $BRIDGE_BIN"
echo "  Server: $URL"
echo ""

if [ -n "$SINGLE_CONFIG" ]; then
  if [ ! -f "$SINGLE_CONFIG" ]; then
    echo "ERROR: Config file not found: $SINGLE_CONFIG"
    exit 1
  fi
  update_config "$SINGLE_CONFIG" "$ENTRY_JSON" "$MCP_NAME" "$DRY_RUN"
else
  CONFIGS=$(discover_configs)
  if [ -z "$CONFIGS" ]; then
    echo "  No Claude Desktop config files found."
    exit 1
  fi

  while IFS= read -r cfg; do
    update_config "$cfg" "$ENTRY_JSON" "$MCP_NAME" "$DRY_RUN"
  done <<< "$CONFIGS"
fi

echo ""
if [ "$DRY_RUN" = true ]; then
  echo "Dry run complete. No files were modified."
  echo "Run without --dry-run to apply changes."
else
  echo "Done. Restart Claude Desktop for changes to take effect."
fi

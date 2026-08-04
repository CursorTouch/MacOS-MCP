#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# stdio-to-http-reconfig.sh
#
# Reconfigure Claude Desktop to connect to a running macOS-MCP HTTP
# server via mcp-remote, replacing any existing stdio-based entry.
#
# Works with multiple Claude Desktop instances (e.g. Parall clones).
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

DEFAULT_URL="http://127.0.0.1:8000/mcp"
MCP_NAME="macos-mcp"

usage() {
  cat << EOF
Usage: $(basename "$0") [OPTIONS]

Reconfigure Claude Desktop's claude_desktop_config.json to connect to a
macOS-MCP HTTP server using mcp-remote as a stdio-to-HTTP bridge.

Options:
  --url URL         Server URL (default: $DEFAULT_URL)
  --auth-key KEY    Add an Authorization: Bearer header
  --name NAME       MCP server name in config (default: $MCP_NAME)
  --config PATH     Reconfigure a single config file instead of auto-detecting
  --dry-run         Show what would change without writing
  --install-server  Also install the launchd background service
  --transport TYPE  Transport for --install-server (default: streamable-http)
  --host HOST       Host for --install-server (default: 127.0.0.1)
  --port PORT       Port for --install-server (default: 8000)
  -h, --help        Show this help

Examples:
  # Reconfigure all detected Claude Desktop instances
  $(basename "$0")

  # Install the HTTP server and reconfigure in one step
  $(basename "$0") --install-server

  # Reconfigure with authentication
  $(basename "$0") --auth-key "my-secret-token"

  # Preview changes without writing
  $(basename "$0") --dry-run

  # Reconfigure a specific config file
  $(basename "$0") --config ~/Library/Application\ Support/Claude/claude_desktop_config.json
EOF
  exit 0
}

# ── Parse arguments ───────────────────────────────────────────────
URL="$DEFAULT_URL"
AUTH_KEY=""
DRY_RUN=false
INSTALL_SERVER=false
TRANSPORT="streamable-http"
HOST="127.0.0.1"
PORT="8000"
SINGLE_CONFIG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)         URL="$2"; shift 2 ;;
    --auth-key)    AUTH_KEY="$2"; shift 2 ;;
    --name)        MCP_NAME="$2"; shift 2 ;;
    --config)      SINGLE_CONFIG="$2"; shift 2 ;;
    --dry-run)     DRY_RUN=true; shift ;;
    --install-server) INSTALL_SERVER=true; shift ;;
    --transport)   TRANSPORT="$2"; shift 2 ;;
    --host)        HOST="$2"; shift 2 ;;
    --port)        PORT="$2"; shift 2 ;;
    -h|--help)     usage ;;
    *)             echo "Unknown option: $1"; usage ;;
  esac
done

# ── Discover config files ────────────────────────────────────────
discover_configs() {
  local configs=()
  local app_support="$HOME/Library/Application Support"

  # Main Claude Desktop
  local main="$app_support/Claude/claude_desktop_config.json"
  if [ -f "$main" ]; then
    configs+=("$main")
  fi

  # Parall clones (any subdirectory under Application Support/Parall/)
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

# ── Build the mcp-remote entry ───────────────────────────────────
build_entry() {
  local url="$1"
  local auth="$2"

  if [ -n "$auth" ]; then
    python3 -c "
import json
entry = {
    'command': 'npx',
    'args': ['-y', 'mcp-remote', '$url', '--transport', 'http-only',
             '--header', 'Authorization: Bearer $auth']
}
print(json.dumps(entry))
"
  else
    python3 -c "
import json
entry = {
    'command': 'npx',
    'args': ['-y', 'mcp-remote', '$url', '--transport', 'http-only']
}
print(json.dumps(entry))
"
  fi
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
new_entry = json.loads('$entry_json')
dry_run = $( [ "$dry_run" = "true" ] && echo "True" || echo "False" )

with open(config_file) as f:
    cfg = json.load(f)

old_entry = cfg.get("mcpServers", {}).get(mcp_name)
cfg.setdefault("mcpServers", {})
cfg["mcpServers"][mcp_name] = new_entry

if dry_run:
    if old_entry == new_entry:
        print(f"  {mcp_name} in $label: already up to date")
    elif old_entry:
        print(f"  {mcp_name} in $label: would replace existing entry")
        print(f"    old: {json.dumps(old_entry)}")
        print(f"    new: {json.dumps(new_entry)}")
    else:
        print(f"  {mcp_name} in $label: would add new entry")
        print(f"    new: {json.dumps(new_entry)}")
else:
    with open(config_file, "w") as f:
        json.dump(cfg, f, indent=2)
    if old_entry and old_entry != new_entry:
        print(f"  Updated {mcp_name} in $label")
    elif old_entry:
        print(f"  {mcp_name} in $label: already up to date")
    else:
        print(f"  Added {mcp_name} to $label")
PYEOF
}

# ── Main ─────────────────────────────────────────────────────────
echo "macOS-MCP: stdio → HTTP reconfiguration"
echo ""

# Optionally install the server first
if [ "$INSTALL_SERVER" = true ]; then
  echo "=== Installing HTTP server ==="
  if command -v macos-mcp &>/dev/null; then
    macos-mcp install --transport "$TRANSPORT" --host "$HOST" --port "$PORT" --force
  elif command -v uvx &>/dev/null; then
    uvx macos-mcp install --transport "$TRANSPORT" --host "$HOST" --port "$PORT" --force
  else
    echo "ERROR: Cannot find macos-mcp or uvx in PATH."
    echo "Install macos-mcp first: pip install macos-mcp  or  brew install uv"
    exit 1
  fi
  echo ""
  sleep 2
fi

# Build the entry JSON
ENTRY_JSON=$(build_entry "$URL" "$AUTH_KEY")

# Find and update configs
echo "=== Updating Claude Desktop configurations ==="

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
    echo "  Expected: ~/Library/Application Support/Claude/claude_desktop_config.json"
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

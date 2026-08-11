#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# stdio-to-http-reconfig-python.sh
#
# Reconfigure Claude Desktop to connect to a running macOS-MCP HTTP
# server via the Python stdio-to-HTTP bridge. Use when the Swift binary
# is unavailable (no Xcode CLI tools) or for quick testing.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BRIDGE_DIR="$(cd "$SCRIPT_DIR/../bridge" && pwd)"
BRIDGE_PY="$BRIDGE_DIR/mcp-stdio-bridge.py"

DEFAULT_URL="http://127.0.0.1:8765/mcp"
MCP_NAME="MacOS-MCP"

usage() {
  cat << EOF
Usage: $(basename "$0") [OPTIONS]

Reconfigure Claude Desktop to use the Python stdio-to-HTTP bridge.
Requires Python 3.11+ (already needed by macOS-MCP).

Options:
  --url URL         Server URL (default: $DEFAULT_URL)
  --name NAME       MCP server name in config (default: $MCP_NAME)
  --config PATH     Reconfigure a single config file
  --dry-run         Show changes without writing
  -h, --help        Show this help
EOF
  exit 0
}

URL="$DEFAULT_URL"
DRY_RUN=false
SINGLE_CONFIG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)     URL="$2"; shift 2 ;;
    --name)    MCP_NAME="$2"; shift 2 ;;
    --config)  SINGLE_CONFIG="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help) usage ;;
    *)         echo "Unknown option: $1"; usage ;;
  esac
done

if [ ! -f "$BRIDGE_PY" ]; then
  echo "ERROR: Python bridge not found at $BRIDGE_PY"
  exit 1
fi

PYTHON3=$(command -v python3 || true)
if [ -z "$PYTHON3" ]; then
  echo "ERROR: python3 not found in PATH"
  exit 1
fi

discover_configs() {
  local configs=()
  local app_support="$HOME/Library/Application Support"
  local main="$app_support/Claude/claude_desktop_config.json"
  if [ -f "$main" ]; then configs+=("$main"); fi
  if [ -d "$app_support/Parall" ]; then
    for d in "$app_support/Parall"/*/; do
      local cfg="$d/claude_desktop_config.json"
      if [ -f "$cfg" ]; then configs+=("$cfg"); fi
    done
  fi
  printf '%s\n' "${configs[@]}"
}

update_config() {
  local config_file="$1"
  local dry_run="$2"
  local label
  label=$(echo "$config_file" | sed "s|$HOME/Library/Application Support/||")

  python3 << PYEOF
import json

config_file = """$config_file"""
mcp_name = "$MCP_NAME"
new_entry = {
    "command": "$PYTHON3",
    "args": ["$BRIDGE_PY", "--url", "$URL"]
}
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
        print(f"  {mcp_name} in $label: would replace")
    else:
        print(f"  {mcp_name} in $label: would add")
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

echo "macOS-MCP: reconfigure to Python bridge"
echo "  Bridge: $BRIDGE_PY"
echo "  Server: $URL"
echo ""

if [ -n "$SINGLE_CONFIG" ]; then
  update_config "$SINGLE_CONFIG" "$DRY_RUN"
else
  CONFIGS=$(discover_configs)
  if [ -z "$CONFIGS" ]; then echo "  No config files found."; exit 1; fi
  while IFS= read -r cfg; do
    update_config "$cfg" "$DRY_RUN"
  done <<< "$CONFIGS"
fi

echo ""
if [ "$DRY_RUN" = true ]; then
  echo "Dry run complete."
else
  echo "Done. Restart Claude Desktop for changes to take effect."
fi

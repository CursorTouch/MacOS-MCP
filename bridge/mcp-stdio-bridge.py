#!/usr/bin/env python3
"""
mcp-stdio-bridge — a zero-dependency stdio-to-HTTP bridge for MCP servers.

Replaces npx mcp-remote for local HTTP MCP servers. No Node.js required.
Reads newline-delimited JSON-RPC frames from stdin, POSTs each to the
target HTTP endpoint, writes the response to stdout. Logging goes to
stderr only; stdout carries JSON-RPC frames exclusively.

Concurrency: each frame forwards on its own thread. A slow tool call
(Snapshot, long Shell command) does not block frames behind it. Responses
may interleave out of order; this is legal JSON-RPC (clients correlate
by id).

Failure policy: a failed REQUEST gets a synthesized JSON-RPC error that
echoes the request's id. A failed NOTIFICATION gets nothing (servers must
not reply to notifications). The bridge only exits on stdin EOF or a
stdin read error — never because one call failed.

Handles MCP Streamable HTTP session management (MCP-Session-Id) and SSE
response parsing (text/event-stream with data: lines).

Design baseline: mootx01-ce apps/mootx01/rust/src/commands/proxy.rs

Usage:
    mcp-stdio-bridge.py [--url URL] [--timeout SECONDS] [--max-concurrent N]

Claude Desktop config:
    {
      "mcpServers": {
        "macos-mcp": {
          "command": "python3",
          "args": ["/path/to/bridge/mcp-stdio-bridge.py",
                   "--url", "http://127.0.0.1:8765/mcp"]
        }
      }
    }
"""

import json
import sys
import threading
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

# -- Configuration -----------------------------------------------------------

DEFAULT_URL = "http://127.0.0.1:8765/mcp"
DEFAULT_TIMEOUT = 3600
DEFAULT_MAX_CONCURRENT = 16
MAX_LINE_BYTES = 4 * 1024 * 1024

def parse_args():
    url = DEFAULT_URL
    timeout = DEFAULT_TIMEOUT
    max_concurrent = DEFAULT_MAX_CONCURRENT
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--url" and i + 1 < len(args):
            url = args[i + 1]; i += 2
        elif args[i] == "--timeout" and i + 1 < len(args):
            timeout = int(args[i + 1]); i += 2
        elif args[i] == "--max-concurrent" and i + 1 < len(args):
            max_concurrent = int(args[i + 1]); i += 2
        elif args[i] in ("-h", "--help"):
            sys.stderr.write(__doc__); sys.exit(0)
        else:
            sys.stderr.write(f"mcp-stdio-bridge: unknown option: {args[i]}\n"); sys.exit(1)
    return url, timeout, max_concurrent

# -- Session state (thread-safe) ---------------------------------------------

_session_id = None
_session_lock = threading.Lock()

def get_session_id():
    with _session_lock:
        return _session_id

def set_session_id(sid):
    global _session_id
    with _session_lock:
        _session_id = sid

# -- Stdout serialization ----------------------------------------------------

_stdout_lock = threading.Lock()

def write_frame(data: bytes) -> None:
    with _stdout_lock:
        try:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        except BrokenPipeError:
            pass

# -- SSE parsing -------------------------------------------------------------

def extract_sse_data(body: bytes) -> bytes:
    """Extract JSON-RPC frames from an SSE text/event-stream response.
    Each 'data: {...}' line is a frame. Multiple frames are joined with newlines."""
    frames = []
    for raw_line in body.split(b"\n"):
        line = raw_line.strip()
        if line.startswith(b"data: "):
            payload = line[6:]  # strip "data: " prefix
            if payload:
                frames.append(payload)
    return b"\n".join(frames) if frames else body

# -- Frame forwarding --------------------------------------------------------

def request_id(line: str):
    try:
        obj = json.loads(line)
    except (json.JSONDecodeError, TypeError):
        return None
    raw_id = obj.get("id")
    if raw_id is None:
        return None
    if isinstance(raw_id, (str, int, float)):
        return json.dumps(raw_id)
    return None

def forward_frame(url: str, timeout: int, line: str) -> None:
    body = line.encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    sid = get_session_id()
    if sid:
        req.add_header("Mcp-Session-Id", sid)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            # Capture session id from response headers
            new_sid = resp.headers.get("Mcp-Session-Id")
            if new_sid:
                set_session_id(new_sid)
            resp_body = resp.read()
        if status == 202 or not resp_body:
            return
        content_type = resp.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            resp_body = extract_sse_data(resp_body)
        if not resp_body:
            return
        # May contain multiple frames (one per SSE data: line)
        for frame in resp_body.split(b"\n"):
            frame = frame.strip()
            if frame:
                write_frame(frame)
    except Exception as exc:
        sys.stderr.write(f"mcp-stdio-bridge: request failed: {exc}\n")
        rid = request_id(line)
        if rid is not None:
            msg = str(exc).replace("\\", "\\\\").replace('"', "'")
            err_frame = (
                f'{{"jsonrpc":"2.0","id":{rid},'
                f'"error":{{"code":-32603,"message":"bridge: {msg}"}}}}'
            )
            write_frame(err_frame.encode("utf-8"))

# -- Startup health check ---------------------------------------------------

def wait_for_server(url: str, max_wait: int = 30) -> bool:
    """Poll via a POST with a minimal JSON-RPC ping. HEAD/GET hang on SSE endpoints."""
    deadline = time.monotonic() + max_wait
    attempt = 0
    ping = b'{"jsonrpc":"2.0","id":"ping","method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"healthcheck","version":"1"}}}'
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(
                url, data=ping, method="POST",
                headers={"Content-Type": "application/json",
                         "Accept": "application/json, text/event-stream"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                # Capture session id from health check too
                new_sid = resp.headers.get("Mcp-Session-Id")
                if new_sid:
                    set_session_id(new_sid)
                return True
        except Exception:
            pass
        attempt += 1
        if attempt == 5:
            sys.stderr.write(
                f"mcp-stdio-bridge: server not up yet at {url}, waiting...\n"
            )
        time.sleep(0.5)
    return False

# -- Main loop ---------------------------------------------------------------

def main():
    url, timeout, max_concurrent = parse_args()
    if not wait_for_server(url):
        sys.stderr.write(f"mcp-stdio-bridge: no server answering at {url} after 30s\n")
        sys.exit(1)
    sys.stderr.write(f"mcp-stdio-bridge: bridging stdio -> {url}\n")

    pool = ThreadPoolExecutor(max_workers=max_concurrent)
    try:
        for raw_line in sys.stdin.buffer:
            line = raw_line.strip()
            if not line:
                continue
            if len(line) > MAX_LINE_BYTES:
                sys.stderr.write(f"mcp-stdio-bridge: frame exceeds {MAX_LINE_BYTES} bytes, dropped\n")
                continue
            decoded = line.decode("utf-8", errors="replace")
            pool.submit(forward_frame, url, timeout, decoded)
    except KeyboardInterrupt:
        pass
    pool.shutdown(wait=True)
    sys.stderr.write("mcp-stdio-bridge: stdin closed, exiting\n")

if __name__ == "__main__":
    main()

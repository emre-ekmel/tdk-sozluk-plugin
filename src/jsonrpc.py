"""Minimal JSON-RPC 2.0 server for Flow Launcher's Python_v2 plugin protocol.

Flow Launcher starts the plugin once and keeps it alive, exchanging one JSON
message per line over stdin/stdout. stdout is reserved for protocol messages;
log to stderr instead of printing.
"""

import json
import sys
import traceback

METHOD_NOT_FOUND = -32601
INTERNAL_ERROR = -32603


def handle_message(handlers, message):
    """Dispatch one decoded request. Returns the response dict, or None for notifications."""
    method = message.get("method")
    params = message.get("params") or []
    msg_id = message.get("id")

    handler = handlers.get(method)
    if handler is None:
        error = {"code": METHOD_NOT_FOUND, "message": f"Method not found: {method}"}
        return None if msg_id is None else {"jsonrpc": "2.0", "id": msg_id, "error": error}

    try:
        result = handler(*params) if isinstance(params, list) else handler(**params)
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        error = {"code": INTERNAL_ERROR, "message": str(exc)}
        return None if msg_id is None else {"jsonrpc": "2.0", "id": msg_id, "error": error}

    if msg_id is None:
        return None
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def serve(handlers, stdin=None, stdout=None, stop_methods=("close",)):
    """Read requests line by line until EOF or a stop method has been answered."""
    stdin = stdin or sys.stdin.buffer
    stdout = stdout or sys.stdout.buffer

    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            print(f"Invalid JSON-RPC message: {line!r}", file=sys.stderr)
            continue

        response = handle_message(handlers, message)
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False).encode("utf-8") + b"\n")
            stdout.flush()

        if message.get("method") in stop_methods:
            break

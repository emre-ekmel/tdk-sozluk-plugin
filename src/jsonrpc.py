"""Minimal JSON-RPC 2.0 server for Flow Launcher's Python_v2 plugin protocol.

Flow Launcher starts the plugin once and keeps it alive, exchanging one JSON
message per line over stdin/stdout. stdout is reserved for protocol messages;
log to stderr instead of printing.
"""

import concurrent.futures
import json
import sys
import threading
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


class Server:
    """Reads requests line by line until EOF or a stop method has been answered.

    Methods listed in `concurrent` run on worker threads so a slow one (a query
    waiting on the network) doesn't hold up the next keystroke; responses may
    then arrive out of order, which JSON-RPC ids allow.
    """

    def __init__(self, handlers, stdin=None, stdout=None, concurrent=(), stop_methods=("close",), max_workers=4):
        self._handlers = handlers
        self._stdin = stdin or sys.stdin.buffer
        self._stdout = stdout or sys.stdout.buffer
        self._concurrent = set(concurrent)
        self._stop_methods = set(stop_methods)
        self._max_workers = max_workers
        self._write_lock = threading.Lock()

    def notify(self, method, params):
        """Send a notification to Flow (e.g. a public API call like CopyToClipboard)."""
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def serve(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix="rpc") as pool:
            for line in self._stdin:
                line = line.strip()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                except ValueError:
                    print(f"Invalid JSON-RPC message: {line!r}", file=sys.stderr)
                    continue
                if not isinstance(message, dict) or "method" not in message:
                    continue  # responses to our notifications, or junk

                method = message.get("method")
                if method in self._concurrent:
                    pool.submit(self._dispatch, message)
                    continue

                self._dispatch(message)
                if method in self._stop_methods:
                    break

    def _dispatch(self, message):
        response = handle_message(self._handlers, message)
        if response is not None:
            self._write(response)

    def _write(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8") + b"\n"
        with self._write_lock:
            self._stdout.write(data)
            self._stdout.flush()


def serve(handlers, stdin=None, stdout=None, stop_methods=("close",)):
    Server(handlers, stdin=stdin, stdout=stdout, stop_methods=stop_methods).serve()

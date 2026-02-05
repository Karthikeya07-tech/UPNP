"""
Serve a single local fil e over HTTP so a DLNA renderer on the same network can play it.
"""
import http.server
import os
import socket
import threading
from typing import Callable


def get_local_ip() -> str:
    """Get this machine's IP on the local network (e.g. WiFi)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def serve_file_once(file_path: str, port: int = 0) -> tuple[str, Callable[[], None]]:
    """
    Start a background HTTP server that serves one file.
    Returns (url_to_file, stop_server_callable).
    port=0 means pick a random free port.
    """
    path = os.path.abspath(file_path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Not a file: {file_path}")

    filename = os.path.basename(path)
    parent = os.path.dirname(path)

    class OneFileHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=parent, **kwargs)

        def do_GET(self):
            if self.path.strip("/") == filename or self.path == "/" + filename:
                self.path = "/" + filename
                return super().do_GET()
            self.send_error(404, "Not found")

        def log_message(self, format, *args):
            pass

    server = http.server.HTTPServer(("0.0.0.0", port), OneFileHandler)
    port = server.server_address[1]
    ip = get_local_ip()
    url = f"http://{ip}:{port}/{filename}"

    def run():
        server.serve_forever()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    def stop():
        server.shutdown()
        server.server_close()

    return url, stop

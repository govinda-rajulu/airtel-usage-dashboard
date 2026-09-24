#!/bin/bash
python3 - <<'PY'
import http.server, socketserver, urllib.request, urllib.error
UP = "http://127.0.0.1:9223"
class H(http.server.BaseHTTPRequestHandler):
    def _go(self):
        try:
            with urllib.request.urlopen(urllib.request.Request(UP + self.path), timeout=30) as r:
                body = r.read()
                self.send_response(r.status)
                for k, v in r.headers.items():
                    if k.lower() not in ("transfer-encoding", "connection"):
                        self.send_header(k, v)
                self.end_headers(); self.wfile.write(body)
        except urllib.error.HTTPError as e:
            self.send_response(e.code); self.end_headers(); self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502); self.end_headers(); self.wfile.write(f"browser not reachable on 9223: {e}".encode())
    do_GET = do_POST = do_PUT = do_DELETE = _go
    def log_message(self, *a): pass
socketserver.ThreadingTCPServer.allow_reuse_address = True
with socketserver.ThreadingTCPServer(("127.0.0.1", 8080), H) as srv:
    print("forwarding 8080 -> 9223; open Web Preview on port 8080")
    srv.serve_forever()
PY

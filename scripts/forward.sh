#!/bin/bash
python3 - <<'PY'
import asyncio, http.server, socketserver, threading, urllib.request, urllib.error
import websockets

UP = "127.0.0.1:9223"

# HTTP half (unchanged, already proven)
class H(http.server.BaseHTTPRequestHandler):
    def _go(self):
        try:
            with urllib.request.urlopen(urllib.request.Request(f"http://{UP}" + self.path), timeout=30) as r:
                body = r.read()
                self.send_response(r.status)
                for k, v in r.headers.items():
                    if k.lower() not in ("transfer-encoding", "connection"):
                        self.send_header(k, v)
                self.end_headers(); self.wfile.write(body)
        except urllib.error.HTTPError as e:
            self.send_response(e.code); self.end_headers(); self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502); self.end_headers(); self.wfile.write(str(e).encode())
    do_GET = do_POST = do_PUT = do_DELETE = _go
    def log_message(self, *a): pass

# websocket half on 8081
async def pipe(ws):
    path = ws.request.path if hasattr(ws, "request") else "/"
    try:
        async with websockets.connect(f"ws://{UP}{path}", max_size=None) as up:
            async def a2b():
                async for m in ws: await up.send(m)
            async def b2a():
                async for m in up: await ws.send(m)
            await asyncio.gather(a2b(), b2a())
    except Exception:
        pass

async def ws_main():
    async with websockets.serve(pipe, "127.0.0.1", 8081, max_size=None):
        print("ws bridge on 8081 -> 9223")
        await asyncio.Future()

socketserver.ThreadingTCPServer.allow_reuse_address = True
srv = socketserver.ThreadingTCPServer(("127.0.0.1", 8080), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
print("http on 8080 -> 9223")
asyncio.run(ws_main())
PY

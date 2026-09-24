#!/usr/bin/env python3
"""Screencast viewer: watch + drive the collector's browser from a plain web page."""
import base64, json, threading, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

frame = {"img": None, "ts": 0}
lock = threading.Lock()

def cast():
    with sync_playwright() as pw:
        b = pw.chromium.connect_over_cdp("http://127.0.0.1:9223", timeout=15_000)
        page = [p for p in b.contexts[0].pages if p.url != "about:blank"] or b.contexts[0].pages
        page = page[0] if isinstance(page, list) else page
        cdp = b.contexts[0].new_cdp_session(page)
        def on_frame(p):
            with lock:
                frame["img"] = p["data"]; frame["ts"] = time.time()
        cdp.on("Page.screencastFrame", on_frame)
        def ack_loop():
            n = 0
            while True:
                with lock: cur = frame["ts"]
                try: cdp.send("Page.screencastFrameAck", {"sessionId": n})
                except Exception: pass
                n += 1; time.sleep(0.05)
        threading.Thread(target=ack_loop, daemon=True).start()
        cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 70, "everyNthFrame": 1})
        cast.page, cast.cdp = page, cdp
        while True: time.sleep(1)

HTML = """<!doctype html><meta charset=utf-8><title>Airtel capture viewer</title>
<style>body{margin:0;background:#111;color:#eee;font:14px system-ui;display:flex;flex-direction:column;height:100vh}
#bar{padding:8px;background:#222;display:flex;gap:8px}#url{flex:1;padding:6px;border-radius:6px;border:1px solid #444;background:#111;color:#eee}
button{padding:6px 14px;border:0;border-radius:6px;background:#e0202c;color:#fff;font-weight:600}
#view{flex:1;background-size:contain;background-repeat:no-repeat;background-position:center;cursor:crosshair}</style>
<div id=bar><input id=url placeholder="type text or URL here"><button onclick=go()>Go / Type+Enter</button></div>
<div id=view></div>
<script>
const v=document.getElementById('view');let W=1280,H=800;
async function tick(){const r=await fetch('/frame');const d=await r.json();
if(d.img){v.style.backgroundImage='url(data:image/jpeg;base64,'+d.img+')';W=d.w;H=d.h}
v.innerHTML=''}
setInterval(tick,500);
v.onclick=async e=>{const r=v.getBoundingClientRect();const s=Math.min(r.width/W,r.height/H);
const ox=(r.width-W*s)/2,oy=(r.height-H*s)/2;
await fetch('/click?x='+Math.round((e.clientX-r.left-ox)/s)+'&y='+Math.round((e.clientY-r.top-oy)/s))};
async function go(){const t=document.getElementById('url').value;await fetch('/type?t='+encodeURIComponent(t));document.getElementById('url').value=''}
</script>"""

class H(BaseHTTPRequestHandler):
    def _j(self, d):
        b = json.dumps(d).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if u.path == "/":
            b = HTML.encode(); self.send_response(200); self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        elif u.path == "/frame":
            with lock: img = frame["img"]
            try: vw = cast.page.viewport_size or {"width": 1280, "height": 800}
            except Exception: vw = {"width": 1280, "height": 800}
            self._j({"img": img, "w": vw["width"], "h": vw["height"]})
        elif u.path == "/click":
            x, y = float(q["x"][0]), float(q["y"][0])
            for t in ("mousePressed", "mouseReleased"):
                cast.cdp.send("Input.dispatchMouseEvent", {"type": t, "x": x, "y": y, "button": "left", "clickCount": 1})
            self._j({"ok": True})
        elif u.path == "/type":
            t = q.get("t", [""])[0]
            if t.startswith("http"):
                cast.page.goto(t, wait_until="domcontentloaded")
            else:
                cast.page.keyboard.type(t); cast.page.keyboard.press("Enter")
            self._j({"ok": True})
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, *a): pass

threading.Thread(target=cast, daemon=True).start()
print("viewer on http://127.0.0.1:8080  (Web Preview port 8080)")
ThreadingHTTPServer(("127.0.0.1", 8080), H).serve_forever()

"""USTA — LUCIUS-ov govor z oknom: lokalni strežnik (127.0.0.1:5824).

Dovod:   lucius.html, GOVOR.md, skatla.json (samo branje)
Funkcija: GET / (obraz), GET /govor (nit), GET /stanje (škatle), POST /poslji (zapeče besede v nit)
Odvod:   GOVOR.md (append, © VBL) — nič izmišljenega (K1)
"""
import threading
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Sedež telesa (ukaz Lastnika, 23. 10. 2026: »vse«): D:\Lucius Gaius.
# Mila varovalka (vrata potujejo s telesom, VBL §2): če sedež ne stoji,
# se ONI izmeri iz mape telesa (lucius/ → prevoz/ → starš = sedež).
ONI = Path(r"D:\Lucius Gaius")
if not (ONI / "prevoz" / "prevoznik.py").exists():
    ONI = Path(__file__).resolve().parent.parent.parent
POGOVOR = ONI / "prevoz" / "pogovor"
SKATLE = ONI / "prevoz" / "skatle"
LUCIUS_HTML = POGOVOR / "lucius.html"
CEST = timezone(timedelta(hours=2))
NL = chr(10)


def out(*a):
    print(*a)


class LuciusHandler(BaseHTTPRequestHandler):
    def _odgovori(self, telo, vrsta):
        self.send_response(200)
        self.send_header("Content-Type", vrsta + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(telo)))
        self.end_headers()
        self.wfile.write(telo)

    def do_GET(self):
        try:
            if self.path.split("?")[0] in ("/", "/lucius") and LUCIUS_HTML.exists():
                self._odgovori(LUCIUS_HTML.read_bytes(), "text/html")
            elif self.path == "/govor":
                self._odgovori((POGOVOR / "GOVOR.md").read_bytes(), "text/plain")
            elif self.path.startswith("/povej?text="):
                from urllib.parse import parse_qs, unquote
                try:
                    from lucius.jedro import povej
                    qs = parse_qs(self.path.split("?", 1)[1])
                    povej(unquote(qs.get("text", [""])[0]))
                    self._odgovori(b'{"ok": true}', "application/json")
                except ImportError:
                    self.send_response(500)
                    self.end_headers()
            elif self.path == "/manifest.json":
                self._odgovori((POGOVOR / "manifest.json").read_bytes(), "application/json")
            elif self.path == "/sw.js":
                self._odgovori((POGOVOR / "sw.js").read_bytes(), "text/javascript")
            elif self.path == "/icon.svg":
                self._odgovori((POGOVOR / "icon.svg").read_bytes(), "image/svg+xml")
            elif self.path == "/logo-192.png":
                self._odgovori((POGOVOR / "logo-192.png").read_bytes(), "image/png")
            elif self.path == "/logo-512.png":
                self._odgovori((POGOVOR / "logo-512.png").read_bytes(), "image/png")
            elif self.path == "/ozadje.png":
                self._odgovori((POGOVOR / "ozadje.png").read_bytes(), "image/png")
            elif self.path == "/stanje":
                pot = SKATLE / "skatla.json"
                self._odgovori(pot.read_bytes() if pot.exists() else b"{}", "application/json")
            else:
                self.send_response(404)
                self.end_headers()
        except Exception:
            self.send_response(500)
            self.end_headers()

    def do_POST(self):
        try:
            dolzina = int(self.headers.get("Content-Length", "0") or "0")
            besedilo = self.rfile.read(dolzina).decode("utf-8", errors="replace").strip()
            if not besedilo:
                self.send_response(400)
                self.end_headers()
                return
            cas = datetime.now(CEST).strftime("%Y-%m-%d %H:%M")
            zapis = NL + "**[" + cas + " | LASTNIK (okno)]** ❡-sporočilo:" + NL + "- ❡ odgovor: " + besedilo + NL
            with open(POGOVOR / "GOVOR.md", "a", encoding="utf-8") as f:
                f.write(zapis)
            self._odgovori(b'{"ok": true}', "application/json")
        except Exception:
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def streznik(port=5824):
    """Živi strežnik LUCIUS-ovega okna (127.0.0.1:5824 — LUCI po tipkovnici)."""
    httpd = ThreadingHTTPServer(("0.0.0.0", port), LuciusHandler)  # telefon doseze okno po lokalni mrezi (ukaz Lastnika, 21. 10.)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    out("  usta: LUCIUS govori na http://127.0.0.1:" + str(port))
    return httpd

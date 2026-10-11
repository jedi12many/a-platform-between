"""The art desk's server (docs/art.md): serves the editor (tools/artdesk/) and the art
files (content/art/), and saves them back when the page says so, on this machine only.

    python3 tools/artdesk/serve.py [--port 8064] [--art DIR]     (make artdesk)

then open http://localhost:8064/. A save is checked by tools/art.py's rules before it's
written: a file that breaks one isn't written, and the page is told why. Only the four art
files can be written, nothing else. --art points it at another folder (the tests use a
copy).

    GET  /                 the editor
    GET  /meta.json        the palette, the colours' names, the files' kinds and sizes, the
                           races and foes the game has (each needs a figure)
    GET  /art/NAME.txt     an art file
    PUT  /art/NAME.txt     saves it: 200, or 400 and what's wrong
"""

import http.server
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "registry"))
import art  # noqa: E402
import registry  # noqa: E402
from c64pic import PALETTE  # noqa: E402

PAGES = {"/": ("index.html", "text/html"), "/artdesk.js": ("artdesk.js", "text/javascript"),
         "/artdesk.css": ("artdesk.css", "text/css")}


def meta():
    reg = registry.load()
    by_id = lambda kind: [n for n, _ in sorted(reg[kind].items(), key=lambda kv: kv[1]["id"])]
    return {
        "palette": [list(c) for c in PALETTE],
        "colours": art.COLOURS,
        "terrain": art.TERRAIN,
        "files": {name: {kind: {"w": w, "h": h, "dots": dots}
                         for kind, (w, h, dots) in kinds.items()}
                  for name, kinds in art.FILES.items()},
        "races": by_id("races"),
        "foes": by_id("foes"),
        "foe_names": {n: reg["foes"][n]["display"] for n in by_id("foes")},
    }


class Desk(http.server.BaseHTTPRequestHandler):
    folder = art.ART

    def send(self, code, body, kind="text/plain; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def art_name(self):
        """The art file the path names, or None."""
        p = self.path.split("?")[0]
        if p.startswith("/art/") and p.endswith(".txt") and p[5:-4] in art.FILES:
            return p[5:-4]
        return None

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in PAGES:
            name, kind = PAGES[p]
            with open(os.path.join(HERE, name), "rb") as f:
                return self.send(200, f.read(), kind)
        if p == "/meta.json":
            return self.send(200, json.dumps(meta()), "application/json")
        name = self.art_name()
        if name:
            with open(art.path_of(name, self.folder)) as f:
                return self.send(200, f.read())
        self.send(404, "not here")

    def do_PUT(self):
        name = self.art_name()
        if not name:
            return self.send(403, "only the art files can be written")
        n = int(self.headers.get("Content-Length", 0))
        text = self.rfile.read(n).decode("utf-8")
        try:
            art.parse(name, text)
        except art.Problem as e:
            return self.send(400, str(e))
        with open(art.path_of(name, self.folder), "w") as f:
            f.write(text)
        self.send(200, "saved")

    def log_message(self, *args):
        pass


def main(argv):
    port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8064
    if "--art" in argv:
        Desk.folder = argv[argv.index("--art") + 1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Desk)
    print(f"The art desk: http://localhost:{port}/ (art in {os.path.abspath(Desk.folder)}); "
          "Ctrl-C to stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

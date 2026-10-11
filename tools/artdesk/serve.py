"""The studio's server (docs/art.md, docs/arena.md): the art desk (tools/artdesk/) and the
arena (tools/arena/web/), side by side, on this machine only. It serves the editor and the
art files (content/art/), and saves them back when the page says so; and it serves the
arena, which draws the art as it is now, so a figure drawn here can be fought straight away.

    python3 tools/artdesk/serve.py [--port 8064] [--art DIR]     (make studio)

then open http://localhost:8064/. A save is checked by tools/art.py's rules before it's
written: a file that breaks one isn't written, and the page is told why. Only the four art
files can be written, nothing else. --art points it at another folder (the tests use a
copy).

    GET  /                 the editor
    GET  /meta.json        the palette, the colours' names, the files' kinds and sizes, the
                           races and foes the game has (each needs a figure)
    GET  /art/NAME.txt     an art file
    PUT  /art/NAME.txt     saves it: 200, or 400 and what's wrong
    GET  /arena/           the arena: its page from tools/arena/web/, its rules and
                           scenarios from build/arena-web/ (make arena-web), and
                           /arena/art.json made from the art files as they are now
"""

import http.server
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "registry"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "arena", "web"))
import art  # noqa: E402
import art_json  # noqa: E402
import registry  # noqa: E402
from c64pic import PALETTE  # noqa: E402

PAGES = {"/": ("index.html", "text/html"), "/artdesk.js": ("artdesk.js", "text/javascript"),
         "/artdesk.css": ("artdesk.css", "text/css")}

# The arena: its page (edited in tools/arena/web/), and what make arena-web builds.
ARENA_PAGE = os.path.join(os.path.dirname(HERE), "arena", "web")
ARENA_BUILT = os.path.join(os.path.dirname(HERE), "..", "build", "arena-web")
ARENA_FILES = {"index.html": (ARENA_PAGE, "text/html"), "arena.js": (ARENA_PAGE, "text/javascript"),
               "arena.css": (ARENA_PAGE, "text/css"), "rules.js": (ARENA_BUILT, "text/javascript"),
               "rules.wasm": (ARENA_BUILT, "application/wasm"),
               "scenarios.json": (ARENA_BUILT, "application/json"),
               "items.json": (ARENA_BUILT, "application/json"),
               "lab.json": (ARENA_BUILT, "application/json"),
               "conditions.json": (ARENA_BUILT, "application/json")}


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
        if p == "/arena":
            self.send_response(301)
            self.send_header("Location", "/arena/")
            self.end_headers()
            return None
        if p.startswith("/arena/"):
            return self.arena(p[len("/arena/"):] or "index.html")
        if p == "/meta.json":
            return self.send(200, json.dumps(meta()), "application/json")
        name = self.art_name()
        if name:
            with open(art.path_of(name, self.folder)) as f:
                return self.send(200, f.read())
        self.send(404, "not here")

    def arena(self, name):
        if name == "build.json":
            try:
                commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                                        text=True, cwd=HERE).stdout.strip() or "unknown"
            except OSError:
                commit = "unknown"
            return self.send(200, json.dumps({"commit": commit, "built": "studio"}), "application/json")
        if name == "art.json":
            return self.send(200, json.dumps(art_json.build(self.folder)), "application/json")
        if name not in ARENA_FILES:
            return self.send(404, "not here")
        folder, kind = ARENA_FILES[name]
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            return self.send(404, "The arena isn't built: run make arena-web (or make studio).")
        with open(path, "rb") as f:
            return self.send(200, f.read(), kind)

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
    print(f"The studio: the art desk at http://localhost:{port}/, the arena at "
          f"http://localhost:{port}/arena/ (art in {os.path.abspath(Desk.folder)}); "
          "Ctrl-C to stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

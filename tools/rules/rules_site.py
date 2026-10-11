"""The rules, for the site's Rules tab (docs/rules.md and the pages it lists, as HTML).

    python3 tools/rules/rules_site.py OUT

Writes OUT/index.html (docs/rules.md) and OUT/NAME.html for every page rules.md links to,
each with the reading order beside it. A link to another of those pages stays on the
site; a link to any other doc goes to it on GitHub. Only the Markdown the docs use is
understood: headings, paragraphs, lists (nested by indent), tables, fenced and indented
code, block quotes, **bold**, *italic*, `code` and links. The docs are the source: edit
them, never the HTML.
"""

import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, "docs")
REPO = "https://github.com/jedi12many/a-platform-between/blob/main/docs/"


def slug(text):
    """GitHub's anchor for a heading: lower case, punctuation gone, spaces to hyphens."""
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


class Page:
    def __init__(self, published):
        self.published = published      # {"turn.md": "turn.html", ...}

    def link(self, target):
        path, _, anchor = target.partition("#")
        if re.match(r"^[a-z]+:", target) or not path.endswith(".md"):
            return target if path else "#" + anchor
        name = os.path.basename(path)
        if name in self.published:
            return self.published[name] + ("#" + anchor if anchor else "")
        return REPO + path + ("#" + anchor if anchor else "")

    def inline(self, text):
        out = []
        for i, part in enumerate(re.split(r"(`[^`]*`)", text)):
            if i % 2:
                out.append("<code>" + html.escape(part[1:-1]) + "</code>")
                continue
            part = html.escape(part, quote=False)
            part = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                          lambda m: f'<a href="{html.escape(self.link(m.group(2)))}">{m.group(1)}</a>', part)
            part = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", part)
            part = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", part)
            part = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"<em>\1</em>", part)
            out.append(part)
        return "".join(out)

    def render(self, text):
        lines = text.split("\n")
        out, i = [], 0
        para = []

        def flush():
            if para:
                out.append("<p>" + self.inline(" ".join(s.strip() for s in para)) + "</p>")
                para.clear()

        while i < len(lines):
            line = lines[i]
            if line.startswith("```"):
                flush()
                j = i + 1
                while j < len(lines) and not lines[j].startswith("```"):
                    j += 1
                out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>")
                i = j + 1
                continue
            m = re.match(r"^(#{1,6})\s+(.*)$", line)
            if m:
                flush()
                n, body = len(m.group(1)), self.inline(m.group(2))
                out.append(f'<h{n} id="{slug(m.group(2))}">{body}</h{n}>')
                i += 1
                continue
            if not line.strip():
                flush()
                i += 1
                continue
            if line.startswith("    ") and not para and not re.match(r"^\s*([-*]|\d+\.)\s", line):
                flush()
                j = i
                block = []
                while j < len(lines) and (lines[j].startswith("    ") or not lines[j].strip()):
                    block.append(lines[j][4:])
                    j += 1
                while block and not block[-1].strip():
                    block.pop()
                out.append("<pre><code>" + html.escape("\n".join(block)) + "</code></pre>")
                i = j
                continue
            if line.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
                flush()
                cells = lambda s: [c.strip() for c in s.strip().strip("|").split("|")]
                head = cells(line)
                rows = []
                j = i + 2
                while j < len(lines) and lines[j].lstrip().startswith("|"):
                    rows.append(cells(lines[j]))
                    j += 1
                t = ["<table><thead><tr>"] + [f"<th>{self.inline(c)}</th>" for c in head] + ["</tr></thead><tbody>"]
                for r in rows:
                    t += ["<tr>"] + [f"<td>{self.inline(c)}</td>" for c in r] + ["</tr>"]
                out.append("".join(t) + "</tbody></table>")
                i = j
                continue
            if line.startswith(">"):
                flush()
                j = i
                block = []
                while j < len(lines) and lines[j].startswith(">"):
                    block.append(lines[j][1:].lstrip())
                    j += 1
                out.append("<blockquote>" + self.render("\n".join(block)) + "</blockquote>")
                i = j
                continue
            if re.match(r"^\s*([-*]|\d+\.)\s", line) and not para:
                html_list, i = self.list_at(lines, i)
                out.append(html_list)
                continue
            para.append(line)
            i += 1
        flush()
        return "\n".join(out)

    def list_at(self, lines, i):
        """A list starting at line i (and the lists inside it, by indent)."""
        indent = len(lines[i]) - len(lines[i].lstrip())
        ordered = bool(re.match(r"^\s*\d+\.", lines[i]))
        items = []
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                # A blank line ends the list unless the next line carries it on.
                if i + 1 < len(lines) and re.match(r"^\s*([-*]|\d+\.)\s", lines[i + 1]) \
                        and len(lines[i + 1]) - len(lines[i + 1].lstrip()) >= indent:
                    i += 1
                    continue
                break
            ind = len(line) - len(line.lstrip())
            m = re.match(r"^\s*([-*]|\d+\.)\s+(.*)$", line)
            if m and ind == indent:
                items.append([m.group(2)])
                i += 1
            elif m and ind > indent:
                sub, i = self.list_at(lines, i)
                items[-1].append(sub)
            elif ind > indent and items:
                items[-1].append(line.strip())
                i += 1
            else:
                break
        tag = "ol" if ordered else "ul"
        parts = []
        for it in items:
            text = [x for x in it if not x.startswith("<")]
            subs = [x for x in it if x.startswith("<")]
            parts.append("<li>" + self.inline(" ".join(text)) + "".join(subs) + "</li>")
        return f"<{tag}>" + "".join(parts) + f"</{tag}>", i


STYLE = """
:root { --bg: #f3efe4; --panel: #fffdf7; --ink: #1d2226; --muted: #5f5a4e; --line: #d9d2c0;
        --accent: #3d6b47; --code: #ebe5d6; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --bg: #12161a; --panel: #1b2127; --ink: #e8e2d0; --muted: #a39d8c;
    --line: #2c343c; --accent: #8fc59a; --code: #232a31; color-scheme: dark; }
}
:root[data-theme="dark"] { --bg: #12161a; --panel: #1b2127; --ink: #e8e2d0; --muted: #a39d8c;
  --line: #2c343c; --accent: #8fc59a; --code: #232a31; color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 1rem/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; }
.page { display: grid; grid-template-columns: 15rem minmax(0, 46rem); gap: 2rem; padding: 1.5rem 16px 3rem; justify-content: center; }
nav.order { position: sticky; top: 1rem; align-self: start; font-size: 0.9rem; }
nav.order ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
nav.order a { display: block; padding: 0.2rem 0.6rem; border-radius: 4px; color: var(--muted); text-decoration: none; }
nav.order a:hover { color: var(--ink); }
nav.order a[aria-current="page"] { background: var(--panel); color: var(--ink); font-weight: 600; }
nav.order .n { display: inline-block; width: 2rem; color: var(--accent); font-family: ui-monospace, Menlo, monospace; }
main { min-width: 0; }
h1, h2, h3 { line-height: 1.25; text-wrap: balance; }
h1 { margin-top: 0; }
a { color: var(--accent); }
code { font: 0.88em ui-monospace, Menlo, Consolas, monospace; background: var(--code); padding: 0 0.25em; border-radius: 3px; }
pre { background: var(--code); padding: 0.75rem 1rem; border-radius: 6px; overflow-x: auto; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; font-size: 0.92rem; display: block; overflow-x: auto; }
th, td { border-bottom: 1px solid var(--line); padding: 0.35rem 0.6rem; text-align: left; vertical-align: top; }
th { background: var(--panel); }
blockquote { margin: 0; padding-left: 1rem; border-left: 3px solid var(--line); color: var(--muted); }
@media (max-width: 760px) { .page { grid-template-columns: minmax(0, 1fr); } nav.order { position: static; } }
"""


def reading_order(index_text):
    """The pages rules.md lists, in its order: [(number, file, title)]."""
    out = []
    for line in index_text.split("\n"):
        m = re.match(r"^\|\s*(\w+)\s*\|\s*(.+?)\s*\|", line)
        if not m:
            continue
        for name in re.findall(r"\[([a-z0-9-]+\.md)\]", m.group(2)):
            out.append((m.group(1), name))
    return out


def title_of(text, name):
    m = re.search(r"^#\s+(.*)$", text, re.M)
    return re.sub(r"[*`]", "", m.group(1)) if m else name


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    out = argv[1]
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(DOCS, "rules.md")) as f:
        index = f.read()
    order = reading_order(index)
    published = {"rules.md": "index.html"}
    published.update({name: name[:-3] + ".html" for _, name in order})
    texts = {"rules.md": index}
    for _, name in order:
        with open(os.path.join(DOCS, name)) as f:
            texts[name] = f.read()
    page = Page(published)
    nav = [("", "rules.md", "Reading order")] + [(n, name, title_of(texts[name], name)) for n, name in order]
    for name, text in texts.items():
        items = "".join(
            f'<li><a href="{published[f]}"{" aria-current=page" if f == name else ""}>'
            f'<span class="n">{html.escape(n)}</span>{html.escape(t)}</a></li>' for n, f, t in nav)
        doc = ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">\n"
               "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
               f"<title>{html.escape(title_of(text, name))} · A Platform Between</title>\n"
               f"<style>{STYLE}</style></head><body><div class=\"page\">\n"
               f"<nav class=\"order\" aria-label=\"The rules\"><ol>{items}</ol></nav>\n"
               f"<main>\n{page.render(text)}\n</main></div></body></html>\n")
        with open(os.path.join(out, published[name]), "w") as f:
            f.write(doc)
    print(f"rules: {len(texts)} pages in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

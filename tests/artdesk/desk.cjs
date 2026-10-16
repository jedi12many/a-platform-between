// Drives the art desk (tools/artdesk/, served by serve.py) in headless Chromium the way an
// artist would: choosing a file and an entry, a dot and a tool, clicking on the grid, the
// buttons and the prompts, and saving. tests/artdesk/check_artdesk.py checks what lands in
// the files.
//
//   node desk.cjs URL roundtrip                   each file's text as the page would save it
//   node desk.cjs URL paint FILE ENTRY DOT X Y    one dot painted, saved (FILE: a look's,
//                                                 tiles16-forest, chosen by its look)
//   node desk.cjs URL undo FILE ENTRY DOT X Y     painted, undone, saved
//   node desk.cjs URL colour FILE ENTRY COLOUR    its own colour chosen, saved
//   node desk.cjs URL box FILE NEW DOT X0 Y0 X1 Y1   a new entry with a box drawn, saved
//   node desk.cjs URL fill FILE ENTRY DOT X Y     a flood fill, saved
//   node desk.cjs URL flip FILE ENTRY             flipped twice, shifted right then left, saved
//   node desk.cjs URL paste FILE TEXT FIT MAP INTO   art pasted as text (the file TEXT), fitted
//                                                 (trim, squeeze), each character mapped
//                                                 (MAP: 0=.,1=a,...), as a new entry (INTO:
//                                                 new) or into one (an entry's name), saved
//   node desk.cjs URL shot FILE ENTRY PATH        a screenshot
//
// DOT is the dot's number on the toolbar (1 is see-through or the background). Prints what
// the page's status line says at the end, and anything the page threw.
"use strict";

const { chromium } = require("playwright");

async function main() {
  const [url, what, ...args] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  let answer = null;
  page.on("dialog", (d) => d.accept(answer === null ? undefined : answer));
  await page.goto(url);
  await page.waitForFunction(() => window.artdesk && window.artdesk.ready);

  // A look's tiles file (tiles16-forest): its look chosen, then Tiles 16.
  const open = async (file, entry) => {
    const [base, look] = file.split("-");
    if (base.startsWith("tiles")) await page.selectOption("[data-look]", look || "");
    await page.click(`[data-file="${base}"]`);
    if (entry) await page.click(`#entry-list [data-name="${entry}"]`);
  };
  // The middle of dot X, Y on the grid, in page pixels.
  const dot = async (x, y) => page.evaluate(([x, y]) => {
    const g = document.getElementById("grid");
    const r = g.getBoundingClientRect();
    const w = Number(g.dataset.w), h = Number(g.dataset.h);
    return { x: r.left + (x + 0.5) * r.width / w, y: r.top + (y + 0.5) * r.height / h };
  }, [x, y]);
  const click = async (x, y) => {
    const p = await dot(x, y);
    await page.mouse.click(p.x, p.y);
  };
  const save = async () => {
    await page.click("#save");
    await page.waitForFunction(() => /Saved|Not saved|Nothing/.test(
      document.getElementById("status").textContent));
  };

  if (what === "roundtrip") {
    const out = {};
    const meta = await (await page.request.get(url + "meta.json")).json();
    for (const f of Object.keys(meta.files)) {
      out[f] = await page.evaluate((f) => window.artdesk.serialise(f), f);
    }
    console.log(JSON.stringify(out));
  } else if (what === "paint" || what === "undo") {
    const [file, entry, n, x, y] = args;
    await open(file, entry);
    await page.click(`#dots button:nth-child(${n})`);
    await page.click('[data-tool="pen"]');
    await click(Number(x), Number(y));
    if (what === "undo") await page.click("#undo");
    await save();
  } else if (what === "colour") {
    const [file, entry, colour] = args;
    await open(file, entry);
    await page.click(`[data-colour="${colour}"]`);
    await save();
  } else if (what === "box") {
    const [file, name, n, x0, y0, x1, y1] = args;
    await open(file);
    answer = name;
    await page.click("#new");
    await page.click(`#dots button:nth-child(${n})`);
    await page.click('[data-tool="box"]');
    const a = await dot(Number(x0), Number(y0));
    const b = await dot(Number(x1), Number(y1));
    await page.mouse.move(a.x, a.y);
    await page.mouse.down();
    await page.mouse.move(b.x, b.y, { steps: 5 });
    await page.mouse.up();
    await save();
  } else if (what === "fill") {
    const [file, entry, n, x, y] = args;
    await open(file, entry);
    await page.click(`#dots button:nth-child(${n})`);
    await page.keyboard.press("f");
    await click(Number(x), Number(y));
    await save();
  } else if (what === "flip") {
    const [file, entry] = args;
    await open(file, entry);
    await page.click("#flip");
    await page.click("#flip");
    await page.click('[data-shift="1,0"]');
    await page.click('[data-shift="-1,0"]');
    await save();
  } else if (what === "paste") {
    const [file, textFile, fit, map, target, shot] = args;
    await open(file, target === "new" ? null : target);
    await page.click("#paste");
    await page.fill("#paste-text", require("fs").readFileSync(textFile, "utf8"));
    await page.selectOption("#paste-fit", fit);
    for (const pair of map.split(",")) {
      const [c, d] = pair.split("=");
      await page.selectOption(`#paste-map select[data-char="${c}"]`, d);
    }
    await page.check(`input[name="paste-into"][value="${target === "new" ? "new" : "this"}"]`);
    if (shot) await page.screenshot({ path: shot });
    console.log("notes: " + (await page.textContent("#paste-notes")));
    await page.click("#paste-apply");
    await save();
  } else if (what === "shot") {
    const [file, entry, path] = args;
    await open(file, entry);
    await page.screenshot({ path });
  }
  console.log("status: " + await page.textContent("#status"));
  for (const e of errors) console.log("page error: " + e);
  await browser.close();
}

main().catch((e) => { console.log("error: " + e.message); process.exit(1); });

// The browser build (build/web/, `make web`) played in headless Chromium with Playwright.
//
//   node tests/modern/check_web.cjs play DEPARTURE CHOICES [THEN]   the transcript, to stdout
//   node tests/modern/check_web.cjs keys                       typing and clicking work
//
// `play` hands the page a choices file, as the desktop's --choices does, and prints the
// transcript the WebAssembly game writes: `make test-modern` compares it with the
// desktop's. `keys` presses real keys and clicks the canvas the way a player would, and
// reads the screen back, row by row.
"use strict";

const fs = require("fs");
const http = require("http");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.join(__dirname, "..", "..", "build", "web");
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".wasm": "application/wasm",
                ".data": "application/octet-stream" };

function serve() {
  const server = http.createServer((req, res) => {
    const name = path.normalize(decodeURIComponent(req.url.split("?")[0])).replace(/^(\.\.[/\\])+/, "");
    const file = path.join(ROOT, name === "/" ? "index.html" : name);
    if (!file.startsWith(ROOT) || !fs.existsSync(file)) {
      res.writeHead(404);
      res.end();
      return;
    }
    res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] || "application/octet-stream" });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve(server)));
}

async function open(server) {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const problems = [];
  page.on("pageerror", (e) => problems.push(String(e)));
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  await page.waitForFunction(() => !document.querySelector("#pick button").disabled, null,
                             { timeout: 60000 });
  return { browser, page, problems };
}

async function screen(page) {
  return page.evaluate(() => {
    const rows = [];
    for (let r = 0; r < 25; ++r) rows.push(Module.UTF8ToString(Module._web_screen_row(r)));
    return rows;
  });
}

// One trip from a choices file; with `thenFile`, the page is reloaded (the machine
// switched off) and a second trip picks up the save from the browser's IndexedDB.
async function play(departure, choicesFile, thenFile) {
  const server = await serve();
  const { browser, page, problems } = await open(server);
  const lines = [];
  for (const file of thenFile ? [choicesFile, thenFile] : [choicesFile]) {
    if (lines.length) {
      lines.push("[switched off and on again]");
      await page.reload();
      await page.waitForFunction(() => !document.querySelector("#pick button").disabled, null,
                                 { timeout: 60000 });
    }
    const choices = fs.readFileSync(file, "utf8");
    await page.evaluate(([d, c]) => Module.start(d, c), [departure, choices]);
    await page.waitForFunction(() => {
      const t = Module.transcript;
      return t.length && (t[t.length - 1] === "[the trip is over]" || t[t.length - 1] === "[end of input]");
    }, null, { timeout: 300000, polling: 200 });
    // Let the save reach IndexedDB before switching off.
    await page.waitForTimeout(500);
    lines.push(...await page.evaluate(() => Module.transcript));
  }
  await browser.close();
  server.close();
  if (problems.length) throw new Error(problems.join("\n"));
  process.stdout.write(lines.join("\n") + "\n");
}

function expect(what, ok) {
  if (!ok) throw new Error("the browser build: " + what);
  console.log("ok  " + what);
}

async function keys() {
  const server = await serve();
  const { browser, page, problems } = await open(server);
  await page.click("text=Departure 00: The Fare");
  await page.waitForTimeout(300);
  let rows = await screen(page);
  expect("it starts at the boarding menu", rows.some((r) => r.startsWith("1. Board")));
  // Click the "1. Board" line, as a player would.
  const row = rows.findIndex((r) => r.startsWith("1. Board"));
  const box = await page.locator("canvas").boundingBox();
  await page.mouse.click(box.x + box.width / 2, box.y + (row + 0.5) * box.height / 25);
  await page.waitForTimeout(300);
  rows = await screen(page);
  expect("a click on a menu line picks it", rows.some((r) => r.includes("Passport")));
  await page.keyboard.type("4PB794AR0A0105AM7HDX");
  await page.keyboard.press("Backspace");
  await page.keyboard.type("T");
  await page.waitForTimeout(200);
  rows = await screen(page);
  expect("typing (and backspace) reaches the game",
         rows[24].startsWith("> 4PB794AR0A0105AM7HDT"));
  await page.keyboard.press("Enter");
  await page.waitForTimeout(200);
  rows = await screen(page);
  expect("Enter ends the line", rows.some((r) => r.startsWith("> 4PB794AR0A0105AM7HDT")) &&
                                rows[24].startsWith("> "));
  const pixels = await page.evaluate(() => {
    const c = document.querySelector("canvas").getContext("2d").getImageData(0, 0, 640, 16).data;
    let lit = 0;
    for (let i = 0; i < c.length; i += 4) if (c[i] || c[i + 1] || c[i + 2]) ++lit;
    return lit;
  });
  expect("the screen is drawn on the canvas (the status bar)", pixels > 1000);
  await browser.close();
  server.close();
  if (problems.length) throw new Error(problems.join("\n"));
}

const [mode, ...args] = process.argv.slice(2);
(mode === "play" ? play(...args) : mode === "keys" ? keys() : Promise.reject(new Error(
  "usage: check_web.cjs play DEPARTURE CHOICES [THEN] | keys"))).catch((e) => {
  console.error("FAIL: " + e.message);
  process.exit(1);
});

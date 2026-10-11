// Plays the arena page (build/site/arena.html) in headless Chromium as a person would: the
// scenarios listed, then for each one asked for, Play, board, read on to the scenario's
// menu, Fight, and the battle screen's first prompt. Prints what it saw, a line a step,
// for tests/arena/check_play.py.
//
//   node play.cjs N...
"use strict";

const fs = require("fs");
const http = require("http");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.join(__dirname, "..", "..", "build", "site");
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".wasm": "application/wasm",
                ".json": "application/json", ".data": "application/octet-stream" };

function serve() {
  const server = http.createServer((req, res) => {
    const name = path.normalize(decodeURIComponent(req.url.split("?")[0]));
    const file = path.join(ROOT, name.endsWith("/") ? name + "index.html" : name);
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

async function main() {
  const server = await serve();
  const url = `http://127.0.0.1:${server.address().port}/`;
  const browser = await chromium.launch();
  try {
    for (const n of process.argv.slice(2).map(Number)) {
      const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
      page.on("pageerror", (e) => console.log("page error: " + e.message));
      await page.goto(url + "arena.html");
      await page.waitForSelector(".scenarios li button");
      console.log(`listed ${await page.locator(".scenarios li").count()}`);
      await page.locator(".scenarios li button").nth(n - 1).click();
      await page.waitForURL(/play\/#departure=arena-/, { timeout: 30000 });
      console.log("departure " + new URL(page.url()).hash.match(/departure=([\w-]+)/)[1]);
      await page.waitForFunction(() => window.Module && Module._web_screen_row, null, { timeout: 60000 });
      const screen = () => page.evaluate(() => {
        const rows = [];
        for (let r = 0; r < 25; ++r) rows.push(Module.UTF8ToString(Module._web_screen_row(r)));
        return rows.join("\n");
      });
      const until = async (re, key) => {
        for (let i = 0; i < 40; ++i) {
          const t = await screen();
          if (re.test(t)) return t;
          if (key) await page.keyboard.press(key);
          await page.waitForTimeout(400);
        }
        return null;
      };
      if (!await until(/1\. Board/)) { console.log("never asked to board"); continue; }
      await page.waitForTimeout(600);           // (the menu is read once it's drawn)
      await page.keyboard.press("1");
      const menu = await until(/1\. Fight/, "Space");
      console.log(menu ? "scenario " + (menu.match(/Lvl \d+/) || ["?"])[0] : "never reached the fight");
      if (!menu) continue;
      await page.waitForTimeout(600);
      await page.keyboard.press("1");
      const fought = await until(/-- A fight! --[\s\S]*choose\./, "1");
      console.log(fought ? "fighting" : "no fight");
      if (!fought && process.env.ARENA_SHOW) console.log(await screen());
      await page.close();
    }
  } finally {
    await browser.close();
    server.close();
  }
}

main().catch((e) => { console.log("error: " + e.message); process.exit(1); });

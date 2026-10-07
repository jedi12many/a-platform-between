// Drives the Waystation website (build/waystation/, `make waystation`) in headless Chromium,
// the way a player would: clicking and typing, and reading back what the page shows.
// tests/waystation/check_site.py checks the results against the Python references.
//
//   node site.cjs create NAME RACE CLASS S1,S2,S3,S4,S5,S6 TAG   the Passport it issues
//   node site.cjs roll                                           rolled sets, and one made
//   node site.cjs spend PASSPORT stat:N|skill:N ...              the Passport afterwards
//   node site.cjs stamp PASSPORT STAMP [rewind]                  what landing it says
//   node site.cjs read PASSPORT                                  what the page says
//   node site.cjs sheet PASSPORT                                 the tabletop sheet's text
//
// RACE, CLASS and TAG are names as the page shows them ("Glassfolk").
"use strict";

const fs = require("fs");
const http = require("http");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.join(__dirname, "..", "..", "build", "waystation");
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".wasm": "application/wasm",
                ".css": "text/css", ".json": "application/json" };

function serve() {
  const server = http.createServer((req, res) => {
    const name = path.normalize(decodeURIComponent(req.url.split("?")[0]));
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

async function session(work) {
  const server = await serve();
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const problems = [];
  page.on("pageerror", (e) => problems.push(String(e)));
  try {
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    await page.waitForSelector("body[data-ready='1']", { timeout: 60000 });
    const out = await work(page);
    if (problems.length) throw new Error(problems.join("\n"));
    return out;
  } finally {
    await browser.close();
    server.close();
  }
}

async function pick(page, select, label) {
  const value = await page.$eval(select, (s, l) => {
    const o = Array.from(s.options).find((o) => o.textContent.split(" (")[0] === l);
    return o ? o.value : null;
  }, label);
  if (value === null) throw new Error(`no ${label} in ${select}`);
  await page.selectOption(select, value);
}

async function read(page, text) {
  await page.click("text=Your Passport");
  await page.fill("#p-text", text);
  await page.click("#p-load");
}

const commands = {
  async create(name, race, cls, stats, tag) {
    return session(async (page) => {
      await page.fill("#c-name", name);
      await pick(page, "#c-race", race);
      await pick(page, "#c-class", cls);
      await pick(page, "#c-tag", tag);
      const values = stats.split(",");
      for (let i = 0; i < 6; ++i) await page.fill(`#c-stat-${i}`, values[i]);
      const error = await page.textContent("#c-error");
      if (error) return "refused: " + error;
      await page.click("text=Issue the Passport");
      return (await page.textContent("#p-out")).replace(/\n/g, "");
    });
  },

  async roll() {
    return session(async (page) => {
      await page.check("input[value=roll]");
      const sets = [];
      for (let i = 0; i < 5; ++i) {
        const button = page.locator("#c-roll-button");
        if (await button.isDisabled()) break;
        await button.click();
        sets.push((await page.textContent("#c-rolled")).replace("Rolled: ", ""));
      }
      await page.fill("#c-name", "Dice");
      await page.click("text=Issue the Passport");
      return JSON.stringify({ sets, passport: (await page.textContent("#p-out")).replace(/\n/g, "") });
    });
  },

  async spend(text, ...clicks) {
    return session(async (page) => {
      await read(page, text);
      for (const c of clicks) {
        const [kind, n] = c.split(":");
        const button = page.locator(`#p-${kind === "stat" ? "stats" : "skills"} tr`).nth(Number(n) + 1)
          .locator("button");
        // Out of points, the page won't let you: the button is disabled.
        if (!(await button.isDisabled())) await button.click();
      }
      return (await page.textContent("#p-out")).replace(/\n/g, "");
    });
  },

  async stamp(text, stamp, rewind) {
    return session(async (page) => {
      await read(page, text);
      await page.click("text=Travel Stamp");
      await page.fill("#t-text", stamp);
      if (rewind === "rewind") await page.check("#t-rewind");
      await page.click("#t-apply");
      const error = await page.textContent("#t-error");
      if (error) return JSON.stringify({ error });
      return JSON.stringify({
        said: await page.$$eval("#t-result p", (ps) => ps.map((p) => p.textContent)),
        passport: (await page.textContent("#t-out")).replace(/\n/g, ""),
      });
    });
  },

  async read(text) {
    return session(async (page) => {
      await read(page, text);
      const error = await page.textContent("#p-error");
      return error || (await page.textContent("#p-summary"));
    });
  },

  async sheet(text) {
    return session(async (page) => {
      await read(page, text);
      await page.click("text=Tabletop sheet");
      return page.innerText("#s-sheet");
    });
  },
};

const [cmd, ...args] = process.argv.slice(2);
if (!commands[cmd]) {
  console.error("usage: see the top of tests/waystation/site.cjs");
  process.exit(2);
}
commands[cmd](...args).then((out) => console.log(out)).catch((e) => {
  console.error("FAIL: " + e.message);
  process.exit(1);
});

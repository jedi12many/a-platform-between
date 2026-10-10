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
//   node site.cjs keep PASSPORT STAMP NOTE    saved to Your travelers, the page loaded again,
//                                             the stamp landed by choosing them: what's kept
//   node site.cjs shell PASSPORT              the site (build/site/) signed in, with a stand-in
//                                             for claude.ai's store: the traveler saved in the
//                                             Waystation's frame, then boarded from the train's
//
// RACE, CLASS and TAG are names as the page shows them ("Glassfolk").
"use strict";

const fs = require("fs");
const http = require("http");
const path = require("path");
const { chromium } = require("playwright");

let ROOT = path.join(__dirname, "..", "..", "build", "waystation");
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

async function session(work, setup) {
  const server = await serve();
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const problems = [];
  page.on("pageerror", (e) => problems.push(String(e)));
  try {
    if (setup) await page.addInitScript(setup);
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    if (!setup) await page.waitForSelector("body[data-ready='1']", { timeout: 60000 });
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

  async keep(text, stamp, note) {
    return session(async (page) => {
      await read(page, text);
      await page.fill("#p-note", note);
      await page.click("#p-save");
      await page.waitForFunction(() => /^Saved/.test(document.getElementById("p-saved").textContent));
      await page.reload();
      await page.waitForSelector("body[data-ready='1']", { timeout: 60000 });
      await page.click("text=Travel Stamp");
      const label = await page.$eval("#t-pick", (s) => s.options[1] && s.options[1].textContent);
      await page.selectOption("#t-pick", { index: 1 });
      await page.fill("#t-text", stamp);
      await page.click("#t-apply");
      await page.waitForSelector("#t-kept", { timeout: 10000 });
      return JSON.stringify({ label, kept: JSON.parse(await page.evaluate(() => localStorage.getItem("apb-travelers"))) });
    });
  },

  // The site, signed in: claude.ai's user and db, stood in for by an in-memory store in the
  // top page (not the frames: they must ask the page for their travelers).
  async shell(text, picks) {
    ROOT = path.join(__dirname, "..", "..", "build", "site");
    return session(async (page) => {
      if (process.env.STEP) console.error("1 who"); await page.waitForFunction(() => /on your account/.test(document.getElementById("who").textContent));
      await page.click("text=Go to the Waystation");
      const way = page.frameLocator("#frame");
      await way.locator("body[data-ready='1']").waitFor({ timeout: 60000 });
      await way.locator("text=Your Passport").first().click();
      await way.locator("#p-text").fill(text);
      await way.locator("#p-load").click();
      await way.locator("#p-note").fill("Off to Dock 3");
      await way.locator("#p-save").click();
      await way.locator("#p-saved", { hasText: "on your account (Tess)" }).waitFor({ timeout: 10000 });
      await page.click("#home");
      await page.waitForSelector("#list li");
      const shown = await page.$$eval("#list li", (ls) => ls.map((l) =>
        l.innerText + "\n" + l.querySelector("input").value));
      await page.click("text=Board a train");
      const play = page.frameLocator("#frame");
      await play.locator("button[data-departure='the-fare']").click({ timeout: 60000 });
      await play.locator("#board-as").waitFor({ state: "visible", timeout: 10000 });
      const choices = await play.locator("#board-who option").allTextContents();
      const frame = page.frames().find((f) => f.url().includes("play/"));
      const onScreen = (words) => frame.waitForFunction((w) => {
        for (let r = 0; r < 25; ++r) if (Module.UTF8ToString(Module._web_screen_row(r)).includes(w)) return true;
        return false;
      }, words, { timeout: 20000 });
      // Board (1), and when the desk asks, have the traveler's Passport typed from the list.
      await onScreen("1. Board");
      await play.locator("canvas").press("1");
      await onScreen("Your Boarding Pass");
      await play.locator("#board-type").click();
      // Typed and read: the desk answers a Passport (the story log is short, and the
      // typed lines have scrolled on by now).
      const typed = await onScreen("That's a Passport, not a").then(() => true, () => false);
      // Then the way it's meant to be: back on the platform, The Fare (the first mission)
      // and Board on her card. The page issues her pass; the trip (its answers scripted,
      // the start menu's Board first) ends in a stamp that lands on her by itself.
      const before = JSON.stringify(await page.evaluate(() => window.__docs));
      await page.click("#home");
      await page.evaluate((c) => { window.APB_TEST_CHOICES = c; }, picks);
      const said = [];
      page.on("console", (m) => said.push(m.text()));      // the scripted trip's transcript
      await page.click("#list li .board button");
      const issued = await page.waitForFunction(() => Object.values(window.__docs)
        .some((d) => d.tickets && Object.keys(d.tickets).length), null, { timeout: 30000 })
        .then(() => true, () => false);
      await page.waitForFunction(() => Object.values(window.__docs).some((d) => d.landed),
                                 null, { timeout: 120000 }).catch(() => null);
      const bar = await page.textContent("#place-name");
      const told = said.join("\n");
      const desk = told.includes("Static.") && !told.includes("Boarding Pass, please")
        ? "aboard" : "the desk asked, or no story: " + told.slice(0, 300);
      return JSON.stringify({ shown, choices, typed, before: JSON.parse(before), issued, desk, bar, told,
                              docs: await page.evaluate(() => window.__docs) });
    }, () => {
      if (window.top !== window) return;
      const docs = {};
      const watching = [];
      const snap = (where) => ({ docs: Object.keys(docs).filter((k) => k.startsWith(where + "/"))
        .map((k) => ({ id: k.split("/").pop(), data: () => docs[k] })) });
      const tell = () => watching.forEach(([where, next]) => next(snap(where)));
      const db = {
        collection: (where) => ({
          doc: (id) => ({
            set: (d) => { docs[where + "/" + id] = JSON.parse(JSON.stringify(d)); setTimeout(tell); return Promise.resolve(); },
            delete: () => { delete docs[where + "/" + id]; setTimeout(tell); return Promise.resolve(); },
          }),
          onSnapshot: (next) => { watching.push([where, next]); setTimeout(() => next(snap(where))); return () => {}; },
        }),
      };
      const user = { me: () => Promise.resolve({ id: "u_test", name: "Tess", email: null }) };
      window.__docs = docs;
      window.claude = { use: (name) => new Promise((ok) => setTimeout(() => ok(name === "db" ? db : name === "user" ? user : null))) };
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

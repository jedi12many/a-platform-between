// Drives the native arena (tools/arena/web/, served by the studio) in headless Chromium the
// way a player would: keys and the buttons on screen. tests/arena/check_native.py checks
// what it prints against the rules.
//
//   node native.cjs URL start CODE        the scenario's intro, then its fight to the first
//                                         turn: the fighters, and the buttons at each step
//   node native.cjs URL fight CODE SEED   the fight on Auto (fast), with those dice, to the end
//   node native.cjs URL pack CODE N       the pack's item N taken up, then the armor put away
//   node native.cjs URL dash CODE SEED N  the first turn: a Dash, N squares east of the start
//   node native.cjs URL shove CODE SEED KEYS   the first turn: KEYS (arrows: R L U D) to
//                                         move, then a Shove of the first foe in reach
//   node native.cjs URL shot CODE PATH    a screenshot of the first turn
//
// Prints one line of JSON, and anything the page threw.
"use strict";

const { chromium } = require("playwright");

async function main() {
  const [url, what, code, arg] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 860 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  const state = () => page.evaluate(() => {
    const s = window.arena.state();
    return { mode: s.mode, st: s.fight && s.fight.st, round: s.fight && s.fight.round,
             pack: s.fight && s.fight.pack, buttons: window.arena.buttons(),
             log: Array.from(document.querySelectorAll("#log li")).map((li) => li.textContent) };
  });
  const until = (m, ms) => page.waitForFunction((m) => window.arena && window.arena.state().mode === m,
                                                m, { timeout: ms || 20000 });
  const seeded = ["fight", "dash", "shove"].includes(what);
  const hash = "#scenario=" + code + (seeded ? "&seed=" + arg : "");
  await page.goto(url + hash);
  await until("intro");
  const out = { intro: await state() };
  await page.keyboard.press("Enter");
  await until("turn");
  out.turn = await state();
  if (what === "fight") {
    await page.keyboard.press("z");
    await page.keyboard.press("t");
    await until("end", 120000);
    out.end = await state();
    out.ending = await page.textContent("#end-title");
  } else if (what === "pack") {
    await page.keyboard.press("p");
    await until("pack");
    out.open = await state();
    await page.keyboard.press(arg);
    out.taken = await state();
    await page.click("#pack-on li:nth-child(2) button");
    out.unworn = await state();
    await page.keyboard.press("Escape");
    await until("turn");
    out.closed = await state();
  } else if (what === "dash") {
    await page.keyboard.press("d");
    await until("dash");
    for (let i = 0; i < Number(process.argv[6]); ++i) await page.keyboard.press("ArrowRight");
    out.planned = await page.evaluate(() => window.arena.state().fight.dash);
    await page.keyboard.press("Enter");
    await page.waitForFunction(() => ["turn", "end"].includes(window.arena.state().mode), null, { timeout: 30000 });
    out.after = await state();
  } else if (what === "shove") {
    const keys = { R: "ArrowRight", L: "ArrowLeft", U: "ArrowUp", D: "ArrowDown" };
    for (const k of process.argv[6]) await page.keyboard.press(keys[k]);
    out.plan = await page.evaluate(() => window.arena.state().fight.plan);
    out.shoves = await page.evaluate(() => window.arena.state().fight.shoves);
    await page.keyboard.press("s");
    if (out.shoves.length > 1) {
      await until("aim");
      await page.keyboard.press("Enter");
    }
    await page.waitForFunction(() => ["turn", "end"].includes(window.arena.state().mode), null, { timeout: 30000 });
    out.after = await state();
  } else if (what === "shot") {
    await page.waitForTimeout(400);
    await page.screenshot({ path: arg });
  }
  out.errors = errors;
  console.log(JSON.stringify(out));
  await browser.close();
}

main().catch((e) => { console.log(JSON.stringify({ failed: e.message })); process.exit(1); });

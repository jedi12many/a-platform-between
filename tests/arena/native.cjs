// Drives the native arena (tools/arena/web/, served by the studio) in headless Chromium the
// way a player would: keys and the buttons on screen. tests/arena/check_native.py checks
// what it prints against the rules.
//
//   node native.cjs URL start CODE        the scenario's intro, then its fight to the first
//                                         turn: the fighters, and the buttons at each step
//   node native.cjs URL fight CODE SEED   the fight on Auto (fast), with those dice, to the end
//   node native.cjs URL pack CODE N       the pack's item N taken up, then the armor put away
//   node native.cjs URL dash CODE SEED N  the first turn: a Dash, N squares east of the start
//   node native.cjs URL power CODE SEED KEY   the first turn: the power on KEY (1-4), on the
//                                         first target or square the page offers
//   node native.cjs URL blink CODE SEED   the first turn: Blink (key 1) as the move, to the
//                                         square the page offers, then an attack from there
//   node native.cjs URL first CODE SEED   the first turn: an attack (A) from where the
//                                         traveler stands, then a step, then Enter
//   node native.cjs URL rules CODE        the first turn: each power button hovered, then
//                                         the first power on the traveler's card: the
//                                         rule card's text each time
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
             listed: Array.from(document.querySelectorAll("#scenario-list .code")).map((c) => c.textContent),
             log: Array.from(document.querySelectorAll("#log li")).map((li) => li.textContent) };
  });
  const until = (m, ms) => page.waitForFunction((m) => window.arena && window.arena.state().mode === m,
                                                m, { timeout: ms || 20000 });
  const seeded = ["fight", "dash", "shove", "power", "blink", "first"].includes(what);
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
  } else if (what === "power") {
    for (let i = 0; i < 4; ++i) {           // to the turn of a traveler with powers
      const has = await page.evaluate(() => {
        const f = window.arena.state().fight;
        return f.st.fighters[f.me].powers.length > 0;
      });
      if (has) break;
      await page.keyboard.press("Enter");
      await page.waitForFunction(() => window.arena.state().mode === "busy" || window.arena.state().mode === "end", null, { timeout: 5000 }).catch(() => {});
      await until("turn");
    }
    out.who = await page.evaluate(() => window.arena.state().fight.me);
    await page.keyboard.press(process.argv[6]);
    out.chose = await page.evaluate(() => window.arena.state().mode);
    if (["cast", "aim"].includes(out.chose)) await page.keyboard.press("Enter");
    await page.waitForFunction(() => ["turn", "end"].includes(window.arena.state().mode), null, { timeout: 30000 });
    out.after = await state();
  } else if (what === "blink") {
    await page.keyboard.press("1");
    out.chose = await page.evaluate(() => window.arena.state().mode);
    await page.keyboard.press("Enter");
    await until("turn");
    out.blinked = await state();
    out.plan = await page.evaluate(() => window.arena.state().fight.plan);
    out.blink = await page.evaluate(() => window.arena.state().fight.blink);
    out.targets = await page.evaluate(() => window.arena.state().fight.targets);
    await page.keyboard.press("a");
    if (out.targets.length > 1) {
      await until("aim");
      await page.keyboard.press("Enter");
    }
    await page.waitForFunction(() => ["turn", "end"].includes(window.arena.state().mode), null, { timeout: 30000 });
    out.after = await state();
  } else if (what === "first") {
    out.me = await page.evaluate(() => window.arena.state().fight.me);
    out.targets = await page.evaluate(() => window.arena.state().fight.targets);
    await page.keyboard.press("a");
    if (out.targets.length > 1) {
      await until("aim");
      await page.keyboard.press("Enter");
    }
    await page.waitForFunction(() => ["turn", "end"].includes(window.arena.state().mode), null, { timeout: 30000 });
    out.acted = await state();
    out.flag = await page.evaluate(() => window.arena.state().fight.acted);
    for (const k of ["ArrowLeft", "ArrowUp", "ArrowDown", "ArrowRight"]) {
      await page.keyboard.press(k);
      const p = await page.evaluate(() => window.arena.state().fight.plan);
      const f = await page.evaluate(() => { const g = window.arena.state().fight; return g.st.fighters[g.me]; });
      if (p.x !== f.x || p.y !== f.y) break;
    }
    out.plan = await page.evaluate(() => window.arena.state().fight.plan);
    await page.keyboard.press("Enter");
    await page.waitForFunction(() => ["busy", "end"].includes(window.arena.state().mode) ||
                               window.arena.state().fight.me !== 0, null, { timeout: 30000 }).catch(() => {});
    await page.waitForFunction(() => ["turn", "end"].includes(window.arena.state().mode), null, { timeout: 30000 });
    out.after = await state();
  } else if (what === "rules") {
    out.powers = await page.evaluate(() => { const f = window.arena.state().fight; return f.st.fighters[f.me].powers; });
    out.cards = [];
    const ruleText = () => page.evaluate(() => {
      const r = document.getElementById("rule");
      return r && !r.hidden ? r.innerText : null;
    });
    for (let k = 1; k <= out.powers.length; ++k) {
      await page.hover(`#actions button[data-key="${k}"]`);
      out.cards.push(await ruleText());
    }
    await page.mouse.move(2, 2);
    out.gone = await ruleText();
    await page.hover("#cards .card .gear.powers .pw");
    out.chip = await ruleText();
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

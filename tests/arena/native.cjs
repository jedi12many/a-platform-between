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
//   node native.cjs URL explore YARD:CLASS   explore (rooms.js): the start room, a walk
//                                         through its first door, and that room's fight
//                                         on Auto (fast) if it has one, back to walking
//   node native.cjs URL shove CODE SEED KEYS   the first turn: KEYS (arrows: R L U D) to
//                                         move, then a Shove of the first foe in reach
//   node native.cjs URL shot CODE PATH    a screenshot of the first turn
//   node native.cjs URL talk -            talk (docs/rooms.md, Talk): yard 14, Vell beside
//                                         the start; yard 2, a parley through the first door
//   node native.cjs URL looks YARD [DIR]  explore in each look (and by floor): the start
//                                         room's tiles as the board draws them (twice);
//                                         DIR: a screenshot of each, LOOK.png
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
  if (what === "talk") {
    const out = { errors };
    const T = () => page.evaluate(() => Object.assign(window.arena.talk(), { mode: window.arena.state().mode,
      buttons: window.arena.buttons(), cleared: window.arena.explore().cleared,
      log: Array.from(document.querySelectorAll("#log li")).map((li) => li.textContent) }));
    const parked = () => page.waitForFunction(() => window.arena && window.arena.talk().waiting && window.arena.state().mode === "explore",
                                              null, { timeout: 20000 });
    const choices = () => page.waitForFunction(() => window.arena.talk().choices.length > 0, null, { timeout: 20000 });
    const say = async (label) => {
      const t = await T();
      const k = t.choices.indexOf(label);
      if (k < 0) throw new Error("no choice '" + label + "' in " + JSON.stringify(t.choices));
      await page.keyboard.press(String(k + 1));
    };
    /* Vell, next to where you arrive: click her, ask, and leave. */
    await page.goto(url + "#explore=14:WARDEN");
    await parked();
    out.before = await T();
    await page.evaluate(() => window.arena.walkTo(8, 3));
    await choices();
    out.vell = await T();
    await say("What's on this floor?");
    await page.waitForFunction(() => window.arena.talk().lines.some((l) => l.indexOf("Rats on the first") >= 0), null, { timeout: 20000 });
    await choices();
    out.rumour = await T();
    await say("Move on");
    await parked();
    out.after = await T();
    /* A parley: through the start room's door, ash rats who talk first; shout. */
    await page.goto(url + "#explore=2:WARDEN");
    await page.reload();
    await parked();
    const door = await page.evaluate(() => { const x = window.arena.explore(), r = x.f.rooms[x.room];
                                               return r.doors[Object.keys(r.doors)[0]]; });
    await page.evaluate((d) => window.arena.walkTo(d[0], d[1]), door);
    await page.waitForFunction(() => window.arena.state().mode === "talk", null, { timeout: 20000 });
    await choices();
    out.parley = await T();
    await say("Shout them down");
    await page.waitForFunction(() => window.arena.talk().choices.join() === "Go on", null, { timeout: 20000 });
    out.shout = await T();
    await page.keyboard.press("Enter");
    await page.waitForFunction(() => window.arena.state().mode !== "talk", null, { timeout: 20000 });
    await page.waitForTimeout(300);
    out.then = await T();
    console.log(JSON.stringify(out));
    await browser.close();
    return;
  }
  if (what === "looks") {
    const out = { errors, looks: {} };
    for (const look of ["", "forest", "mountain", "town", "dungeon"]) {
      const p = await browser.newPage({ viewport: { width: 1400, height: 860 } });
      p.on("pageerror", (e) => errors.push(e.message));
      await p.goto(url + "#explore=" + code + ":WARDEN" + (look ? ":look=" + look : ""));
      await p.waitForFunction(() => window.arena && window.arena.state().mode === "explore", null, { timeout: 20000 });
      out.looks[look || "by floor"] = await p.evaluate(() => {
        const f = window.arena.state().fight, x = window.arena.explore(), r = x.f.rooms[x.room];
        const tiles = () => f.st.map.map((row, y) => row.split("").map((t, x) => f.dress(x, y, Number(t))));
        return { look: f.look, room: r, tiles: tiles(), again: tiles() };
      });
      if (arg) await p.screenshot({ path: arg + "/" + (look || "by-floor") + ".png" });
      await p.close();
    }
    console.log(JSON.stringify(out));
    await browser.close();
    return;
  }
  if (what === "explore") {
    const out = { errors };
    const X = () => page.evaluate(() => {
      const x = window.arena.explore(), s = window.arena.state();
      return { mode: s.mode, room: x.room, x: x.x, y: x.y, cleared: x.cleared, lost: x.lost, pack: x.pack,
               map: s.fight && s.fight.st.map, fighters: s.fight && s.fight.st.fighters.map((f) => [f.side, f.x, f.y]),
               doors: x.f.rooms[x.room].doors, buttons: window.arena.buttons(), px: x.px, py: x.py,
               grid: window.arena.grid(), scroll: x.scroll, cam: s.fight && s.fight.cam, party: x.party,
               shown: s.fight && s.fight.shown.slice(0, x.party.length).map((f) => [f.x, f.y, f.alpha === undefined ? 1 : f.alpha]),
               side: document.getElementById("cards").innerText };
    });
    await page.goto(url + "#explore=" + code);
    await until("explore");
    out.start = await X();
    /* Holding a key walks smoothly: a third of a second, and you're between squares (left;
     * scrolling, right, so the view follows away from the area's left edge). */
    const key = out.start.scroll ? "ArrowRight" : "ArrowLeft";
    await page.keyboard.down(key);
    await page.waitForTimeout(330);
    out.held = await X();
    await page.keyboard.up(key);
    await page.waitForTimeout(600);
    out.rest = await X();
    /* Then through the start room's first door (scrolling: on into the next room's doorway). */
    const side = Object.keys(out.start.doors)[0], door = out.start.doors[side];
    const ox = out.start.scroll ? (out.start.room % 3) * 16 : 0, oy = out.start.scroll ? Math.floor(out.start.room / 3) * 8 : 0;
    const step = { N: [0, -1], E: [1, 0], S: [0, 1], W: [-1, 0] }[side];
    const go = out.start.scroll ? [door[0] + ox + step[0], door[1] + oy + step[1]] : door;
    await page.evaluate(([x, y]) => window.arena.walkTo(x, y), go);
    await page.waitForTimeout(650);
    out.mid = await X();                       /* walking: the party strung out behind the leader */
    await page.waitForFunction((r) => window.arena.explore().room !== r, out.start.room, { timeout: 20000 });
    await page.waitForTimeout(400);
    /* Scrolling, the view settles on the room before its fight. */
    await page.waitForFunction(() => window.arena.state().mode !== "explore" || !window.arena.explore().settle,
                               null, { timeout: 20000 });
    out.next = await X();
    if (out.next.mode === "talk") {
      /* Foes who talk first (docs/rooms.md, People): this test is for the fight. */
      await page.waitForFunction(() => window.arena.talk().choices.indexOf("Fight") >= 0, null, { timeout: 20000 });
      out.parley = await page.evaluate(() => window.arena.talk().who);
      await page.evaluate(() => window.arena.say(window.arena.talk().choices.indexOf("Fight")));
      await page.waitForFunction(() => window.arena.state().mode !== "talk", null, { timeout: 20000 });
      out.next = await X();
    }
    if (out.next.mode !== "explore") {
      await until("turn");
      out.fight = await X();
      await page.waitForTimeout(700);
      out.gridUp = await page.evaluate(() => window.arena.grid());
      await page.keyboard.press("z");
      await page.keyboard.press("t");
      await page.waitForFunction(() => ["explore", "lost"].includes(window.arena.state().mode), null, { timeout: 120000 });
      out.after = await X();
    }
    console.log(JSON.stringify(out));
    await browser.close();
    return;
  }
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

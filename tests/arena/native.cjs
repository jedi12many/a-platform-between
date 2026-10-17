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
//   node native.cjs URL explore YARD:CLASSES   explore (rooms.js): an open floor's start,
//                                         a walk right (a key held), the party following
//   node native.cjs URL shove CODE SEED KEYS   the first turn: KEYS (arrows: R L U D) to
//                                         move, then a Shove of the first foe in reach
//   node native.cjs URL shot CODE PATH    a screenshot of the first turn
//   node native.cjs URL talk -            talk (docs/rooms.md, Talk): yard 326, walked up to
//                                         Vell; then its band 2 of ash rats, who talk first
//   node native.cjs URL scale -          the board's scale at a few window sizes
//   node native.cjs URL c64 -            the C64's scale (C): tiles16 and the cartridge's figures
//   node native.cjs URL open YARD:CLASSES[:look=LOOK] walk|sneak|ambush   an open floor
//                                         (docs/open-floors.md): to the stairs until a band
//                                         sees you (or you fall on one), every step's checks,
//                                         then the fight on its window, on Auto, to the end
//   node native.cjs URL looks YARD [DIR]  explore in each look (and by floor): the floor's
//                                         tiles as the board draws them (twice);
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
      buttons: window.arena.buttons(), cleared: window.arena.explore().bands.map((b) => b.cleared),
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
    /* Vell, a few squares from where you arrive: click her (you walk up), ask, and leave. */
    await page.goto(url + "#explore=326:WARDEN");
    await parked();
    out.before = await T();
    const vell = await page.evaluate(() => window.arena.explore().o.people.filter((p) => p.who === "trader")[0]);
    await page.evaluate((v) => window.arena.walkTo(v.x, v.y), vell);
    await choices();
    out.vell = await T();
    await say("What's on this floor?");
    await page.waitForFunction(() => window.arena.talk().lines.some((l) => l.indexOf("Rats on the first") >= 0), null, { timeout: 20000 });
    await choices();
    out.rumour = await T();
    await say("Move on");
    await parked();
    out.after = await T();
    out.near = await page.evaluate(() => { const x = window.arena.explore(); return [x.x, x.y]; });
    out.vellAt = [vell.x, vell.y];
    /* A parley: band 2, ash rats who talk first, as when they see you; shout. */
    await page.evaluate(() => openMeet(window.arena.explore().bands[1], ""));
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
    const all = Object.keys((await (await fetch(url + "art.json")).json()).looks);   /* the four, and alternatives */
    for (const look of [""].concat(all)) {
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
  if (what === "zoom") {
    /* Z zooms out to the whole floor and back: the view's size and where it is, each press. */
    const out = { errors, views: [] };
    const V = () => page.evaluate(() => {
      const x = window.arena.explore(), f = window.arena.state().fight;
      return { view: f.view, cam: f.cam, px: x.px, py: x.py, mode: window.arena.state().mode,
               button: window.arena.buttons().filter((b) => b && b.indexOf("Zoom") >= 0)[0] || null };
    });
    await page.goto(url + "#explore=" + code);
    await until("explore");
    out.views.push(await V());
    for (let k = 0; k < 3; ++k) {
      await page.keyboard.press("z");
      await page.waitForTimeout(150);
      out.views.push(await V());
      if (arg && k === 0) await page.screenshot({ path: arg });     /* (the whole floor) */
    }
    out.floor = await page.evaluate(() => [window.arena.explore().o.w, window.arena.explore().o.h]);
    console.log(JSON.stringify(out));
    await browser.close();
    return;
  }
  if (what === "minimap") {
    /* The minimap's fog at the start and after a walk, and the view's rectangle. */
    const out = { errors };
    const M = () => page.evaluate(() => {
      const x = window.arena.explore(), f = window.arena.state().fight, c = document.getElementById("minimap");
      const at = (px, py) => Array.from(c.getContext("2d").getImageData(px, py, 1, 1).data.slice(0, 3));
      return { size: c && [c.width, c.height], fog: x.fog ? Array.from(x.fog) : null, x: x.x, y: x.y,
               w: x.o.w, h: x.o.h, sight: openSight(),
               cam: f.cam, view: f.view, corner: c && at(Math.round(f.cam.x * 4), Math.round(f.cam.y * 4)) };
    });
    await page.goto(url + "#explore=" + code);
    await until("explore");
    await page.waitForTimeout(200);
    out.start = await M();
    await page.keyboard.down("ArrowRight");
    await page.waitForTimeout(900);
    await page.keyboard.up("ArrowRight");
    await page.waitForTimeout(500);
    out.walked = await M();
    if (arg) await page.screenshot({ path: arg });
    console.log(JSON.stringify(out));
    await browser.close();
    return;
  }
  if (what === "c64") {
    /* The C64's scale: exploring starts at it (nothing chosen yet); the tiles as drawn (a dot
     * of each row of every tile), a figure's a dots, the button; then C turns it off, kept
     * after a reload, and C turns it on again. */
    const out = { errors };
    await page.goto(url + "#explore=48213:WARDEN:look=forest2");
    await until("explore");
    const sample = () => page.evaluate(() => {
      const hex = (c, x, y) => { const d = c.getContext("2d").getImageData(x, y, 1, 1).data;
        return "#" + [d[0], d[1], d[2]].map((v) => v.toString(16).padStart(2, "0")).join(""); };
      const tiles = {};
      for (const name of ["open", "wall", "pit", "cover"]) {
        const c = tileSprite(name, true, "forest2"), rows = [];
        for (let y = 0; y < 16; ++y) { const r = []; for (let x = 0; x < 8; ++x) r.push(hex(c, x * 4 + 1, y * 2)); rows.push(r); }
        tiles[name] = rows;
      }
      const f = figureSprite("HUMAN2"), fig = [];
      for (let y = 0; y < 21; ++y) { const r = []; for (let x = 0; x < 12; ++x) r.push(hex(f, 1 + x * 2, 1 + y)); fig.push(r); }
      return { c64: c64, tiles: tiles, figure: fig, buttons: window.arena.buttons() };
    });
    out.on = await sample();
    await page.keyboard.press("c");
    out.off = await page.evaluate(() => c64);
    await page.reload();
    await until("explore");
    out.reloaded = await page.evaluate(() => c64);
    await page.keyboard.press("c");
    out.again = await page.evaluate(() => c64);
    console.log(JSON.stringify(out));
    await browser.close();
    return;
  }
  if (what === "scale") {
    /* The board's scale (resize in arena.js) at a few window sizes. */
    const out = { errors, scales: [] };
    for (const [w, h] of [[1400, 860], [1640, 1000], [1237, 911], [2000, 1300]]) {
      const p = await browser.newPage({ viewport: { width: w, height: h } });
      p.on("pageerror", (e) => errors.push(e.message));
      await p.goto(url + "#explore=48213:WARDEN");
      await p.waitForFunction(() => window.arena && window.arena.state().mode === "explore", null, { timeout: 20000 });
      out.scales.push(await p.evaluate(() => {
        const r = document.getElementById("board").getBoundingClientRect(), f = window.arena.state().fight;
        const w = f.view[0] * 32, h = f.view[1] * 32;
        return { fit: Math.min((r.width - 32) / w, (r.height - 32) / h), scale: view.scale, ox: view.ox, oy: view.oy };
      }));
      await p.close();
    }
    console.log(JSON.stringify(out));
    await browser.close();
    return;
  }
  if (what === "open") {
    /* An open floor (docs/open-floors.md): CODE is YARD:CLASSES[:look=LOOK]; ARG says how
     * the party goes: walk, sneak (S first), or ambush (sneaking, and A on the first band
     * spotted near enough). To the stairs until a fight starts, every step's checks
     * (X.seeTrace); then the fight on its window on Auto (fast), back to walking. */
    const out = { errors };
    const [yard, party, look] = code.split(":");
    await page.goto(url + "#explore=" + yard + ":" + party + (look ? ":" + look : ""));
    await until("explore");
    if (arg !== "walk") await page.keyboard.press("s");
    out.start = await page.evaluate(() => {
      const x = window.arena.explore(), t = x.party.map((c) => window.arena.travelers()[c]);
      return { o: x.o, light: x.light, bands: x.bands.map((b) => ({ x: b.x, y: b.y, hiding: b.hiding, foes: b.foes,
               sense: Math.max(...b.foes.map((f) => window.arena.foes()[f.name].sense)),
               stealth: Math.max(...b.foes.map((f) => window.arena.foes()[f.name].stealth)) })),
               party: t.map((c) => ({ notice: c.notice, stealth: c.stealth })), sneak: !!x.sneak,
               side: document.getElementById("cards").innerText };
    });
    await page.evaluate(() => { const s = window.arena.explore().o.stairs; window.arena.walkTo(s[0], s[1]); });
    out.ambushed = false;
    for (let i = 0; i < 600; ++i) {
      const st = await page.evaluate(() => ({ mode: window.arena.state().mode, floor: window.arena.explore().floor,
                                               b: window.arena.buttons() }));
      if (st.mode !== "explore" || st.floor > 1) break;
      if (arg === "ambush" && st.b.some((t) => t && t.startsWith("Ambush"))) {
        out.ambushed = true;
        out.drawn = await page.evaluate(() => {                /* before: what's drawn of the bands */
          const x = window.arena.explore(), f = window.arena.state().fight;
          return { foes: f.st.fighters.filter((g) => g.side === 1).map((g) => [g.x, g.y]).sort(),
                   spotted: x.bands.filter((b) => b.spotted && !b.cleared).flatMap((b) => b.foes.map((g) => [g.x, g.y])).sort(),
                   unspotted: x.bands.filter((b) => !b.spotted).length };
        });
        await page.keyboard.press("a");
        break;
      }
      await page.waitForTimeout(100);
    }
    await page.waitForTimeout(300);
    const at = () => page.evaluate(() => {
      const x = window.arena.explore(), s = window.arena.state();
      return { mode: s.mode, floor: x.floor, trace: x.seeTrace, win: x.win, fightBand: x.fightBand ? x.fightBand.k : -1,
               party: x.party.length,
               spec: s.S && s.S.native && s.S.native.spec, map: s.fight && s.fight.st.map, x: x.x, y: x.y,
               fighters: s.fight && s.fight.st.fighters.map((f) => [f.side, f.x, f.y]), round: s.fight && s.fight.st.round,
               shown: (s.fight && s.fight.explore) ? s.fight.st.fighters.length - x.party.length : null,
               cleared: x.bands.map((b) => b.cleared), spotted: x.bands.map((b) => b.spotted),
               log: Array.from(document.querySelectorAll("#log li")).map((li) => li.textContent) };
    });
    out.met = await at();
    if (out.met.mode === "talk") {
      await page.waitForFunction(() => window.arena.talk().choices.indexOf("Fight") >= 0, null, { timeout: 20000 });
      await page.evaluate(() => window.arena.say(window.arena.talk().choices.indexOf("Fight")));
      await page.waitForFunction(() => window.arena.state().mode !== "talk", null, { timeout: 20000 });
      out.met = await at();
      out.talked = true;
    }
    if (out.met.mode !== "explore") {
      await page.keyboard.press("z");
      await page.keyboard.press("t");
      await page.waitForFunction(() => ["explore", "lost"].includes(window.arena.state().mode), null, { timeout: 120000 });
      await page.waitForTimeout(200);
      out.after = await at();
    }
    console.log(JSON.stringify(out));
    await browser.close();
    return;
  }
  if (what === "explore") {
    const out = { errors };
    const X = () => page.evaluate(() => {
      const x = window.arena.explore(), s = window.arena.state();
      return { mode: s.mode, x: x.x, y: x.y, px: x.px, py: x.py, map: s.fight && s.fight.st.map,
               start: x.o.start, w: x.o.w, h: x.o.h, buttons: window.arena.buttons(),
               grid: window.arena.grid(), cam: s.fight && s.fight.cam, view: s.fight && s.fight.view,
               party: x.party, c64: c64,
               shown: s.fight && s.fight.shown.slice(0, x.party.length).map((f) => [f.x, f.y, f.alpha === undefined ? 1 : f.alpha]),
               side: document.getElementById("cards").innerText };
    });
    await page.goto(url + "#explore=" + code);
    await until("explore");
    out.start = await X();
    /* Holding a key walks smoothly: a third of a second, and you're between squares; held
     * on, the party strings out behind the leader. */
    await page.keyboard.down("ArrowRight");
    await page.waitForTimeout(330);
    out.held = await X();
    await page.waitForTimeout(800);
    out.mid = await X();
    await page.keyboard.up("ArrowRight");
    await page.waitForTimeout(600);
    out.rest = await X();
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

/* The native arena (docs/arena.md, "The native arena"): a scenario's fight, played by hand
 * in a modern page. The rules are rules v1's battle engine, the rules lab's
 * (core/next/battle.c, docs/turn.md), as WebAssembly (rules.js, from
 * tools/arena/web/arena.c); the pictures are the game's art
 * (content/art/, as art.json), drawn crisp at any size; the scenarios are
 * tools/arena/scenarios.py's. No story, no codes: a fight, again, or another.
 */
"use strict";

var REPO = "https://github.com/jedi12many/a-platform-between";
var TYPES = ["kinetic", "energy", "fire", "cold", "mind"];
var TYPE_COLOUR = { kinetic: 1, energy: 3, fire: 8, cold: 14, mind: 4 };   /* C64 colours */
var SQ = 32;                                  /* a square, in the art's pixels */
var ACT = { attack: 0, guard: 1, wait: 2, flee: 3, done: 4, shove: 5, dash: 6, power: 7 };
var RESULTS = ["miss", "glancing", "hit", "critical"];

var ART, SCENARIOS, ITEMS, CONDS, POWERS, BUILD = "studio";
var rules = {};                               /* the WebAssembly calls */
var sprites = {};                             /* drawn art, by name */

var $ = function (id) { return document.getElementById(id); };

function el(tag, cls, text) {
  var n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined && text !== null) n.textContent = text;
  return n;
}

function call(name) {
  var r = JSON.parse(rules[name].apply(null, Array.prototype.slice.call(arguments, 1)));
  if (r.error) throw new Error(name + ": " + r.error);
  return r;
}

/* ------------------------------------------------------------------ the art */

function canvas(w, h) {
  var c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return c;
}

/* A row of multicolour dots, each two pixels wide, onto a canvas. */
function paint(ctx, rows, colourOf, wide) {
  var y, x, c;
  for (y = 0; y < rows.length; ++y) {
    for (x = 0; x < rows[y].length; ++x) {
      c = colourOf(rows[y][x]);
      if (c === null) continue;
      ctx.fillStyle = ART.palette[c];
      ctx.fillRect(x * wide, y, wide, 1);
    }
  }
}

function tileSprite(name) {
  var key = "tile:" + name, t = ART.tiles, e = t.entries[name], c;
  if (sprites[key]) return sprites[key];
  c = canvas(SQ, SQ);
  paint(c.getContext("2d"), e.rows, function (d) {
    return d === "k" ? t.background : d === "d" ? t.shared[0] : d === "g" ? t.shared[1]
      : ART.colours.indexOf(e.option);
  }, 2);
  return (sprites[key] = c);
}

/* A figure, outlined in black so it stands off any floor: 26 x 23. */
function figureSprite(name, grey) {
  var key = "fig:" + name + (grey ? ":grey" : ""), f = ART.figures, e, body, c, ctx, dx, dy;
  if (sprites[key]) return sprites[key];
  e = f.entries[name] || f.entries.STRANGER;
  body = canvas(24, 21);
  paint(body.getContext("2d"), e.rows, function (d) {
    if (d === ".") return null;
    if (grey) return d === "c" ? 12 : 11;
    return d === "a" ? f.shared[0] : d === "b" ? f.shared[1] : ART.colours.indexOf(e.option);
  }, 2);
  c = canvas(26, 23);
  ctx = c.getContext("2d");
  var shadow = canvas(24, 21), sctx = shadow.getContext("2d");
  sctx.drawImage(body, 0, 0);
  sctx.globalCompositeOperation = "source-in";
  sctx.fillStyle = "#0b0b0e";
  sctx.fillRect(0, 0, 24, 21);
  for (dy = 0; dy <= 2; ++dy) {
    for (dx = 0; dx <= 2; ++dx) if (dx !== 1 || dy !== 1) ctx.drawImage(shadow, dx, dy);
  }
  ctx.drawImage(body, 1, 1);
  return (sprites[key] = c);
}

function effectSprite(name, colour) {
  var key = "fx:" + name + ":" + colour, f = ART.effects, e = f.entries[name], c, hires;
  if (sprites[key]) return sprites[key];
  if (!e) return null;
  hires = e.option === "hires";
  c = canvas(24, 21);
  paint(c.getContext("2d"), e.rows, function (d) {
    if (d === ".") return null;
    if (hires) return colour;
    return d === "a" ? f.shared[0] : d === "b" ? f.shared[1] : colour;
  }, hires ? 1 : 2);
  return (sprites[key] = c);
}

/* A figure as a small picture for a card. */
function portrait(name) {
  var c = canvas(26, 23);
  c.getContext("2d").drawImage(figureSprite(name), 0, 0);
  return c;
}

/* ------------------------------------------------------------- a fight's state */

var S = null;            /* the scenario being fought */
var fight = null;        /* everything about the fight now */
var mode = "intro";      /* intro, busy, turn, aim, pack, end */
var picked = 0;          /* the intro's scenario */
var fast = false;
var auto = false;        /* the traveler plays on quick */
var hover = null;        /* the square under the mouse */

function itemOf(id) { return id ? ITEMS[String(id)] : null; }
function condOf(id) { return CONDS[String(id)] || { tag: "?", display: "?", what: "" }; }
function powerOf(id) { return POWERS[String(id)] || { display: "?", what: "", target: "foe", shape: "bolt" }; }

/* What a scenario's hazards do, in words. */
function hazardText(h) {
  if (!h) return "";
  var c = h[2] ? CONDS[Object.keys(CONDS).filter(function (k) { return CONDS[k].name === h[2]; })[0]] : null;
  return "Its hazards (^) are " + (h[1] || "plain") + ": " + h[0] + (h[1] ? " " + h[1] : "") +
    " damage to anyone who steps in or starts a turn there" + (c ? ", and " + c.display.toLowerCase() : "") + ".";
}

function weaponText(f) {
  var it = itemOf(f.item), kind = f.power ? "power" : f.ranged ? "ranged" : "melee";
  var dmg = f.weapon + (f.ranged ? 0 : f.stat_bonus);
  return (it ? it.display : f.side === 0 ? "Bare hands" : "Its attack") + ": " + dmg + " " +
    TYPES[f.type] + ", " + kind + (f.area ? ", area " + f.area : "");
}

function name(i) { return S.native.names[i]; }

var fixedSeed = 0;       /* #seed=N: the next fight's dice (for tests) */

function newFight() {
  var seed = fixedSeed || 1 + Math.floor(Math.random() * 65535);
  fixedSeed = 0;
  var r = call("ar_begin", seed, S.native.spec);
  var st = r;
  fight = {
    seed: seed, st: st, round: 0, whose: -1, me: -1, plan: null, reach: null, targets: [],
    shoves: [], aim: 0, aimKind: "attack", dash: null, dashReach: null, log: [], floaters: [], effects: [],
    puse: 0, ptargets: [], psquares: null, cast: null,
    pack: S.native.pack.slice(),
    shown: st.fighters.map(function (f) {
      return { x: f.x, y: f.y, health: f.health, state: f.state, alpha: 1, flash: 0, lunge: null,
               fall: 0 };
    }),
    dealt: 0, taken: 0, hits: 0, swings: 0, swaps: 0
  };
  plays(S.code, 1);
}

/* --------------------------------------------------------------- the screens */

function show(screen) {
  $("intro").hidden = screen !== "intro";
  $("fight").hidden = screen !== "fight";
}

function setMode(m) {
  mode = m;
  $("pack").hidden = m !== "pack";
  $("end").hidden = m !== "end";
  actions();
  if (fight) cards();
}

/* The intro: the list, and the chosen scenario's brief. */
function intro() {
  show("intro");
  fight = null;
  $("where").textContent = "";
  var list = $("scenario-list");
  list.textContent = "";
  shown().forEach(function (i, k, all) {
    var s = SCENARIOS[i], li = el("li"), b = el("button");
    if (k === 0 || !!SCENARIOS[all[k - 1]].play !== !!s.play) {
      list.append(el("li", "group", s.play ? "To play now" : "Opened by its link"));
    }
    b.type = "button";
    b.append(el("span", "code", s.code), el("span", "t", s.title),
             el("span", "who", s.traveler + " vs " + count(s.foes)));
    b.setAttribute("aria-current", String(i === picked));
    b.onclick = function () { picked = i; intro(); };
    b.ondblclick = function () { picked = i; start(); };
    li.append(b);
    list.append(li);
  });
  brief(SCENARIOS[picked]);
  setMode("intro");
}

function count(names) {
  var seen = {}, out = [];
  names.forEach(function (n) { seen[n] = (seen[n] || 0) + 1; });
  Object.keys(seen).forEach(function (n) {
    out.push(seen[n] > 1 ? seen[n] + " " + n.toLowerCase() + "s" : "a " + n.toLowerCase());
  });
  return out.join(", ");
}

function brief(s) {
  var b = $("brief"), head = el("header"), test = el("div", "test"), m = el("div", "matchup");
  var st = JSON.parse(rules.ar_begin(1, s.native.spec));   /* the fighters, as the rules make them */
  var mine = el("div", "side-list"), theirs = el("div", "side-list");
  b.textContent = "";
  head.append(el("span", "code", s.code), el("h2", null, s.title));
  var p1 = el("p"), p2 = el("p");
  p1.append(el("b", null, "What we want tested: "), document.createTextNode(s.issue));
  p2.append(el("b", null, "Watch for: "), document.createTextNode(s.watch));
  test.append(p1, p2);
  if (s.hazard) test.append(el("p", "hz", hazardText(s.hazard)));
  st.fighters.forEach(function (f, i) {
    (f.side === 0 ? mine : theirs).append(card(s, f, i, false));
  });
  var h1 = el("h3", null, "Your side"), h2 = el("h3", null, "Against");
  var l = el("div"), r = el("div");
  l.append(h1, mine);
  r.append(h2, theirs);
  m.append(l, el("div", "vs", "vs"), r);
  var a = s.lab, odds = el("div", "odds"), bar = el("div", "oddsbar");
  ["won", "lost", "fled"].forEach(function (k) {
    var i = el("i", k);
    i.style.width = a[k] + "%";
    i.title = k + " " + a[k] + "%";
    bar.append(i);
  });
  odds.append(el("h3", null, "What the computer says (rules v1)"), bar,
    el("p", "oddsnote", "Playing both sides a thousand times (it never shoves or dashes), the traveler wins " + a.won +
      "%, loses " + a.lost + "%" + (a.fled ? ", flees " + a.fled + "%" : "") + "; a fight lasts " +
      a.rounds + " rounds, and a winner keeps " + a.health_left + "% of their health." +
      (s.arena ? " By rules v0, as the game plays now: " + s.arena.won + "%." : "") +
      (plays(s.code, 0) ? " You've played it " + plays(s.code, 0) + " times here." : "")));
  var go = el("div", "start"), btn = el("button", "primary");
  btn.type = "button";
  btn.innerHTML = "<kbd>Enter</kbd>Start the fight";
  btn.onclick = start;
  go.append(btn);
  b.append(head, test, m, odds, go);
}

/* A fighter's card: picture, name, health, numbers, gear. */
function card(s, f, i, live) {
  var c = el("div", "card " + (f.side === 0 ? "traveler" : "foe"));
  var pic = portrait(s.native.figures[i]), nm = el("div", "name"), hp = el("div", "hp");
  var bar = el("i"), st = el("div", "stats"), gear = el("div", "gear");
  var health = live ? fight.shown[i].health : f.health;
  var frac = health / f.health_max;
  if (live && f.state !== 0) c.classList.add("down");
  if (live && fight.whose === i && (mode === "turn" || mode === "aim" || mode === "pack")) {
    c.classList.add("turn");
  }
  nm.append(el("span", null, s.native.names[i]),
            el("small", null, live && f.state === 1 ? (fight.shown[i].fell ? "fell" : "down")
                              : live && f.state === 2 ? "gone"
                              : health + " / " + f.health_max));
  bar.style.width = Math.max(0, 100 * frac) + "%";
  hp.append(bar);
  if (frac <= 0.25) hp.classList.add("low"); else if (frac <= 0.5) hp.classList.add("mid");
  [["Attack", f.attack, f.attack], ["Armor", f.armor, f.armor_now], ["Ward", f.ward, f.ward_now],
   ["Dodge", f.dodge, f.dodge_now], ["Soak", f.soak, f.soak_now], ["Speed", f.speed, f.speed_now],
   ["Resist", 2 * f.level, 2 * f.level]].forEach(function (p) {
    var sp = el("span", null, p[0] + " "), now = p[2] === undefined ? p[1] : p[2];
    var b = el("b", now > p[1] ? "up" : now < p[1] ? "down" : null, String(now));
    if (now !== p[1]) b.title = "Without its conditions: " + p[1];
    sp.append(b);
    st.append(sp);
  });
  var w = el("b", null, weaponText(f));
  gear.append(w);
  if (f.side === 0) {
    var arm = itemOf(f.armor_item);
    gear.append(document.createTextNode(" · " + (arm ? arm.display : "no armor")));
  } else if (f.weak >= 0) {
    gear.append(document.createTextNode(" · weak to " + TYPES[f.weak]));
  }
  if (live && f.guarding) gear.append(document.createTextNode(" · on guard"));
  c.append(pic, nm, hp, st, gear);
  if (f.powers && f.powers.length) {
    var pl = el("div", "gear powers");
    f.powers.forEach(function (p, k) {
      var pd = powerOf(p[0]), sp = el("span", "pw" + (p[2] === 0 ? " spent" : ""),
        (live && f.side === 0 ? (k + 1) + " " : "") + pd.display +
        (p[2] >= 0 ? " " + p[2] + "/" + (pd.uses || 0) : ""));
      sp.title = pd.display + " (tier " + p[3] + ", rolls " + p[4] + "): " + pd.what +
        (p[2] < 0 ? "; at will" : "; " + p[2] + " left this fight");
      pl.append(sp);
    });
    c.append(pl);
  }
  if (f.conds && f.conds.length && !(live && f.state !== 0)) {
    var chips = el("div", "chips");
    f.conds.forEach(function (cr) {
      var cd = condOf(cr[0]), chip = el("span", "chip" + (cd.trait ? " trait" : ""),
                                         cd.display + (cr[1] ? " " + cr[1] : ""));
      chip.title = cd.display + ": " + cd.what + (cr[1] ? " (" + cr[1] + " left)" : "");
      chips.append(chip);
    });
    c.append(chips);
  }
  return c;
}

function cards() {
  var box = $("cards");
  box.textContent = "";
  fight.st.fighters.forEach(function (f, i) { box.append(card(S, f, i, true)); });
  $("where").innerHTML = "";
  var b = el("b", null, S.code + " " + S.title);
  $("where").append(b, document.createTextNode("  ·  round " + Math.max(1, fight.round)));
}

/* ------------------------------------------------------------------ the log */

function log(text, cls) {
  var li = el("li", cls || null);
  if (typeof text === "string") li.textContent = text; else li.append.apply(li, text);
  $("log").append(li);
  $("log").scrollTop = $("log").scrollHeight;
}

function toast(text) {
  var t = $("toast");
  t.textContent = text;
  t.classList.add("on");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(function () { t.classList.remove("on"); }, 1800);
}

/* -------------------------------------------------------------- the fight's flow */

function start() {
  S = SCENARIOS[picked];
  newFight();
  show("fight");
  $("log").textContent = "";
  log("Fight " + S.code + ": " + S.title + ". Dice seed " + fight.seed + ".", "round");
  resize();
  cards();
  advance();
}

function wait(ms) {
  return new Promise(function (r) { setTimeout(r, fast ? ms / 5 : ms); });
}

/* Play foes until it's a traveler's turn, or the end. */
async function advance() {
  setMode("busy");
  var r = call("ar_next");
  await play(r.events);
  settle(r);
  if (r.result !== 0) return finish(r.result);
  if (r.whose >= 0) beginTurn(r.whose);
}

function settle(r) {
  fight.st = r;
  r.fighters.forEach(function (f, i) {
    var s = fight.shown[i];
    s.x = f.x; s.y = f.y; s.health = f.health; s.state = f.state;
    s.alpha = f.state === 2 || s.fell ? 0 : 1;
  });
  cards();
}

function me() { return fight.st.fighters[fight.me]; }

function beginTurn(who) {
  var f;
  fight.me = who;
  fight.whose = who;
  f = me();
  fight.plan = { x: f.x, y: f.y };
  fight.blink = 0;
  fight.reach = call("ar_reach", who).reach;
  aimFrom();
  setMode("turn");
  if (auto) setTimeout(quick, fast ? 60 : 300);
}

function aimFrom() {
  fight.targets = call("ar_targets", fight.me, fight.plan.x, fight.plan.y).targets;
  fight.shoves = call("ar_shoves", fight.me, fight.plan.x, fight.plan.y).targets;
  if (fight.aim >= fight.targets.length) fight.aim = 0;
}

/* The list being aimed at: attacks or shoves. */
function aimList() {
  return fight.aimKind === "shove" ? fight.shoves : fight.aimKind === "power" ? fight.ptargets : fight.targets;
}

/* A power (keys 1-4): straight away if it has one target (or none to choose), else aim
 * at a fighter, or pick a square (docs/turn.md, Powers in play). */
function usePower(k) {
  var p = me().powers && me().powers[k], pd, info;
  if (!p) return;
  if (p[2] === 0) { toast("No charges left."); return; }
  pd = powerOf(p[0]);
  if (isBlink(pd)) {
    /* Blink is your move (docs/turn.md): from where you stand, instead of walking. */
    if (fight.blink) { toast("You've blinked: that was your move."); return; }
    if (moved()) { toast("Blink is your move: undo your walk first (Esc)."); return; }
  }
  info = call("ar_power", fight.me, k, fight.plan.x, fight.plan.y);
  fight.puse = k;
  if (pd.target === "around") return act(ACT.power, 0, 0, 0, k);
  if (pd.target === "square") {
    fight.psquares = info.squares;
    if (info.squares.join("").indexOf("1") < 0) { toast("Nowhere it can go from here."); return; }
    fight.cast = firstSquare(info.squares, pd);
    setMode("cast");
    return;
  }
  fight.ptargets = info.targets;
  if (!info.targets.length) {
    toast(pd.target === "foe" ? "No foe it can reach from here." : "Nobody next to you to help.");
    return;
  }
  if (info.targets.length === 1) return act(ACT.power, info.targets[0].who, 0, 0, k);
  fight.aim = 0;
  fight.aimKind = "power";
  setMode("aim");
}

function isBlink(pd) { return pd.shape === "shift" && pd.target === "square"; }

/* The cast's square chosen: a Blink is the move, and the turn goes on from there; any
 * other power is the turn's action. */
function castAt(x, y) {
  var pd = powerOf(me().powers[fight.puse][0]);
  if (!isBlink(pd)) return act(ACT.power, 0, x, y, fight.puse);
  fight.blink = fight.puse + 1;
  fight.walk = fight.reach;
  fight.reach = fight.reach.map(function (r) { return r.replace(/1/g, "0"); });
  fight.plan = { x: x, y: y };
  aimFrom();
  setMode("turn");
}

function undoMove() {
  var f = me();
  if (fight.blink) {
    fight.blink = 0;
    fight.reach = fight.walk;
  }
  fight.plan = { x: f.x, y: f.y };
  aimFrom();
  actions();
}

/* Where a square power's cursor starts: on the nearest foe it can reach, or the nearest
 * square it can. */
function firstSquare(squares, pd) {
  var best = null, bd = 1e9, me0 = fight.plan;
  fight.st.fighters.forEach(function (f) {
    if (f.side === 0 || f.state !== 0 || pd.shape === "shift") return;
    var d = Math.max(Math.abs(f.x - me0.x), Math.abs(f.y - me0.y));
    if (squares[f.y][f.x] === "1" && d < bd) { bd = d; best = { x: f.x, y: f.y }; }
  });
  if (best) return best;
  for (var y = 0; y < squares.length; ++y) {
    for (var x = 0; x < squares[y].length; ++x) {
      var d2 = Math.max(Math.abs(x - me0.x), Math.abs(y - me0.y));
      if (squares[y][x] === "1" && d2 < bd) { bd = d2; best = { x: x, y: y }; }
    }
  }
  return best;
}

function canCast(x, y) {
  return fight.psquares && y >= 0 && y < fight.psquares.length && x >= 0 &&
    x < fight.psquares[y].length && fight.psquares[y][x] === "1";
}

/* The squares a square power would touch, from the cursor: a burst's blast, a field's
 * line, a shift's end. */
function castPreview() {
  var p = me().powers[fight.puse], pd = powerOf(p[0]), tier = p[3], c = fight.cast, out = [];
  if (!c) return out;
  if (pd.shape === "burst") {
    var a = tier >= 6 ? 2 : 1;
    for (var y = c.y - a; y <= c.y + a; ++y) for (var x = c.x - a; x <= c.x + a; ++x) out.push({ x: x, y: y });
  } else if (pd.shape === "field") {
    var dx = Math.sign(c.x - fight.plan.x), dy = Math.sign(c.y - fight.plan.y), n = tier + 2;
    for (var i = 0; i < n; ++i) {
      var o = i - Math.floor((n - 1) / 2);
      out.push({ x: c.x - dy * o, y: c.y + dx * o });
    }
  } else {
    out.push(c);
  }
  return out;
}

function canReach(x, y) {
  return fight.reach && y >= 0 && y < fight.reach.length && x >= 0 && x < fight.reach[y].length &&
    fight.reach[y][x] === "1";
}

function planTo(x, y) {
  if (!canReach(x, y)) return false;
  fight.plan = { x: x, y: y };
  aimFrom();
  actions();
  return true;
}

function moved() {
  var f = me();
  return fight.plan.x !== f.x || fight.plan.y !== f.y;
}

async function act(kind, target, dx, dy, use) {
  var r = call("ar_act", fight.me, kind, fight.plan.x, fight.plan.y, target === undefined ? 0 : target,
               dx === undefined ? 0 : dx, dy === undefined ? 0 : dy, use === undefined ? 0 : use,
               fight.blink || 0);
  if (r.refused) {
    toast(kind === ACT.flee ? "No way out from here: flee from an exit, or next to no one."
          : kind === ACT.dash ? "Can't dash there from here."
          : kind === ACT.power ? "That power can't go there from here." : "That can't be done from here.");
    return;
  }
  setMode("busy");
  await play(r.events);
  settle(r);
  if (r.result !== 0) return finish(r.result);
  advance();
}

function quick() {
  if (mode !== "turn") return;
  var q = call("ar_quick", fight.me);
  fight.plan = { x: q.x, y: q.y };
  fight.blink = q.blink;
  act(q.kind, q.target, q.dx, q.dy, q.use);
}

function attack() {
  if (!fight.targets.length) { toast("Nobody in reach from here."); return; }
  if (fight.targets.length === 1) return act(ACT.attack, fight.targets[0].who);
  fight.aim = 0;
  fight.aimKind = "attack";
  setMode("aim");
}

/* Shove: a foe next to the square chosen (docs/turn.md): pushed a square away. */
function shove() {
  if (!fight.shoves.length) { toast("Nobody next to you to shove from here."); return; }
  if (fight.shoves.length === 1) return act(ACT.shove, fight.shoves[0].who);
  fight.aim = 0;
  fight.aimKind = "shove";
  setMode("aim");
}

/* Dash: instead of acting, a second move from the square chosen. */
function dash() {
  fight.dashReach = call("ar_dash", fight.me, fight.plan.x, fight.plan.y).reach;
  fight.dash = { x: fight.plan.x, y: fight.plan.y };
  setMode("dash");
}

function canDash(x, y) {
  return fight.dashReach && y >= 0 && y < fight.dashReach.length && x >= 0 &&
    x < fight.dashReach[y].length && fight.dashReach[y][x] === "1";
}

function dashTo(x, y) {
  if (!canDash(x, y)) return false;
  fight.dash = { x: x, y: y };
  return true;
}

function waitTurn() {
  if (moved() || me().waited) {
    toast(moved() ? "You can only wait before you move." : "You've already waited this round.");
    return;
  }
  act(ACT.wait, 0);
}

/* ---------------------------------------------------------------- the pack */

function openPack() {
  setMode("pack");
  drawPack();
}

function drawPack() {
  var f = me(), on = $("pack-on"), inn = $("pack-in");
  on.textContent = "";
  inn.textContent = "";
  [["Hands", f.item, 0], ["Body", f.armor_item, 1]].forEach(function (p) {
    var it = itemOf(p[1]), li = el("li", "item"), b = el("button");
    li.append(el("span", "slot", p[0]), el("span", "nm", it ? it.display : p[2] ? "No armor" : "Bare hands"));
    li.append(el("span", "what", it ? describe(it) : p[2] ? "Armor 0" : "bare hands, melee"));
    if (it) {
      b.type = "button";
      b.textContent = "Put in pack";
      b.disabled = fight.pack.length >= 6;
      b.onclick = function () { swap(p[2], 0); };
      li.append(b);
    }
    on.append(li);
  });
  if (!fight.pack.length) inn.append(el("li", "note", "The pack is empty."));
  fight.pack.forEach(function (id, n) {
    var it = itemOf(id), li = el("li", "item"), b = el("button");
    li.append(el("kbd", "k", String(n + 1)), el("span", "nm", it.display), el("span", "what", describe(it)));
    b.type = "button";
    b.textContent = it.kind === "armor" ? "Wear" : "Hold";
    b.onclick = function () { swap(it.kind === "armor" ? 1 : 0, id); };
    li.append(b);
    inn.append(li);
  });
}

function describe(it) {
  var skill = it.kind === "ranged" ? "ranged" : it.kind === "focus" ? "channel" : "melee";
  var bonus = it.kind === "melee" ? me().melee_bonus : 0;
  if (it.kind === "armor") return "Armor " + it.armor + " · tier " + it.tier;
  return (it.damage + bonus) + " " + it.type + ", " + (it.kind === "focus" ? "a power, against Ward" : it.kind) +
    " · rolls " + skill + " " + S.native.skills[skill];
}

/* Hold or wear item (0: empty the slot); what was there goes in the pack. */
function swap(slot, item) {
  var f = me(), was = slot ? f.armor_item : f.item, r;
  if (item) fight.pack.splice(fight.pack.indexOf(item), 1);
  if (was) fight.pack.push(was);
  r = call("ar_equip", fight.me, slot, item);
  fight.st.fighters = r.fighters;
  fight.swaps++;
  log((item ? (slot ? "Puts on " : "Takes up ") + itemOf(item).display
            : "Puts away " + itemOf(was).display) + " (free).", "good");
  aimFrom();
  cards();
  drawPack();
  actions();
}

/* ----------------------------------------------------------------- the end */

function finish(result) {
  var won = result === 1, title = $("end-title"), body = $("end-body");
  var f = fight.st.fighters[0], a = S.lab;
  fight.whose = -1;
  title.textContent = won ? "Victory" : result === 2 ? "Defeated" : "Escaped";
  title.className = won ? "won" : result === 2 ? "lost" : "";
  body.textContent = "";
  var grid = el("div", "endstats");
  [[fight.round, "rounds"], [fight.st.fighters[0].health + " / " + f.health_max, "health left"],
   [fight.dealt, "damage dealt"], [fight.taken, "damage taken"],
   [fight.swings ? Math.round(100 * fight.hits / fight.swings) + "%" : "-", "of your attacks landed"],
   [fight.swaps, "swaps from the pack"]].forEach(function (p) {
    var d = el("div");
    d.append(el("b", null, String(p[0])), el("span", null, p[1]));
    grid.append(d);
  });
  body.append(grid, el("p", "note", "The computer, playing both sides by rules v1, wins this " + a.won +
    "% of the time in " + a.rounds + " rounds. How did yours feel?"));
  log(title.textContent + ".", won ? "good" : "bad");
  setMode("end");
}

function feedbackUrl() {
  var q = new URLSearchParams({
    template: "playtest.yml",
    title: "[" + S.code + "] " + S.title,
    scenario: S.code + " " + S.title + " (modern arena)",
    build: BUILD,
    played: String(plays(S.code, 0))
  });
  return REPO + "/issues/new?" + q.toString();
}

function plays(code, add) {
  var key = "apb-studio-arena-plays-" + code, n = 0;
  try {
    n = Number(localStorage.getItem(key)) || 0;
    if (add) localStorage.setItem(key, String(n += add));
  } catch (e) { /* private window: no count */ }
  return n;
}

/* ---------------------------------------------------- showing what happened */

function tween(s, x, y, ms) {
  var x0 = s.x, y0 = s.y, t0 = performance.now(), dur = fast ? ms / 5 : ms;
  return new Promise(function (done) {
    (function step() {
      var t = Math.min(1, (performance.now() - t0) / dur), e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      s.x = x0 + (x - x0) * e;
      s.y = y0 + (y - y0) * e;
      if (t < 1) requestAnimationFrame(step); else done();
    })();
  });
}

function floater(x, y, text, colour) {
  fight.floaters.push({ x: x, y: y, text: text, colour: colour, t0: performance.now() });
}

async function play(events) {
  var i, e;
  for (i = 0; i < events.length; ++i) {
    e = events[i];
    await show1(e);
  }
}

/* Damage shown as it lands: health down, a flash, a number rising. */
function hurtShown(who, n, why, cls) {
  var s = fight.shown[who];
  if (n > 0) {
    s.health = Math.max(0, s.health - n);
    s.flash = performance.now();
    if (fight.st.fighters[who].side === 0) fight.taken += n;
  }
  floater(s.x, s.y, n > 0 ? "-" + n : "0", n > 0 ? "#ef6b5b" : "#9a98a6");
  if (why) log(why, cls || (n > 0 ? (fight.st.fighters[who].side === 0 ? "bad" : "good") : null));
}

function rolled(e) {
  return e.roll + "+" + (e.total - e.roll) + "=" + e.total + " vs " + e.tn;
}

async function show1(e) {
  var s, t, c = e.cond ? condOf(e.cond) : null;
  switch (e.kind) {
  case "turn":
    if (e.value !== fight.round) {
      fight.round = e.value;
      log("Round " + e.value, "round");
    }
    fight.whose = e.actor;
    cards();
    if (fight.st.fighters[e.actor].side !== 0) await wait(220);
    break;
  case "move":
  case "push":
    s = fight.shown[e.actor];
    await tween(s, e.x, e.y, e.kind === "push" ? 140 : 110);
    if (e.kind === "push") log(name(e.actor) + " is pushed back.");
    break;
  case "dash":
    log(name(e.actor) + " dashes on.");
    break;
  case "free":
    log(name(e.actor) + " gets a free attack on " + name(e.target) + ".", "bad");
    await wait(150);
    break;
  case "attack":
    await strike(e);
    break;
  case "power":
    log(name(e.actor) + " uses " + powerOf(e.cond).display + " (tier " + e.value + ").", "round");
    t = { kind: "SPARK", colour: 4, at: { x: e.x, y: e.y }, t0: performance.now(), dur: fast ? 60 : 320 };
    fight.effects.push(t);
    await wait(300);
    fight.effects.splice(fight.effects.indexOf(t), 1);
    break;
  case "hit":
    s = fight.shown[e.target];
    if (e.value) hurtShown(e.target, e.value, null);
    else floater(s.x, s.y, e.result ? "hit" : "miss", e.result ? "#e8c547" : "#9a98a6");
    log([el("span", null, powerOf(e.cond).display + " → " + name(e.target) + ": "), el("span", "roll", rolled(e)),
         el("span", null, ", " + RESULTS[e.result] + (e.value ? ", " + e.value + " damage." : "."))],
        e.result ? (fight.st.fighters[e.actor].side === 0 ? "good" : "bad") : null);
    if (fight.st.fighters[e.actor].side === 0 && fight.st.fighters[e.target].side !== 0) {
      fight.swings++;
      if (e.result) fight.hits++;
      fight.dealt += e.value;
    }
    cards();
    await wait(220);
    break;
  case "mend":
    s = fight.shown[e.target];
    s.health = Math.min(fight.st.fighters[e.target].health_max, s.health + e.value);
    floater(s.x, s.y, "+" + e.value, "#7fcf7a");
    log(name(e.target) + " is healed " + e.value + " (" + powerOf(e.cond).display + ").", "good");
    await wait(250);
    break;
  case "field":
    t = fight.st.map[e.y];
    fight.st.map[e.y] = t.slice(0, e.x) + String(e.value) + t.slice(e.x + 1);
    await wait(60);
    break;
  case "shift":
    s = fight.shown[e.actor];
    await tween(s, e.x, e.y, 160);
    log(name(e.actor) + " blinks across.");
    break;
  case "shove":
    s = fight.shown[e.actor];
    t = fight.shown[e.target];
    s.lunge = { x: t.x - s.x, y: t.y - s.y, t0: performance.now(), dur: fast ? 50 : 240 };
    log([el("span", null, name(e.actor) + " shoves " + name(e.target) + ": "), el("span", "roll", rolled(e)),
         el("span", null, ", " + RESULTS[e.result] + ".")], e.result ? "good" : null);
    await wait(220);
    break;
  case "slam":
    hurtShown(e.actor, e.value, name(e.actor) + " slams into something: " + e.value + " damage.");
    await wait(250);
    break;
  case "fall":
    s = fight.shown[e.actor];
    for (t = 0; t <= 1; t += 0.1) { s.fall = t; await wait(30); }
    s.alpha = 0;
    s.fell = true;
    log(name(e.actor) + " falls into the pit!", fight.st.fighters[e.actor].side === 0 ? "bad" : "good");
    break;
  case "down":
    fight.shown[e.target].state = 1;
    log(name(e.target) + " is down!", fight.st.fighters[e.target].side === 0 ? "bad" : "good");
    await wait(350);
    break;
  case "hazard":
    hurtShown(e.actor, e.value, name(e.actor) + " takes " + e.value + " from the ground.");
    await wait(300);
    break;
  case "cond_on":
    s = fight.shown[e.actor];
    floater(s.x, s.y + 0.35, c.tag, "#e8c547");
    log(name(e.actor) + " is " + c.display.toLowerCase() + (e.value ? " (" + e.value + " rounds)" : "") +
        ": " + c.what + ".", fight.st.fighters[e.actor].side === 0 ? "bad" : "good");
    await wait(180);
    break;
  case "cond_off":
    log(name(e.actor) + " is no longer " + c.display.toLowerCase() + ".");
    break;
  case "immune":
    s = fight.shown[e.actor];
    floater(s.x, s.y + 0.35, "immune", "#6fb3ff");
    log(name(e.actor) + " is immune to " + c.display.toLowerCase() + ".");
    break;
  case "tick":
    hurtShown(e.actor, e.value, name(e.actor) + " takes " + e.value + " from " + c.display.toLowerCase() + ".");
    await wait(250);
    break;
  case "heal":
    s = fight.shown[e.actor];
    s.health = Math.min(fight.st.fighters[e.actor].health_max, s.health + e.value);
    floater(s.x, s.y, e.value ? "+" + e.value : "no healing", "#7fcf7a");
    log(name(e.actor) + (e.value ? " heals " + e.value : " can't heal") + " (" + c.display.toLowerCase() + ").");
    await wait(200);
    break;
  case "skip":
    log(name(e.actor) + " loses the turn: " + c.display.toLowerCase() + ".", fight.st.fighters[e.actor].side === 0 ? "bad" : "good");
    await wait(300);
    break;
  case "shake":
    log([el("span", null, name(e.actor) + " tries to shake off " + c.display.toLowerCase() + ": "),
         el("span", "roll", rolled(e)), el("span", null, e.result >= 2 ? ", and does." : ", and can't.")]);
    break;
  case "stand":
    log(name(e.actor) + " stands up (" + e.value + " squares of move left).");
    break;
  case "thorns":
    hurtShown(e.target, e.value, name(e.target) + " is hurt by " + name(e.actor) + "'s " +
              c.display.toLowerCase() + ": " + e.value + ".");
    break;
  case "absorb":
    s = fight.shown[e.actor];
    floater(s.x, s.y + 0.2, "barrier " + e.value, "#6fb3ff");
    log(name(e.actor) + "'s barrier takes " + e.value + ".");
    break;
  case "guard":
    log(name(e.actor) + " stands guard.");
    await wait(200);
    break;
  case "wait":
    log(name(e.actor) + " waits.");
    break;
  case "flee":
    log(name(e.actor) + " tries to get away: " + e.roll + " + " + (e.total - e.roll) + " = " +
        e.total + " vs TN " + e.tn + ", " + (e.result ? "out" : "caught") + ".");
    await wait(250);
    break;
  case "gone":
    s = fight.shown[e.actor];
    for (t = 1; t >= 0; t -= 0.1) { s.alpha = t; await wait(25); }
    log(name(e.actor) + " is gone.");
    break;
  }
}

async function strike(e) {
  var a = fight.st.fighters[e.actor], sa = fight.shown[e.actor], st = fight.shown[e.target];
  var mine = a.side === 0, res = RESULTS[e.result] || "?", t0, fx, dur, line;
  var colour = TYPE_COLOUR[TYPES[a.type]] === undefined ? 1 : TYPE_COLOUR[TYPES[a.type]];
  if (a.ranged || a.power) {
    fx = { kind: a.power ? "SPARK" : "BOLT", colour: colour, from: { x: sa.x, y: sa.y },
           to: { x: st.x, y: st.y }, t0: performance.now(), dur: fast ? 50 : 260 };
    fight.effects.push(fx);
    await wait(260);
    fight.effects.splice(fight.effects.indexOf(fx), 1);
  } else {
    sa.lunge = { x: st.x - sa.x, y: st.y - sa.y, t0: performance.now(), dur: fast ? 50 : 240 };
    await wait(120);
    fx = { kind: "SLASH", colour: colour, at: { x: st.x, y: st.y }, t0: performance.now(), dur: fast ? 40 : 220 };
    fight.effects.push(fx);
    await wait(200);
    fight.effects.splice(fight.effects.indexOf(fx), 1);
  }
  if (e.value) {
    st.health = Math.max(0, st.health - e.value);
    st.flash = performance.now();
    floater(st.x, st.y, (e.result === 3 ? "CRIT -" : "-") + e.value, e.result === 3 ? "#e8c547" : "#ef6b5b");
  } else {
    floater(st.x, st.y, "miss", "#9a98a6");
  }
  if (mine && fight.st.fighters[e.target].side !== 0) {
    fight.swings++;
    if (e.value) fight.hits++;
    fight.dealt += e.value;
  } else if (fight.st.fighters[e.target].side === 0) {
    fight.taken += e.value;
  }
  line = [el("span", null, name(e.actor) + " → " + name(e.target) + ": "),
          el("span", "roll", e.roll + "+" + (e.total - e.roll) + "=" + e.total + " vs " + e.tn),
          el("span", null, ", " + res + (e.value ? ", " + e.value + " damage." : "."))];
  log(line, e.value ? (mine ? "good" : "bad") : null);
  cards();
  await wait(260);
}

/* ------------------------------------------------------------ the board */

var board, ctx, view = { scale: 1, ox: 0, oy: 0 };

function resize() {
  if (!fight) return;
  var r = board.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  var w = fight.st.map[0].length * SQ, h = fight.st.map.length * SQ;
  board.width = Math.max(1, Math.round(r.width * dpr));
  board.height = Math.max(1, Math.round(r.height * dpr));
  view.scale = Math.min((r.width - 32) / w, (r.height - 32) / h) * dpr;
  view.ox = (board.width - w * view.scale) / 2;
  view.oy = (board.height - h * view.scale) / 2;
}

function squareAt(cx, cy) {
  var dpr = window.devicePixelRatio || 1;
  var x = Math.floor((cx * dpr - view.ox) / view.scale / SQ);
  var y = Math.floor((cy * dpr - view.oy) / view.scale / SQ);
  if (!fight || y < 0 || x < 0 || y >= fight.st.map.length || x >= fight.st.map[0].length) return null;
  return { x: x, y: y };
}

function fighterAt(x, y) {
  var i, s;
  for (i = 0; i < fight.shown.length; ++i) {
    s = fight.shown[i];
    if (s.state === 0 && Math.round(s.x) === x && Math.round(s.y) === y) return i;
  }
  return -1;
}

function bracket(x, y, colour, w) {
  var p = 2, l = 9, a = x * SQ + p, b = y * SQ + p, z = SQ - 2 * p;
  ctx.strokeStyle = colour;
  ctx.lineWidth = w || 1.5;
  ctx.beginPath();
  ctx.moveTo(a, b + l); ctx.lineTo(a, b); ctx.lineTo(a + l, b);
  ctx.moveTo(a + z - l, b); ctx.lineTo(a + z, b); ctx.lineTo(a + z, b + l);
  ctx.moveTo(a + z, b + z - l); ctx.lineTo(a + z, b + z); ctx.lineTo(a + z - l, b + z);
  ctx.moveTo(a + l, b + z); ctx.lineTo(a, b + z); ctx.lineTo(a, b + z - l);
  ctx.stroke();
}

function tag(x, y, text, colour) {
  ctx.font = "600 7px system-ui, sans-serif";
  var w = ctx.measureText(text).width + 6, cx = x * SQ + SQ / 2;
  ctx.fillStyle = "rgba(10,10,14,.85)";
  ctx.fillRect(cx - w / 2, y * SQ - 9, w, 10);
  ctx.fillStyle = colour;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, cx, y * SQ - 4);
}

function frame(now) {
  requestAnimationFrame(frame);
  if (!fight || $("fight").hidden) return;
  var map = fight.st.map, x, y, i, s, f, order, fx, t, pulse;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = "#101015";
  ctx.fillRect(0, 0, board.width, board.height);
  ctx.setTransform(view.scale, 0, 0, view.scale, view.ox, view.oy);
  ctx.imageSmoothingEnabled = false;

  for (y = 0; y < map.length; ++y) {
    for (x = 0; x < map[y].length; ++x) {
      ctx.drawImage(tileSprite(ART.tiles.order[Number(map[y][x])] || "open"), x * SQ, y * SQ);
    }
  }
  /* Where the traveler can go, and where they'll stand. */
  if (mode === "turn" || mode === "aim") {
    ctx.fillStyle = "rgba(111,179,255,.16)";
    for (y = 0; y < map.length; ++y) {
      for (x = 0; x < map[y].length; ++x) if (canReach(x, y)) ctx.fillRect(x * SQ + 1, y * SQ + 1, SQ - 2, SQ - 2);
    }
    if (hover && canReach(hover.x, hover.y) && mode === "turn") bracket(hover.x, hover.y, "rgba(230,228,220,.5)", 1);
    pulse = 0.6 + 0.4 * Math.sin(now / 220);
    bracket(fight.plan.x, fight.plan.y, "rgba(232,197,71," + pulse + ")", 2);
  }
  /* A power on a square: where it can go, and what it would touch from the cursor. */
  if (mode === "cast") {
    ctx.fillStyle = "rgba(180,120,255,.14)";
    for (y = 0; y < map.length; ++y) {
      for (x = 0; x < map[y].length; ++x) if (canCast(x, y)) ctx.fillRect(x * SQ + 1, y * SQ + 1, SQ - 2, SQ - 2);
    }
    ctx.fillStyle = canCast(fight.cast.x, fight.cast.y) ? "rgba(239,107,91,.28)" : "rgba(150,150,150,.2)";
    castPreview().forEach(function (q) {
      if (q.y >= 0 && q.y < map.length && q.x >= 0 && q.x < map[0].length) ctx.fillRect(q.x * SQ + 1, q.y * SQ + 1, SQ - 2, SQ - 2);
    });
    pulse = 0.6 + 0.4 * Math.sin(now / 220);
    bracket(fight.cast.x, fight.cast.y, "rgba(200,150,255," + pulse + ")", 2);
  }
  /* A Dash: where the second move can go, from the square chosen. */
  if (mode === "dash") {
    ctx.fillStyle = "rgba(232,197,71,.16)";
    for (y = 0; y < map.length; ++y) {
      for (x = 0; x < map[y].length; ++x) if (canDash(x, y)) ctx.fillRect(x * SQ + 1, y * SQ + 1, SQ - 2, SQ - 2);
    }
    if (hover && canDash(hover.x, hover.y)) bracket(hover.x, hover.y, "rgba(230,228,220,.5)", 1);
    bracket(fight.plan.x, fight.plan.y, "rgba(232,197,71,.5)", 1);
    pulse = 0.6 + 0.4 * Math.sin(now / 220);
    bracket(fight.dash.x, fight.dash.y, "rgba(232,197,71," + pulse + ")", 2);
  }

  order = fight.shown.map(function (s, i) { return i; }).sort(function (a, b) {
    return fight.shown[a].y - fight.shown[b].y;
  });
  order.forEach(function (i) {
    var s = fight.shown[i], f = fight.st.fighters[i], px = s.x, py = s.y, img, l, k, fl;
    if (s.alpha <= 0) return;
    if (i === fight.me && (mode === "turn" || mode === "aim" || mode === "dash" || mode === "cast") && s.state === 0) {
      ctx.globalAlpha = 0.3;
      ctx.drawImage(figureSprite(S.native.figures[i]), px * SQ + 3, py * SQ + 8);
      ctx.globalAlpha = 1;
      px = mode === "dash" ? fight.dash.x : fight.plan.x;
      py = mode === "dash" ? fight.dash.y : fight.plan.y;
    }
    if (s.lunge) {
      l = (now - s.lunge.t0) / s.lunge.dur;
      if (l >= 1) s.lunge = null;
      else { k = Math.sin(l * Math.PI) * 0.3; px += s.lunge.x * k; py += s.lunge.y * k; }
    }
    ctx.globalAlpha = s.alpha;
    if (s.state === 1) {
      ctx.save();
      ctx.translate(px * SQ + 16, py * SQ + 22);
      ctx.rotate(Math.PI / 2);
      ctx.globalAlpha = 0.6;
      ctx.drawImage(figureSprite(S.native.figures[i], true), -13, -12);
      ctx.restore();
      ctx.globalAlpha = 1;
      return;
    }
    /* A shadow, and a ring for whoever's turn it is. */
    ctx.fillStyle = "rgba(0,0,0,.35)";
    ctx.beginPath();
    ctx.ellipse(px * SQ + 16, py * SQ + 29, 9, 2.5, 0, 0, 2 * Math.PI);
    ctx.fill();
    if (fight.whose === i) {
      ctx.strokeStyle = f.side === 0 ? "rgba(111,179,255,.9)" : "rgba(239,107,91,.9)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.ellipse(px * SQ + 16, py * SQ + 29, 11, 3.5, 0, 0, 2 * Math.PI);
      ctx.stroke();
    }
    img = figureSprite(S.native.figures[i]);
    if (s.fall) {
      /* Into the pit: smaller and smaller. */
      ctx.save();
      ctx.translate(px * SQ + 16, py * SQ + 20);
      ctx.scale(1 - s.fall, 1 - s.fall);
      ctx.drawImage(img, -13, -12);
      ctx.restore();
      ctx.globalAlpha = 1;
      return;
    }
    ctx.drawImage(img, px * SQ + 3, py * SQ + 8);
    fl = (now - s.flash) / 180;
    if (s.flash && fl < 1) {
      ctx.globalAlpha = 1 - fl;
      ctx.globalCompositeOperation = "lighter";
      ctx.drawImage(img, px * SQ + 3, py * SQ + 8);
      ctx.drawImage(img, px * SQ + 3, py * SQ + 8);
      ctx.globalCompositeOperation = "source-over";
    }
    ctx.globalAlpha = s.alpha;
    /* Health. */
    var w = 22, frac = Math.max(0, s.health / f.health_max);
    ctx.fillStyle = "rgba(10,10,14,.8)";
    ctx.fillRect(px * SQ + 5, py * SQ + 3, w, 3);
    ctx.fillStyle = frac > 0.5 ? "#7fcf7a" : frac > 0.25 ? "#e8c547" : "#ef6b5b";
    ctx.fillRect(px * SQ + 5, py * SQ + 3, w * frac, 3);
    if (f.guarding) { ctx.fillStyle = "#e8c547"; ctx.fillRect(px * SQ + 28, py * SQ + 2, 2, 5); }
    /* Its conditions (not a race's traits), as tags under its feet. */
    var tags = (f.conds || []).filter(function (cr) { return !condOf(cr[0]).trait; })
      .map(function (cr) { return condOf(cr[0]).tag; }).slice(0, 3);
    if (tags.length) {
      ctx.font = "700 5px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      var text = tags.join(" "), tw = ctx.measureText(text).width + 4;
      ctx.fillStyle = "rgba(10,10,14,.85)";
      ctx.fillRect(px * SQ + 16 - tw / 2, py * SQ + 28.5, tw, 6);
      ctx.fillStyle = "#e8c547";
      ctx.fillText(text, px * SQ + 16, py * SQ + 31.7);
    }
    ctx.globalAlpha = 1;
  });

  /* Who can be attacked from the square chosen, and the TN for each. */
  if (mode === "turn" || mode === "aim") {
    (mode === "aim" ? aimList() : fight.targets).forEach(function (t, n) {
      var s = fight.shown[t.who], on = mode === "aim" && n === fight.aim;
      bracket(s.x, s.y, on ? "#ef6b5b" : "rgba(239,107,91,.6)", on ? 2.2 : 1.2);
      tag(s.x, s.y, t.tn ? (mode === "aim" && fight.aimKind === "shove" ? "Shove " : "TN ") + t.tn
          : powerOf(me().powers[fight.puse][0]).display, on ? "#ffffff" : "#ef9b8f");
    });
  }

  /* Bolts and slashes. */
  fight.effects.forEach(function (fx) {
    var t = Math.min(1, (now - fx.t0) / fx.dur), img = effectSprite(fx.kind, fx.colour), px, py;
    if (!img) return;
    if (fx.from) {
      px = fx.from.x + (fx.to.x - fx.from.x) * t;
      py = fx.from.y + (fx.to.y - fx.from.y) * t;
    } else {
      px = fx.at.x; py = fx.at.y;
      ctx.globalAlpha = 1 - t * 0.6;
    }
    ctx.drawImage(img, px * SQ + 4, py * SQ + 5);
    ctx.globalAlpha = 1;
  });

  /* Numbers that rise and fade. */
  fight.floaters = fight.floaters.filter(function (fl) {
    var t = (now - fl.t0) / 900;
    if (t >= 1) return false;
    ctx.globalAlpha = 1 - t * t;
    ctx.font = "700 9px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = "rgba(10,10,14,.9)";
    ctx.strokeText(fl.text, fl.x * SQ + 16, fl.y * SQ + 4 - t * 14);
    ctx.fillStyle = fl.colour;
    ctx.fillText(fl.text, fl.x * SQ + 16, fl.y * SQ + 4 - t * 14);
    ctx.globalAlpha = 1;
    return true;
  });
}

/* ---------------------------------------------------- every button, always */

/* Each: [key label, text, what it does, disabled?, why it's disabled, primary?] */
function buttons() {
  var t = fight && fight.targets ? fight.targets.length : 0;
  var sh = fight && fight.shoves ? fight.shoves.length : 0;
  switch (mode) {
  case "intro":
    return [["↑ ↓", "Choose a scenario", function () { pick(1); }, false, "", false, "hint"],
            ["Enter", "Start the fight", start, false, "", true]];
  case "turn":
    return [["Arrows", "Move (or click a lit square)", null, false, "", false, "hint"],
            ["A", t > 1 ? "Attack…" : "Attack", attack, !t, "Nobody in reach from here", true],
            ["S", sh > 1 ? "Shove…" : "Shove", shove, !sh, "Nobody next to you to shove"],
            ["D", "Dash", dash]].concat(powerButtons()).concat([
            ["G", "Guard", function () { act(ACT.guard, 0); }],
            ["W", "Wait", waitTurn, moved() || me().waited, moved() ? "Only before you move" : "Once a round"],
            ["P", "Pack", openPack],
            ["F", "Flee", function () { act(ACT.flee, 0); }],
            ["Esc", fight.blink ? "Undo blink" : "Undo move", undoMove, !moved(), "You haven't moved"],
            ["Enter", "End turn", function () { act(ACT.done, 0); }],
            ["Q", "Quick turn", quick],
            ["gap"],
            ["T", auto ? "Auto: on" : "Auto: off", toggleAuto, false, "", false, "toggle"],
            ["Z", fast ? "Fast: on" : "Fast: off", toggleFast, false, "", false, "toggle"],
            ["X", "Leave", leave]]);
  case "aim":
    return [["← →", "Next target", function () { cycle(1); }],
            ["Enter", fight.aimKind === "shove" ? "Shove" : fight.aimKind === "power"
              ? powerOf(me().powers[fight.puse][0]).display : "Strike", function () {
              if (fight.aimKind === "power") act(ACT.power, aimList()[fight.aim].who, 0, 0, fight.puse);
              else act(fight.aimKind === "shove" ? ACT.shove : ACT.attack, aimList()[fight.aim].who);
            }, false, "", true],
            ["Esc", "Back", function () { setMode("turn"); }]];
  case "cast":
    return [["Arrows", "Where (or click a lit square)", null, false, "", false, "hint"],
            ["Enter", powerOf(me().powers[fight.puse][0]).display + " there", function () {
              castAt(fight.cast.x, fight.cast.y);
            }, !canCast(fight.cast.x, fight.cast.y), "It can't go there", true],
            ["Esc", "Back", function () { setMode("turn"); }]];
  case "dash":
    return [["Arrows", "Where to dash (or click a lit square)", null, false, "", false, "hint"],
            ["Enter", "Dash there", function () { act(ACT.dash, 0, fight.dash.x, fight.dash.y); },
             fight.dash.x === fight.plan.x && fight.dash.y === fight.plan.y, "Pick a square first", true],
            ["Esc", "Back", function () { setMode("turn"); }]];
  case "pack":
    return [["1-6", "Hold or wear from the pack", null, false, "", false, "hint"],
            ["Esc", "Close the pack", function () { setMode("turn"); }, false, "", true]];
  case "busy":
    return [["", "The foes are moving…", null, false, "", false, "hint"],
            ["gap"],
            ["T", auto ? "Auto: on" : "Auto: off", toggleAuto, false, "", false, "toggle"],
            ["Z", fast ? "Fast: on" : "Fast: off", toggleFast, false, "", false, "toggle"]];
  case "end":
    return [["R", "Fight again", start, false, "", true],
            ["F", "Give feedback", function () { window.open(feedbackUrl(), "_blank", "noopener"); }],
            ["Esc", "Back to the scenarios", intro]];
  }
  return [];
}

/* A button for each of the traveler's powers: 1-4. */
function powerButtons() {
  var f = me();
  return (f.powers || []).map(function (p, k) {
    var pd = powerOf(p[0]), blink = isBlink(pd);
    var off = p[2] === 0 ? "No charges left this fight"
            : blink && fight.blink ? "You've blinked this turn"
            : blink && moved() ? "Blink is your move: before you walk" : "";
    return [String(k + 1), pd.display + (blink ? " (move" + (p[2] >= 0 ? ", " + p[2] : "") + ")"
            : p[2] >= 0 ? " (" + p[2] + ")" : ""), function () { usePower(k); },
            !!off, off, false, "power"];
  });
}

function actions() {
  var bar = $("actions");
  bar.textContent = "";
  buttons().forEach(function (b) {
    if (b[0] === "gap") { bar.append(el("span", "gap")); return; }
    if (b[6] === "hint") {
      var h = el("span", "hint");
      if (b[0]) h.append(el("kbd", null, b[0]));
      h.append(document.createTextNode(b[1]));
      bar.append(h);
      return;
    }
    var btn = el("button", b[5] ? "primary" : null), k = el("kbd", null, b[0]);
    btn.type = "button";
    btn.append(k, document.createTextNode(b[1]));
    btn.disabled = !!b[3];
    if (b[3] && b[4]) btn.title = b[4];
    if (b[6] === "toggle") btn.setAttribute("aria-pressed", String(b[1].indexOf("on") > 0));
    if (b[6] === "power") btn.classList.add("power");
    btn.onclick = b[2];
    btn.dataset.key = b[0];
    bar.append(btn);
  });
}

function toggleAuto() {
  auto = !auto;
  actions();
  if (auto && mode === "turn") quick();
}

function toggleFast() { fast = !fast; actions(); }

function leave() {
  if (mode === "busy") return;
  intro();
}

function cycle(d) {
  var n = aimList().length;
  fight.aim = (fight.aim + d + n) % n;
}

/* The scenarios listed: the ones to play now (scenarios.py's PLAYING), and one opened by
 * its link (#scenario=R-02) if it isn't among them. */
function shown() {
  var out = [];
  SCENARIOS.forEach(function (s, i) { if (s.play || i === picked) out.push(i); });
  return out;
}

function pick(d) {
  var all = shown(), k = all.indexOf(picked);
  picked = all[(k + d + all.length) % all.length];
  intro();
  var cur = document.querySelector('.scenarios button[aria-current="true"]');
  if (cur) cur.focus();
}

/* The keys: each button's, plus arrows and the numpad to move. */
var STEPS = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0],
              Numpad8: [0, -1], Numpad2: [0, 1], Numpad4: [-1, 0], Numpad6: [1, 0],
              Numpad7: [-1, -1], Numpad9: [1, -1], Numpad1: [-1, 1], Numpad3: [1, 1] };

function onKey(e) {
  var k = e.key, step = STEPS[e.code] || STEPS[k], b, f;
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (mode === "intro") {
    if (k === "ArrowDown") { pick(1); e.preventDefault(); }
    else if (k === "ArrowUp") { pick(-1); e.preventDefault(); }
    else if (k === "Enter") { e.preventDefault(); start(); }
    return;
  }
  if (mode === "turn" && step) {
    e.preventDefault();
    f = fight.plan;
    if (!planTo(f.x + step[0], f.y + step[1])) toast("Can't get there this turn.");
    return;
  }
  if (mode === "cast" && step) {
    e.preventDefault();
    var nx = fight.cast.x + step[0], ny = fight.cast.y + step[1];
    if (ny >= 0 && ny < fight.st.map.length && nx >= 0 && nx < fight.st.map[0].length) fight.cast = { x: nx, y: ny };
    actions();
    return;
  }
  if (mode === "dash" && step) {
    e.preventDefault();
    if (!dashTo(fight.dash.x + step[0], fight.dash.y + step[1])) toast("Can't dash there.");
    actions();
    return;
  }
  if (mode === "aim" && (k === "ArrowRight" || k === "ArrowDown" || k === "Tab")) { e.preventDefault(); cycle(1); return; }
  if (mode === "aim" && (k === "ArrowLeft" || k === "ArrowUp")) { e.preventDefault(); cycle(-1); return; }
  if (mode === "pack" && /^[1-6]$/.test(k)) {
    var id = fight.pack[Number(k) - 1];
    if (id) swap(itemOf(id).kind === "armor" ? 1 : 0, id);
    return;
  }
  if (mode === "pack" && (k === "p" || k === "P")) { setMode("turn"); return; }
  b = buttons().filter(function (x) {
    var key = x[0];
    if (!x[2] || x[3] || x[6] === "hint") return false;
    if (key === "Esc") return k === "Escape";
    if (key === "Enter") return k === "Enter";
    return key.length === 1 && key.toLowerCase() === k.toLowerCase();
  })[0];
  if (b) { e.preventDefault(); b[2](); }
}

function onClick(e) {
  if (!fight) return;
  var sq = squareAt(e.offsetX, e.offsetY), who, t;
  if (!sq) return;
  if (mode === "cast") {
    if (canCast(sq.x, sq.y)) castAt(sq.x, sq.y);
    else toast("It can't go there.");
    return;
  }
  if (mode === "aim" && fight.aimKind === "power") {
    who = fighterAt(sq.x, sq.y);
    t = fight.ptargets.filter(function (x) { return x.who === who; })[0];
    if (t) act(ACT.power, t.who, 0, 0, fight.puse);
    return;
  }
  if (mode === "dash") {
    if (dashTo(sq.x, sq.y)) act(ACT.dash, 0, sq.x, sq.y);
    else toast("Can't dash there.");
    return;
  }
  if (mode === "aim" && fight.aimKind === "shove") {
    who = fighterAt(sq.x, sq.y);
    t = fight.shoves.filter(function (x) { return x.who === who; })[0];
    if (t) act(ACT.shove, t.who);
    return;
  }
  if (mode === "turn" || mode === "aim") {
    who = fighterAt(sq.x, sq.y);
    t = fight.targets.filter(function (x) { return x.who === who; })[0];
    if (t) { act(ACT.attack, t.who); return; }
    if (mode === "turn" && !planTo(sq.x, sq.y) && who < 0) toast("Can't get there this turn.");
  }
}

function onMove(e) {
  if (!fight) return;
  hover = squareAt(e.offsetX, e.offsetY);
  var who = hover ? fighterAt(hover.x, hover.y) : -1;
  var t = fight.targets && fight.targets.some(function (x) { return x.who === who; });
  board.style.cursor = ((mode === "turn" || mode === "aim") && (t || (hover && canReach(hover.x, hover.y))))
    || (mode === "dash" && hover && canDash(hover.x, hover.y))
    || (mode === "cast" && hover && canCast(hover.x, hover.y)) ? "pointer" : "default";
  board.title = who >= 0 ? name(who) + (t ? ": click to attack" : "") : "";
}

/* ----------------------------------------------------------------- start */

/* On the published site there's no art desk (it saves into the game's files, so it runs
 * only in the studio, on a machine with the game): the first tab goes back to the
 * platform's arena page instead. */
function published() {
  document.querySelector("h1").firstChild.textContent = "Arena ";
}
if (window.top !== window) document.documentElement.classList.add("framed");

async function boot() {
  var got = await Promise.all(["art.json", "scenarios.json", "items.json", "lab.json", "conditions.json",
                               "powers.json"].map(function (f) {
    return fetch(f).then(function (r) {
      if (!r.ok) throw new Error(f + ": " + r.status);
      return r.json();
    });
  }));
  ART = got[0];
  SCENARIOS = got[3].concat(got[1]);                  /* the rules lab's first: they're new */
  ITEMS = got[2];
  CONDS = got[4];
  POWERS = got[5];
  fetch("build.json").then(function (r) { return r.json(); }).then(function (b) {
    BUILD = b.commit + " (" + b.built + ")";
    if (b.built !== "studio") published();
  }).catch(published);
  var M = await ArenaRules();
  rules.ar_begin = M.cwrap("ar_begin", "string", ["number", "string"]);
  rules.ar_next = M.cwrap("ar_next", "string", []);
  rules.ar_reach = M.cwrap("ar_reach", "string", ["number"]);
  rules.ar_targets = M.cwrap("ar_targets", "string", ["number", "number", "number"]);
  rules.ar_act = M.cwrap("ar_act", "string", ["number", "number", "number", "number", "number", "number", "number", "number",
                                              "number"]);
  rules.ar_power = M.cwrap("ar_power", "string", ["number", "number", "number", "number"]);
  rules.ar_dash = M.cwrap("ar_dash", "string", ["number", "number", "number"]);
  rules.ar_shoves = M.cwrap("ar_shoves", "string", ["number", "number", "number"]);
  rules.ar_quick = M.cwrap("ar_quick", "string", ["number"]);
  rules.ar_equip = M.cwrap("ar_equip", "string", ["number", "number", "number"]);
  board = $("board");
  ctx = board.getContext("2d");
  board.addEventListener("click", onClick);
  board.addEventListener("mousemove", onMove);
  board.addEventListener("mouseleave", function () { hover = null; });
  window.addEventListener("resize", resize);
  document.addEventListener("keydown", onKey);
  var sd = /seed=(\d+)/.exec(location.hash);
  if (sd) fixedSeed = Number(sd[1]);
  var m = /scenario=([AR]-\d+)/.exec(location.hash);
  if (m) picked = Math.max(0, SCENARIOS.findIndex(function (s) { return s.code === m[1]; }));
  intro();
  requestAnimationFrame(frame);
  window.arena = {                                                  /* for tests */
    state: function () { return { mode: mode, fight: fight, S: S, auto: auto, fast: fast }; },
    seed: function (n) { fixedSeed = n; },
    buttons: function () { return buttons().map(function (b) { return b[1]; }); }
  };
}

boot().catch(function (err) {
  document.body.append(el("p", "note", "The arena couldn't start: " + err.message));
});

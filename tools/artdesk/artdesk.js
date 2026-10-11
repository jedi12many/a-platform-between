// The art desk (docs/art.md): paints the game's figures, effects and tiles dot by dot,
// under the C64's rules, and saves them to content/art/ through tools/artdesk/serve.py.
//
// The rules hold by construction: a figure's dot is see-through, one of the sprites' two
// shared colours or its own; a tile's is the background, one of the tiles' two shared
// colours or its own (one of the first eight); a hires effect's is on or off. A
// multicolour dot is two pixels wide, as on the C64, and the previews show the art as
// the game shows it: on the C version's 32-pixel squares with its hires outline, and on
// the cartridge's 16-pixel ones with the outline drawn in (tools/battlegfx.py does the
// same when it builds them). The files are parsed and written here as tools/art.py reads
// them; the server checks a save against art.py before writing it.
"use strict";

const FILE_TITLES = { figures: "Figures", effects: "Effects", tiles32: "Tiles 32",
                      tiles16: "Tiles 16" };
const DOT_NAMES = {
  ".": "see-through", "a": "shared 1", "b": "shared 2", "c": "own", "#": "on",
  "k": "background", "d": "shared 1", "g": "shared 2", "o": "own",
};
const CART_OUTLINE = 0;              // the cartridge's sprites' first shared colour: black
const FIGURE_DX = -4, FIGURE_DY = -7;  // cart/mem.inc: a figure on its 16-pixel square
const PREVIEW_EFFECT = { hires: 1, multi: 3 };  // white, cyan: as the battle screen shows them

let META = null;
const files = {};                    // name -> {comments, header: [[key, ...values]], entries, dirty}
const state = { file: "figures", index: 0, dot: 1, tool: "pen", undo: {}, redo: {} };

// ------------------------------------------------------------------ the files

function parse(name, text) {
  const out = { comments: [], header: [], entries: [], dirty: false };
  const lines = text.split("\n");
  let notes = [];
  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i].replace(/\s+$/, "");
    if (!ln) continue;
    if (ln.startsWith("#")) {
      if (!out.entries.length && !out.header.length) out.comments.push(ln);
      else notes.push(ln);
      continue;
    }
    const words = ln.split(/\s+/);
    if (words[0] === "shared" || words[0] === "background") {
      out.header.push(words);
      continue;
    }
    const size = sizeOf(name, words[0], words[2]);
    const rows = lines.slice(i + 1, i + 1 + size.h);
    out.entries.push({ kind: words[0], name: words[1], option: words[2], rows, notes });
    notes = [];
    i += size.h;
  }
  return out;
}

function serialise(f) {
  let text = f.comments.map((c) => c + "\n").join("");
  text += f.header.map((h) => h.join(" ") + "\n").join("");
  for (const e of f.entries) {
    text += "\n" + e.notes.map((n) => n + "\n").join("");
    text += `${e.kind} ${e.name} ${e.option}\n` + e.rows.join("\n") + "\n";
  }
  return text;
}

function sizeOf(name, kind, option) {
  const kinds = META.files[name];
  return kinds[kind === "effect" ? `effect ${option}` : kind];
}

function headerColour(f, key, i) {
  const h = f.header.find((w) => w[0] === key);
  return h ? META.colours.indexOf(h[1 + i]) : 0;
}

// ------------------------------------------------------------------ what a dot shows

function current() { return files[state.file].entries[state.index]; }
function isMulti(e) { return e.kind !== "effect" || e.option === "multi"; }

// A colour (0-15, or null: see-through) for each dot an entry can have.
function colourMap(fileName, e, outlineBlack) {
  const f = files[fileName];
  const own = e.kind === "effect" ? PREVIEW_EFFECT[e.option] : META.colours.indexOf(e.option);
  if (e.kind === "tile") {
    return { k: headerColour(f, "background", 0), d: headerColour(f, "shared", 0),
             g: headerColour(f, "shared", 1), o: own };
  }
  const sprites = files.figures;
  return { ".": null, "#": own, c: own,
           a: outlineBlack ? CART_OUTLINE : headerColour(sprites, "shared", 0),
           b: headerColour(sprites, "shared", 1) };
}

function rgb(c) {
  const p = META.palette[c];
  return `rgb(${p[0]},${p[1]},${p[2]})`;
}

// Rows of dots onto a 2D context at pixel x, y (dot width 2 for multicolour), scale s.
function paintRows(ctx, rows, colours, multi, x, y, s) {
  const dw = multi ? 2 : 1;
  for (let j = 0; j < rows.length; j++) {
    for (let i = 0; i < rows[j].length; i++) {
      const c = colours[rows[j][i]];
      if (c === null || c === undefined) continue;
      ctx.fillStyle = rgb(c);
      ctx.fillRect((x + i * dw) * s, (y + j) * s, dw * s, s);
    }
  }
}

// ------------------------------------------------------------------ the build's own changes
// (tools/battlegfx.py: outline, outlined, fallen, marked, marked16, cursor16)

function solidSet(rows) {
  const solid = new Set();
  rows.slice(0, 21).forEach((r, y) => {
    for (let x = 0; x < 12; x++) {
      if ((r[x] || ".") !== ".") { solid.add(`${2 * x},${y}`); solid.add(`${2 * x + 1},${y}`); }
    }
  });
  return solid;
}

function outline(rows) {
  const solid = solidSet(rows);
  const out = [];
  for (let y = 0; y < 21; y++) {
    let r = "";
    for (let x = 0; x < 24; x++) {
      const edge = !solid.has(`${x},${y}`) && [[1, 0], [-1, 0], [0, 1], [0, -1]].some(
        ([dx, dy]) => solid.has(`${x + dx},${y + dy}`));
      r += edge ? "#" : ".";
    }
    out.push(r);
  }
  return out;
}

function outlined(rows) {
  const at = (x, y) => (y >= 0 && y < 21 && x >= 0 && x < 12 ? rows[y][x] : ".");
  return rows.map((r, y) => r.split("").map((c, x) => (
    c === "." && [[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => at(x + dx, y + dy) !== ".")
      ? "a" : c)).join(""));
}

function fallen(rows) {
  const used = rows.filter((r) => r.replace(/\./g, ""));
  const keep = [];
  for (let i = 0; i < 6 && used.length; i++) keep.push(used[Math.floor(i * used.length / 6)]);
  return Array(15).fill(".".repeat(12)).concat(keep);
}

function filled(rows, x0, y0, x1, y1, c) {
  return rows.map((r, y) => r.split("").map((d, x) => (
    x >= x0 && x <= x1 && y >= y0 && y <= y1 ? c : d)).join(""));
}

const marked32 = (rows) => filled(rows, 7, 14, 8, 17, "k");
const marked16 = (rows) => filled(rows, 3, 6, 4, 9, "k");

function cursor16(rows) {
  const at = { 0: [0, 1, 6, 7], 1: [0, 7], 2: [0, 7], 13: [0, 7], 14: [0, 7], 15: [0, 1, 6, 7] };
  return rows.map((r, y) => r.split("").map((d, x) => (at[y] && at[y].includes(x) ? "o" : d))
    .join(""));
}

// ------------------------------------------------------------------ the grid

const grid = document.getElementById("grid");
const gctx = grid.getContext("2d");
let zoom = 16;
let stroke = null;                   // {x0, y0, before} while a button is down

function layout() {
  const e = current();
  if (!e) return;
  const dw = isMulti(e) ? 2 : 1;
  const w = e.rows[0].length, h = e.rows.length;
  zoom = Math.max(4, Math.floor(Math.min(520 / (w * dw), 520 / h)));
  grid.width = w * dw * zoom;
  grid.height = h * zoom;
  grid.dataset.w = w;                // (its size in dots: for the tests)
  grid.dataset.h = h;
}

function drawGrid(preview) {
  const e = current();
  if (!e) return;
  const rows = preview || e.rows;
  const dw = isMulti(e) ? 2 : 1;
  const colours = colourMap(state.file, e, false);
  for (let y = 0; y < rows.length; y++) {          // see-through: a checkerboard
    for (let x = 0; x < rows[0].length; x++) {
      const c = colours[rows[y][x]];
      gctx.fillStyle = (c === null || c === undefined) ? ((x + y) % 2 ? "#26304a" : "#2e3a58")
                                                       : rgb(c);
      gctx.fillRect(x * dw * zoom, y * zoom, dw * zoom, zoom);
    }
  }
  gctx.strokeStyle = "rgba(0,0,0,.35)";              // the dots' edges, and the characters'
  gctx.lineWidth = 1;
  for (let x = 0; x <= rows[0].length; x++) {
    const cell = e.kind === "tile" && x % 4 === 0;
    gctx.strokeStyle = cell ? "rgba(232,197,71,.45)" : "rgba(0,0,0,.35)";
    gctx.beginPath(); gctx.moveTo(x * dw * zoom + .5, 0); gctx.lineTo(x * dw * zoom + .5, grid.height);
    gctx.stroke();
  }
  for (let y = 0; y <= rows.length; y++) {
    const cell = e.kind === "tile" && y % 8 === 0;
    gctx.strokeStyle = cell ? "rgba(232,197,71,.45)" : "rgba(0,0,0,.35)";
    gctx.beginPath(); gctx.moveTo(0, y * zoom + .5); gctx.lineTo(grid.width, y * zoom + .5);
    gctx.stroke();
  }
}

function dotAt(ev) {
  const e = current();
  const r = grid.getBoundingClientRect();
  const dw = isMulti(e) ? 2 : 1;
  const x = Math.floor((ev.clientX - r.left) * (grid.width / r.width) / (dw * zoom));
  const y = Math.floor((ev.clientY - r.top) * (grid.height / r.height) / zoom);
  if (x < 0 || y < 0 || x >= e.rows[0].length || y >= e.rows.length) return null;
  return { x, y };
}

function setDot(rows, x, y, c) {
  if (rows[y][x] === c) return rows;
  const out = rows.slice();
  out[y] = out[y].slice(0, x) + c + out[y].slice(x + 1);
  return out;
}

function lineDots(x0, y0, x1, y1) {
  const out = [];
  const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
  let err = dx + dy;
  for (;;) {
    out.push([x0, y0]);
    if (x0 === x1 && y0 === y1) return out;
    const e2 = 2 * err;
    if (e2 >= dy) { err += dy; x0 += sx; }
    if (e2 <= dx) { err += dx; y0 += sy; }
  }
}

function boxDots(x0, y0, x1, y1) {
  const out = [];
  const [a, b] = [Math.min(x0, x1), Math.max(x0, x1)];
  const [c, d] = [Math.min(y0, y1), Math.max(y0, y1)];
  for (let x = a; x <= b; x++) { out.push([x, c], [x, d]); }
  for (let y = c; y <= d; y++) { out.push([a, y], [b, y]); }
  return out;
}

function floodFill(rows, x, y, c) {
  const from = rows[y][x];
  if (from === c) return rows;
  const g = rows.map((r) => r.split(""));
  const todo = [[x, y]];
  while (todo.length) {
    const [i, j] = todo.pop();
    if (j < 0 || j >= g.length || i < 0 || i >= g[0].length || g[j][i] !== from) continue;
    g[j][i] = c;
    todo.push([i + 1, j], [i - 1, j], [i, j + 1], [i, j - 1]);
  }
  return g.map((r) => r.join(""));
}

function key() { return `${state.file}/${state.index}`; }

function commit(rows, before) {
  const e = current();
  if (rows.join() === before.join()) return;
  (state.undo[key()] = state.undo[key()] || []).push(before);
  state.redo[key()] = [];
  e.rows = rows;
  changed();
}

function changed() {
  files[state.file].dirty = true;
  drawAll();
  status("Not saved yet.", "");
}

grid.addEventListener("contextmenu", (ev) => ev.preventDefault());
grid.addEventListener("pointerdown", (ev) => {
  const at = dotAt(ev);
  if (!at) return;
  grid.setPointerCapture(ev.pointerId);
  const e = current();
  const dots = sizeOf(state.file, e.kind, e.option).dots;
  const c = ev.button === 2 ? dots[0] : dots[state.dot];
  if (state.tool === "pick") {
    state.dot = dots.indexOf(e.rows[at.y][at.x]);
    drawDots();
    return;
  }
  if (state.tool === "fill") {
    commit(floodFill(e.rows, at.x, at.y, c), e.rows);
    return;
  }
  stroke = { x0: at.x, y0: at.y, last: at, c, before: e.rows, rows: setDot(e.rows, at.x, at.y, c) };
  drawGrid(stroke.rows);
});
grid.addEventListener("pointermove", (ev) => {
  const at = dotAt(ev);
  document.getElementById("where").textContent = at ? `${at.x}, ${at.y}` : " ";
  if (!stroke || !at) return;
  const e = current();
  if (state.tool === "pen") {
    for (const [x, y] of lineDots(stroke.last.x, stroke.last.y, at.x, at.y)) {
      stroke.rows = setDot(stroke.rows, x, y, stroke.c);
    }
  } else {
    stroke.rows = e.rows;
    const shape = state.tool === "line" ? lineDots : boxDots;
    for (const [x, y] of shape(stroke.x0, stroke.y0, at.x, at.y)) {
      stroke.rows = setDot(stroke.rows, x, y, stroke.c);
    }
  }
  stroke.last = at;
  drawGrid(stroke.rows);
});
grid.addEventListener("pointerup", () => {
  if (!stroke) return;
  const s = stroke;
  stroke = null;
  commit(s.rows, s.before);
  drawGrid();
});

// ------------------------------------------------------------------ the side panels

function el(tag, attrs, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "on") for (const [ev, fn] of Object.entries(v)) n.addEventListener(ev, fn);
    else if (k === "text") n.textContent = v;
    else n.setAttribute(k, v);
  }
  for (const k of kids) n.append(k);
  return n;
}

function drawFiles() {
  const nav = document.getElementById("files");
  nav.replaceChildren(...Object.keys(FILE_TITLES).map((name) => el("button", {
    type: "button", "data-file": name, "aria-pressed": String(name === state.file),
    class: files[name].dirty ? "dirty" : "", text: FILE_TITLES[name],
    on: { click: () => { state.file = name; state.index = 0; drawAll(); } } })));
}

function thumb(fileName, e) {
  const c = el("canvas");
  const multi = isMulti(e);
  const w = e.rows[0].length * (multi ? 2 : 1), h = e.rows.length;
  const s = Math.max(1, Math.floor(40 / Math.max(w, h)));
  c.width = w * s; c.height = h * s;
  paintRows(c.getContext("2d"), e.rows, colourMap(fileName, e, false), multi, 0, 0, s);
  return c;
}

function drawList() {
  const f = files[state.file];
  const list = document.getElementById("entry-list");
  list.replaceChildren(...f.entries.map((e, i) => {
    let tag = "";
    if (e.kind === "tile") tag = i < 8 ? "terrain" : "scenery";
    if (e.kind === "effect") tag = e.option;
    return el("li", { "data-name": e.name, "aria-selected": String(i === state.index),
                      on: { click: () => { state.index = i; drawAll(); } } },
              thumb(state.file, e), el("span", { text: e.name }), el("span", { class: "tag", text: tag }));
  }));
  const terrain = state.file.startsWith("tiles") && state.index < 8;
  document.getElementById("rename").disabled = terrain;
  document.getElementById("delete").disabled = terrain;
  // What the game needs that isn't here.
  const needs = document.getElementById("needs");
  needs.className = "note";
  needs.textContent = "";
  if (state.file === "figures") {
    const want = META.races.concat(["STRANGER"], META.foes);
    const have = f.entries.map((e) => e.name);
    const missing = want.filter((n) => !have.includes(n));
    const extra = have.filter((n) => !want.includes(n));
    if (missing.length) {
      needs.className = "note bad";
      needs.textContent = `The game needs a figure for ${missing.join(", ")}.`;
    } else if (extra.length) {
      needs.textContent = `${extra.join(", ")}: not a race or foe yet, so the game won't show it.`;
    } else {
      needs.textContent = "Every race and foe has its figure.";
    }
  } else if (state.file.startsWith("tiles")) {
    needs.textContent = "The first eight are the rules' terrain. Tiles after them are " +
      "scenery, for rooms to come: kept and checked, not yet in the game.";
  }
}

function drawHeader() {
  const f = files[state.file];
  const box = document.getElementById("header-colours");
  const rows = [];
  for (const h of f.header) {
    h.slice(1).forEach((c, i) => {
      const label = h[0] === "background" ? "Background" : `Shared ${i + 1}`;
      const sel = el("select", { "data-header": `${h[0]}:${i}`, on: { change: (ev) => {
        h[1 + i] = ev.target.value; changed(); } } });
      META.colours.forEach((name) => sel.append(el("option", { value: name, text: name })));
      sel.value = c;
      rows.push(el("label", { class: "header-colour" }, el("span", { text: label }), sel));
    });
  }
  const what = state.file === "figures" || state.file === "effects"
    ? "the sprites' colours (the cartridge makes Shared 1 black, an outline, and sets " +
      "Shared 2 itself)"
    : state.file === "tiles16" ? "every tile's colours (the cartridge sets these itself, in " +
      "cart/screen.s: change them there too)" : "every tile's colours";
  box.replaceChildren(el("h2", { text: `${FILE_TITLES[state.file]}: ${what}` }), ...rows);
}

function drawDots() {
  const e = current();
  const box = document.getElementById("dots");
  if (!e) { box.replaceChildren(); return; }
  const dots = sizeOf(state.file, e.kind, e.option).dots;
  const colours = colourMap(state.file, e, false);
  box.replaceChildren(...dots.split("").map((d, i) => {
    const c = colours[d];
    const chip = el("span", { class: "chip" + (c === null ? " clear" : "") });
    if (c !== null) chip.style.background = rgb(c);
    return el("button", { type: "button", "data-dot": d, "aria-pressed": String(i === state.dot),
                          title: `${DOT_NAMES[d]} (${i + 1})`,
                          on: { click: () => { state.dot = i; drawDots(); } } },
              chip, el("span", { text: `${i + 1}` }));
  }));
  document.querySelectorAll("[data-tool]").forEach((b) =>
    b.setAttribute("aria-pressed", String(b.dataset.tool === state.tool)));
}

function drawOwn() {
  const e = current();
  const box = document.getElementById("own-colour");
  document.getElementById("entry-title").textContent = e ? `${e.kind} ${e.name}` : " ";
  if (!e || e.kind === "effect") {
    box.replaceChildren(el("p", { class: "note", text: e ? `A ${e.option} effect: shown in ` +
      `${META.colours[PREVIEW_EFFECT[e.option]]} here; the battle screen colours it.` : "" }));
    return;
  }
  const limit = e.kind === "tile" ? 8 : 16;
  const sw = el("div", { class: "swatches", role: "group", "aria-label": "Its own colour" });
  META.colours.forEach((name, i) => {
    const b = el("button", { type: "button", "data-colour": name, title: name,
                             "aria-pressed": String(e.option === name),
                             on: { click: () => { e.option = name; changed(); } } });
    b.style.background = rgb(i);
    if (i >= limit) b.disabled = true;
    sw.append(b);
  });
  box.replaceChildren(el("p", { class: "note", text: e.kind === "tile"
    ? "Its own colour (a multicolour cell's: one of the first eight)" : "Its own colour" }), sw);
}

// ------------------------------------------------------------------ the previews

function canvasOf(w, h, s) {
  const c = el("canvas");
  c.width = w * s; c.height = h * s;
  return c;
}

function tileRows(fileName, name) {
  const t = files[fileName].entries.find((e) => e.name === name);
  return t || files[fileName].entries[0];
}

function drawTile(ctx, fileName, t, rows, x, y, s, own) {
  const colours = colourMap(fileName, t, false);
  if (own !== undefined) colours.o = own;
  paintRows(ctx, rows || t.rows, colours, true, x, y, s);
}

function previewFigure(e) {
  const out = [];
  // The C version: 32-pixel squares, the body and its hires outline over it.
  const floor32 = tileRows("tiles32", "open");
  let c = canvasOf(64, 32, 3);
  let ctx = c.getContext("2d");
  drawTile(ctx, "tiles32", floor32, null, 0, 0, 3);
  drawTile(ctx, "tiles32", floor32, null, 32, 0, 3);
  const colours = colourMap("figures", e, false);
  const black = { "#": 0, ".": null };
  paintRows(ctx, e.rows, colours, true, 4, 6, 3);
  paintRows(ctx, outline(e.rows), black, false, 4, 6, 3);
  const down = fallen(e.rows);
  paintRows(ctx, down, colours, true, 36, 6, 3);
  paintRows(ctx, outline(down), black, false, 36, 6, 3);
  out.push(el("figure", {}, el("figcaption", { text: "The C version (C64, desktop, browser): " +
    "standing, and down" }), c));
  // The cartridge: 16-pixel squares, the outline drawn in, Shared 1 black.
  const floor16 = tileRows("tiles16", "open");
  c = canvasOf(64, 32, 3);
  ctx = c.getContext("2d");
  for (let y = 0; y < 2; y++) for (let x = 0; x < 4; x++) drawTile(ctx, "tiles16", floor16, null, x * 16, y * 16, 3);
  const cart = colourMap("figures", e, true);                // on squares (1, 1) and (3, 1)
  paintRows(ctx, outlined(e.rows), cart, true, 16 + FIGURE_DX, 16 + FIGURE_DY, 3);
  paintRows(ctx, outlined(fallen(e.rows)), cart, true, 48 + FIGURE_DX, 16 + FIGURE_DY, 3);
  out.push(el("figure", {}, el("figcaption", { text: "The cartridge: standing, and down" }), c));
  return out;
}

function previewTile(e) {
  const out = [];
  const small = state.file === "tiles16";
  const w = small ? 16 : 32;
  const s = small ? 4 : 2;
  let c = canvasOf(w * 3, w * 3, small ? 2 : 1);
  let ctx = c.getContext("2d");
  for (let y = 0; y < 3; y++) for (let x = 0; x < 3; x++) drawTile(ctx, state.file, e, null, x * w, y * w, small ? 2 : 1);
  out.push(el("figure", {}, el("figcaption", { text: "Side by side" }), c));
  c = canvasOf(w * (small ? 3 : 2), w, s);
  ctx = c.getContext("2d");
  drawTile(ctx, state.file, e, null, 0, 0, s);
  drawTile(ctx, state.file, e, (small ? marked16 : marked32)(e.rows), w, 0, s);
  if (small) drawTile(ctx, state.file, e, cursor16(e.rows), 2 * w, 0, s, 7);
  out.push(el("figure", {}, el("figcaption", { text: small
    ? "Plain, a square you can reach, the cursor on it" : "Plain, and a square you can reach" }), c));
  return out;
}

function previewEffect(e) {
  const floor32 = tileRows("tiles32", "open");
  const c = canvasOf(32, 32, 4);
  const ctx = c.getContext("2d");
  drawTile(ctx, "tiles32", floor32, null, 0, 0, 4);
  paintRows(ctx, e.rows, colourMap("effects", e, false), isMulti(e), 4, 6, 4);
  return [el("figure", {}, el("figcaption", { text: "On a square (the C version's)" }), c)];
}

function drawPreviews() {
  const e = current();
  const box = document.getElementById("previews");
  if (!e) { box.replaceChildren(); return; }
  box.replaceChildren(...(e.kind === "figure" ? previewFigure(e)
    : e.kind === "tile" ? previewTile(e) : previewEffect(e)));
}

function drawAll() {
  const f = files[state.file];
  state.index = Math.min(state.index, f.entries.length - 1);
  drawFiles();
  drawHeader();
  drawList();
  drawDots();
  drawOwn();
  layout();
  drawGrid();
  drawPreviews();
}

// ------------------------------------------------------------------ commands

function status(text, kind) {
  const s = document.getElementById("status");
  s.textContent = text;
  s.className = kind || "";
}

// On the published site (docs/art.md) there's no server to save into the game's files: Save
// downloads each changed file instead, to send in. In the studio (make studio) it saves.
let PUBLISHED = false;

function download(name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([serialise(files[name])], { type: "text/plain" }));
  a.download = `${name}.txt`;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

async function save() {
  const dirty = Object.keys(files).filter((n) => files[n].dirty);
  if (!dirty.length) { status("Nothing to save.", ""); return; }
  if (PUBLISHED) {
    dirty.forEach(download);
    dirty.forEach((n) => { files[n].dirty = false; });
    status(`Downloaded ${dirty.map((n) => `${n}.txt`).join(", ")}: send it in to put it in the game.`, "good");
    drawFiles();
    return;
  }
  for (const name of dirty) {
    const r = await fetch(`art/${name}.txt`, { method: "PUT", body: serialise(files[name]) });
    const said = await r.text();
    if (!r.ok) {
      status(`Not saved: ${said}`, "bad");
      return;
    }
    files[name].dirty = false;
  }
  status(`Saved ${dirty.map((n) => `${n}.txt`).join(", ")}.`, "good");
  drawFiles();
}

async function load(name) {
  const r = await fetch(`art/${name}.txt`, { cache: "no-store" });
  files[name] = parse(name, await r.text());
}

function nameOk(n) {
  const f = files[state.file];
  if (!/^[A-Za-z0-9_]+$/.test(n || "")) {
    status("A name is letters, digits and _, no spaces.", "bad");
    return false;
  }
  if (f.entries.some((e) => e.name === n)) {
    status(`There's already a ${n}.`, "bad");
    return false;
  }
  return true;
}

function blankEntry(kind, option, name) {
  const size = sizeOf(state.file, kind, option);
  return { kind, name, option, notes: [], rows: Array(size.h).fill(size.dots[0].repeat(size.w)) };
}

document.getElementById("new").addEventListener("click", () => {
  const f = files[state.file];
  const proto = f.entries[0];
  const upper = state.file === "figures" || state.file === "effects";
  const n = prompt(upper ? "Its name (as the registry has it: MAINT_DRONE)" : "Its name (crate)");
  if (n === null) return;
  const name = upper ? n.trim().toUpperCase() : n.trim().toLowerCase();
  if (!nameOk(name)) return;
  const option = proto.kind === "effect" ? proto.option : proto.kind === "tile" ? "black" : "grey";
  f.entries.push(blankEntry(proto.kind, option, name));
  state.index = f.entries.length - 1;
  changed();
});
document.getElementById("duplicate").addEventListener("click", () => {
  const f = files[state.file];
  const e = current();
  const n = prompt("The copy's name", `${e.name}_2`);
  if (n === null || !nameOk(n.trim())) return;
  f.entries.push({ ...e, name: n.trim(), notes: [], rows: e.rows.slice() });
  state.index = f.entries.length - 1;
  changed();
});
document.getElementById("rename").addEventListener("click", () => {
  const e = current();
  const n = prompt("Its new name", e.name);
  if (n === null || n.trim() === e.name || !nameOk(n.trim())) return;
  e.name = n.trim();
  changed();
});
document.getElementById("delete").addEventListener("click", () => {
  const f = files[state.file];
  const e = current();
  if (!confirm(`Delete ${e.name}?`)) return;
  f.entries.splice(state.index, 1);
  state.index = Math.max(0, state.index - 1);
  changed();
});
document.getElementById("save").addEventListener("click", save);
document.getElementById("revert").addEventListener("click", async () => {
  if (!confirm("Throw away everything that isn't saved?")) return;
  for (const n of Object.keys(files)) await load(n);
  state.undo = {}; state.redo = {};
  drawAll();
  status("Back to what's saved.", "");
});
document.querySelectorAll("[data-tool]").forEach((b) => b.addEventListener("click", () => {
  state.tool = b.dataset.tool; drawDots(); }));

function transform(fn) {
  const e = current();
  commit(fn(e.rows), e.rows);
}
document.getElementById("flip").addEventListener("click", () =>
  transform((rows) => rows.map((r) => r.split("").reverse().join(""))));
document.getElementById("clear").addEventListener("click", () => {
  const e = current();
  const d = sizeOf(state.file, e.kind, e.option).dots[0];
  transform((rows) => rows.map((r) => d.repeat(r.length)));
});
document.querySelectorAll("[data-shift]").forEach((b) => b.addEventListener("click", () => {
  const [dx, dy] = b.dataset.shift.split(",").map(Number);
  transform((rows) => {
    const h = rows.length, w = rows[0].length;
    return rows.map((r, y) => Array.from({ length: w }, (_, x) =>
      rows[(y - dy + h) % h][(x - dx + w) % w]).join(""));
  });
}));

function undo(from, to) {
  const k = key();
  const stack = (state[from][k] || []);
  if (!stack.length) return;
  const e = current();
  (state[to][k] = state[to][k] || []).push(e.rows);
  e.rows = stack.pop();
  changed();
}
document.getElementById("undo").addEventListener("click", () => undo("undo", "redo"));
document.getElementById("redo").addEventListener("click", () => undo("redo", "undo"));

document.addEventListener("keydown", (ev) => {
  if (ev.target.closest("input, select, textarea")) return;
  const k = ev.key.toLowerCase();
  if ((ev.ctrlKey || ev.metaKey) && k === "s") { ev.preventDefault(); save(); return; }
  if ((ev.ctrlKey || ev.metaKey) && k === "z") { ev.preventDefault(); undo("undo", "redo"); return; }
  if ((ev.ctrlKey || ev.metaKey) && k === "y") { ev.preventDefault(); undo("redo", "undo"); return; }
  if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
  const tools = { p: "pen", l: "line", b: "box", f: "fill", i: "pick" };
  if (tools[k]) { state.tool = tools[k]; drawDots(); return; }
  const e = current();
  const n = Number(ev.key);
  if (e && n >= 1 && n <= sizeOf(state.file, e.kind, e.option).dots.length) {
    state.dot = n - 1;
    drawDots();
  }
});
window.addEventListener("beforeunload", (ev) => {
  if (Object.values(files).some((f) => f.dirty)) { ev.preventDefault(); ev.returnValue = ""; }
});

// ------------------------------------------------------------------ pasting art as text
// Art drawn elsewhere, pasted as a grid of characters: a line before the grid is its name,
// a line "colour: red" its own colour; each character is mapped to one of the entry's
// dots, and the grid fitted to the entry's size (feet on the bottom row for a figure,
// centred otherwise): trimmed at the edges of what's drawn, or squeezed in.

const BACKGROUND_CHARS = "0. k";      // characters taken for see-through (or background) first
const paste = { grid: null, name: "", colour: null, map: {} };

function readPasted(text) {
  const lines = text.split(/\r?\n/).map((l) => l.replace(/\s+$/, ""));
  let colour = null;
  const rest = [];
  for (const ln of lines) {
    const m = ln.match(/^\s*colou?r\s*[:=]\s*(\w+)\s*$/i);
    if (m) colour = m[1].toLowerCase();
    else rest.push(ln);
  }
  // The grid: the longest run of lines all the same length (2 lines at least).
  let best = null;
  for (let i = 0; i < rest.length;) {
    let j = i;
    while (j < rest.length && rest[j].length && rest[j].length === rest[i].length) j++;
    if (j - i >= 2 && (!best || j - i > best[1] - best[0])) best = [i, j];
    i = j > i ? j : i + 1;
  }
  if (!best) return { grid: null, name: "", colour };
  const named = rest.slice(0, best[0]).map((l) => l.trim()).filter(Boolean);
  let name = named.length ? named[named.length - 1] : "";
  const header = name.split(/\s+/);       // an art file's own "figure NAME colour" line
  if (header.length === 3 && /^(figure|tile|effect)$/.test(header[0])) {
    name = header[1];
    if (header[0] !== "effect") colour = colour || header[2];
  }
  return { grid: rest.slice(best[0], best[1]), name: name.replace(/\W+/g, "_"), colour };
}

// The characters in the grid, background-like ones first, then in order.
function pastedChars(grid) {
  const seen = [...new Set(grid.join(""))];
  const bg = seen.filter((c) => BACKGROUND_CHARS.includes(c))
    .sort((a, b) => BACKGROUND_CHARS.indexOf(a) - BACKGROUND_CHARS.indexOf(b));
  return bg.concat(seen.filter((c) => !bg.includes(c)).sort());
}

function pasteTarget() {
  const into = document.querySelector('input[name="paste-into"]:checked').value;
  const e = current();
  if (into === "this" && e) return e;
  const proto = files[state.file].entries[0];
  return { kind: proto.kind, option: proto.kind === "effect" ? proto.option
    : proto.kind === "tile" ? "black" : "grey" };
}

// Columns (or rows) to keep, n of them, from `have` (indexes of what's drawn, in order),
// with the grid `size` wide: trimmed evenly at both ends, or squeezed (every so many kept).
function fitIndexes(have, size, n, how, bottom) {
  const lo = have.length ? have[0] : 0, hi = have.length ? have[have.length - 1] : size - 1;
  const span = hi - lo + 1;
  if (span <= n) {                       // what's drawn fits: a window round it
    let start = bottom ? hi - n + 1 : lo - Math.floor((n - span) / 2);
    return Array.from({ length: n }, (_, i) => start + i);
  }
  if (how === "squeeze") {
    return Array.from({ length: n }, (_, i) => lo + Math.floor((i + 0.5) * span / n));
  }
  const cut = span - n;
  const start = bottom ? hi - n + 1 : lo + Math.floor(cut / 2);
  return Array.from({ length: n }, (_, i) => start + i);
}

// The pasted grid as the target's rows, and what was given up to get there.
function pastedRows(target) {
  const size = sizeOf(state.file, target.kind, target.option);
  const grid = paste.grid;
  const w = Math.max(...grid.map((r) => r.length));
  const at = (x, y) => (y >= 0 && y < grid.length && x >= 0 && x < w ? grid[y][x] || " " : null);
  const blank = (c) => c === null || paste.map[c] === size.dots[0];
  const how = document.getElementById("paste-fit").value;
  const cols = [], rows = [];
  for (let x = 0; x < w; x++) if (grid.some((r, y) => !blank(at(x, y)))) cols.push(x);
  for (let y = 0; y < grid.length; y++) if ([...Array(w).keys()].some((x) => !blank(at(x, y)))) rows.push(y);
  const xs = fitIndexes(cols, w, size.w, how, false);
  const ys = fitIndexes(rows, grid.length, size.h, how, target.kind === "figure");
  const out = ys.map((y) => xs.map((x) => {
    const c = at(x, y);
    return c === null ? size.dots[0] : paste.map[c];
  }).join(""));
  const notes = [`${w} x ${grid.length} pasted; what's drawn is ${cols.length ? cols[cols.length - 1] - cols[0] + 1 : 0}`
    + ` x ${rows.length ? rows[rows.length - 1] - rows[0] + 1 : 0}; ${target.kind === "effect" ? `a ${target.option} effect` : `a ${target.kind}`} is ${size.w} x ${size.h}.`];
  for (const [list, n, what] of [[cols, size.w, "columns"], [rows, size.h, "rows"]]) {
    const span = list.length ? list[list.length - 1] - list[0] + 1 : 0;
    if (span > n) notes.push(how === "squeeze" ? `${span} ${what} squeezed into ${n}.`
      : `${span - n} ${what} trimmed${what === "rows" && target.kind === "figure" ? " off the top (feet on the bottom row)" : ", from both edges"}.`);
  }
  const by = {};
  for (const [c, d] of Object.entries(paste.map)) (by[d] = by[d] || []).push(c);
  for (const [d, cs] of Object.entries(by)) {
    if (cs.length > 1) notes.push(`${cs.slice(0, -1).join(", ")} and ${cs[cs.length - 1]} ${cs.length > 2 ? "all" : "both"} become ${dotLabel(target, d)}.`);
  }
  return { rows: out, notes };
}

// A dot's name, and the colour it is in this entry: "shared 1: dgrey".
function dotLabel(target, d) {
  const c = colourMap(state.file, target, false)[d];
  return c === null || c === undefined ? DOT_NAMES[d] : `${DOT_NAMES[d]}: ${META.colours[c]}`;
}

function drawPaste() {
  const box = document.getElementById("paste-map");
  const apply = document.getElementById("paste-apply");
  const notes = document.getElementById("paste-notes");
  const preview = document.getElementById("paste-preview");
  const target = { ...pasteTarget() };
  const size = sizeOf(state.file, target.kind, target.option);
  const said = [];
  if (paste.colour && target.kind !== "effect" && into() === "new") {   // its own colour
    const i = META.colours.indexOf(paste.colour);
    if (i >= 0 && (target.kind !== "tile" || i < 8)) target.option = paste.colour;
    else said.push(`"${paste.colour}" isn't a colour it can have: ${target.option} instead.`);
  }
  if (!paste.grid) {
    box.replaceChildren();
    preview.replaceChildren();
    notes.replaceChildren(el("li", { text: "Paste a grid: two rows or more, all the same length." }));
    apply.disabled = true;
    return;
  }
  const chars = pastedChars(paste.grid);
  chars.forEach((c, i) => {
    if (!size.dots.includes(paste.map[c])) paste.map[c] = size.dots[Math.min(i, size.dots.length - 1)];
  });
  for (const c of Object.keys(paste.map)) if (!chars.includes(c)) delete paste.map[c];
  box.replaceChildren(...chars.map((c) => el("label", {},
    el("code", { text: c === " " ? "␠" : c }), "→",
    el("select", { "data-char": c, "aria-label": `What ${c} becomes`, on: { change: (ev) => {
      paste.map[c] = ev.target.value; drawPaste(); } } },
      ...[...size.dots].map((d) => {
        const o = el("option", { value: d, text: dotLabel(target, d) });
        if (paste.map[c] === d) o.selected = true;
        return o;
      })))));
  const fitted = pastedRows(target);
  const rows = fitted.rows;
  said.unshift(...fitted.notes);
  const shown = { ...target, rows };
  const multi = isMulti(shown), s = 6;
  const cv = canvasOf(size.w * (multi ? 2 : 1), size.h, s);
  paintRows(cv.getContext("2d"), rows, colourMap(state.file, shown, false), multi, 0, 0, s);
  preview.replaceChildren(cv);
  paste.result = shown;
  notes.replaceChildren(...said.map((t) => el("li", { text: t })));
  apply.disabled = false;
}

function into() { return document.querySelector('input[name="paste-into"]:checked').value; }

document.getElementById("paste").addEventListener("click", () => {
  const e = current();
  document.getElementById("paste-this").textContent = e ? e.name : "(nothing open)";
  document.querySelector('input[name="paste-into"][value="this"]').disabled = !e;
  drawPaste();
  document.getElementById("paste-dialog").showModal();
  document.getElementById("paste-text").focus();
});
document.getElementById("paste-text").addEventListener("input", (ev) => {
  const r = readPasted(ev.target.value);
  paste.grid = r.grid;
  paste.colour = r.colour;
  const upper = state.file === "figures" || state.file === "effects";
  if (r.name) document.getElementById("paste-name").value = upper ? r.name.toUpperCase()
    : r.name.toLowerCase();
  paste.map = {};
  drawPaste();
});
document.querySelectorAll('input[name="paste-into"], #paste-fit').forEach((n) =>
  n.addEventListener("change", drawPaste));
document.getElementById("paste-dialog").addEventListener("close", () => {
  const dlg = document.getElementById("paste-dialog");
  if (dlg.returnValue !== "apply" || !paste.result) return;
  const f = files[state.file];
  if (into() === "this") {
    const e = current();
    if (paste.result.option !== e.option) e.option = paste.result.option;
    commit(paste.result.rows, e.rows);
    status(`Pasted into ${e.name}: not saved yet.`, "");
    return;
  }
  const upper = state.file === "figures" || state.file === "effects";
  const raw = document.getElementById("paste-name").value.trim();
  const name = upper ? raw.toUpperCase() : raw.toLowerCase();
  if (!nameOk(name)) return;
  f.entries.push({ kind: paste.result.kind, name, option: paste.result.option, notes: [],
                   rows: paste.result.rows });
  state.index = f.entries.length - 1;
  changed();
  status(`Pasted as ${name}: not saved yet.`, "");
});

// For the tests (tests/artdesk/): the text a file would be saved as.
window.artdesk = { serialise: (name) => serialise(files[name]), ready: false };

if (window.top !== window) document.documentElement.classList.add("framed");

(async () => {
  // build.json comes with the published site (make site); the studio's server has none.
  try {
    const b = await fetch("build.json", { cache: "no-store" });
    PUBLISHED = b.ok && (await b.json()).built !== "studio";
  } catch (e) { PUBLISHED = false; }
  if (PUBLISHED) {
    document.getElementById("save").textContent = "Download";
    document.getElementById("save").title = "Download the changed files, to send in (Ctrl+S)";
  }
  META = await (await fetch("meta.json")).json();
  for (const name of Object.keys(FILE_TITLES)) await load(name);
  state.dot = 1;
  drawAll();
  status("Ready.", "");
  window.artdesk.ready = true;
})();

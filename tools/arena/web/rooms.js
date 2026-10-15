/* Exploring (docs/rooms.md, milestone E13's prototype): a floor of rooms from a yard, walked
 * overhead, one room to a screen; coming into a room with foes in it starts a fight on the
 * room's own map, played by the arena's fight (arena.js) on rules v1.
 *
 * The first half builds a floor (docs/rooms.md, "A floor, from a yard"), the same as the
 * reference tools/rooms/rooms.py (tests/rooms/check_rooms.py holds them together); it runs
 * in Node too. The second half is the page's explore mode.
 */
"use strict";

/* ------------------------------------------------------------- building a floor */

var ROOMS = (function () {
  var COLS = 3, ROWS = 3, W = 16, H = 8;
  var DIRS = [["N", 0, -1], ["E", 1, 0], ["S", 0, 1], ["W", -1, 0]];
  var BACK = { N: "S", E: "W", S: "N", W: "E" };
  var TERRAIN = [3, 3, 4, 4, 6, 2, 1, 5];        /* rough, rough, cover, cover, high, pit, wall, hazard */
  var POOL = ["ASH_RAT", "SCRAP_GUNNER", "RUST_GUARD", "MAINT_DRONE"];
  var CACHE = ["IRON_SWORD", "ARC_PISTOL", "CHAIN_COAT", "PULSE_RIFLE", "BALLISTIC_WEAVE"];
  var STAIRS = [7, 3];
  var STANDS = [0, 3, 4, 6];                     /* open, rough, cover, high ground */

  function xs(x) {
    x ^= (x << 7) & 0xFFFF;
    x ^= x >> 9;
    x ^= (x << 8) & 0xFFFF;
    return x;
  }

  /* The Deep Yards' mixing (docs/deep-yards.md). */
  function mix(yard, key) {
    var x = yard || 0xACE1, k;
    for (k = 0; k < 3; ++k) {
      x = xs(x);
      x = (x * 0x9E37 + key) % 65536 || 0xACE1;
    }
    return xs(x);
  }

  function next(i, d) {
    var cx = i % COLS, cy = Math.floor(i / COLS), s = DIRS.filter(function (q) { return q[0] === d; })[0];
    var nx = cx + s[1], ny = cy + s[2];
    return nx >= 0 && nx < COLS && ny >= 0 && ny < ROWS ? ny * COLS + nx : -1;
  }

  /* Squares reachable from (sx, sy), 8 ways, round walls, pits and hazards: "x,y" keys. */
  function reach(tiles, sx, sy) {
    var seen = {}, todo = [[sx, sy]], p, dx, dy, nx, ny;
    seen[sx + "," + sy] = 1;
    while (todo.length) {
      p = todo.pop();
      for (dx = -1; dx <= 1; ++dx) {
        for (dy = -1; dy <= 1; ++dy) {
          nx = p[0] + dx; ny = p[1] + dy;
          if (nx < 0 || ny < 0 || nx >= W || ny >= H || seen[nx + "," + ny]) continue;
          if (tiles[ny][nx] === 1 || tiles[ny][nx] === 2 || tiles[ny][nx] === 5) continue;
          seen[nx + "," + ny] = 1;
          todo.push([nx, ny]);
        }
      }
    }
    return seen;
  }

  function build(yard, floor) {
    var state = mix((yard ^ 0x5A5A) & 0xFFFF, (floor * 256 + 255) % 65536);
    var n = COLS * ROWS, doors = [], i, d, k, c, opts, stack, seen, depth, queue, stairs, rooms = [];
    function r(m) { state = xs(state); return state % m; }
    function open(a, dir) { doors[a][dir] = null; doors[next(a, dir)][BACK[dir]] = null; }
    function has(a, dir) { return Object.prototype.hasOwnProperty.call(doors[a], dir); }

    for (i = 0; i < n; ++i) doors.push({});
    var start = r(3) * COLS;
    stack = [start]; seen = {}; seen[start] = 1;
    while (stack.length) {
      c = stack[stack.length - 1];
      opts = DIRS.map(function (q) { return q[0]; })
        .filter(function (dir) { return next(c, dir) >= 0 && !seen[next(c, dir)]; });
      if (!opts.length) { stack.pop(); continue; }
      d = opts[r(opts.length)];
      open(c, d);
      seen[next(c, d)] = 1;
      stack.push(next(c, d));
    }
    for (k = 0; k < 2; ++k) {
      i = r(n); d = DIRS[r(4)][0];
      if (next(i, d) >= 0 && !has(i, d)) open(i, d);
    }
    depth = {}; depth[start] = 0; queue = [start];
    while (queue.length) {
      c = queue.shift();
      DIRS.forEach(function (q) {
        if (has(c, q[0]) && depth[next(c, q[0])] === undefined) {
          depth[next(c, q[0])] = depth[c] + 1;
          queue.push(next(c, q[0]));
        }
      });
    }
    stairs = 0;
    for (i = 1; i < n; ++i) if (depth[i] > depth[stairs]) stairs = i;
    for (i = 0; i < n; ++i) {
      if (has(i, "E")) { k = 1 + r(6); doors[i].E = [W - 1, k]; doors[next(i, "E")].W = [0, k]; }
      if (has(i, "S")) { k = 1 + r(14); doors[i].S = [k, H - 1]; doors[next(i, "S")].N = [k, 0]; }
    }

    for (i = 0; i < n; ++i) {
      var tiles = [], x, y, t, sides, first, must, got, kind, foes = [], cache = null, here = i === stairs ? STAIRS : null;
      for (y = 0; y < H; ++y) {
        tiles.push([]);
        for (x = 0; x < W; ++x) tiles[y].push(x === 0 || y === 0 || x === W - 1 || y === H - 1 ? 1 : 0);
      }
      sides = DIRS.map(function (q) { return q[0]; }).filter(function (dir) { return has(i, dir); });
      sides.forEach(function (dir) { tiles[doors[i][dir][1]][doors[i][dir][0]] = 7; });
      first = doors[i][sides[0]];
      must = sides.map(function (dir) { return doors[i][dir]; }).concat(here ? [here] : []);
      for (k = 3 + r(4) + Math.min(depth[i], 3); k > 0; --k) {
        x = 2 + r(12); y = 2 + r(4); t = TERRAIN[r(8)];
        if (tiles[y][x] !== 0 || (here && x === here[0] && y === here[1])) continue;
        tiles[y][x] = t;
        got = reach(tiles, first[0], first[1]);
        if (!must.every(function (m) { return got[m[0] + "," + m[1]]; })) tiles[y][x] = 0;
      }
      got = reach(tiles, first[0], first[1]);
      kind = i === start ? "start" : i === stairs ? "stairs" : ["fight", "fight", "fight", "cache", "empty", "empty"][r(6)];

      var square = function (far) {
        var tries, sx, sy;
        function fits(px, py, nearOk) {
          return STANDS.indexOf(tiles[py][px]) >= 0 && got[px + "," + py] &&
            !(here && px === here[0] && py === here[1]) &&
            !foes.some(function (f) { return f.x === px && f.y === py; }) &&
            (nearOk || sides.every(function (dir) {
              var q = doors[i][dir];
              return Math.max(Math.abs(px - q[0]), Math.abs(py - q[1])) >= 3;
            }));
        }
        for (tries = 0; tries < 32; ++tries) {
          sx = 2 + r(12); sy = 1 + r(6);
          if (fits(sx, sy, !far)) return [sx, sy];
        }
        for (sy = 1; sy < 7; ++sy) for (sx = 2; sx < 14; ++sx) if (fits(sx, sy, true)) return [sx, sy];
        return null;
      };

      if (kind === "fight" || kind === "stairs") {
        var g = floor + Math.floor(depth[i] / 2);
        var count = Math.min(4, 1 + Math.floor(g / 3) + (kind === "stairs" ? 1 : 0));
        var L = Math.min(4, 1 + Math.floor(g / 2));
        for (k = 0; k < count; ++k) {
          var name = POOL[r(L)], at = square(true);
          if (at) foes.push({ name: name, x: at[0], y: at[1] });
        }
      } else if (kind === "cache") {
        var item = CACHE[r(CACHE.length)], spot = square(false);
        if (spot) cache = { item: item, x: spot[0], y: spot[1] };
      }
      var ds = {};
      sides.forEach(function (dir) { ds[dir] = doors[i][dir].slice(); });
      rooms.push({ i: i, depth: depth[i], kind: kind, rows: tiles.map(function (row) { return row.join(""); }),
                   doors: ds, stairs: here ? here.slice() : null, foes: foes, cache: cache });
    }
    return { yard: yard, floor: floor, start: start, stairs: stairs, rooms: rooms };
  }

  return { build: build, next: next, BACK: BACK, COLS: COLS, ROWS: ROWS, W: W, H: H };
})();

if (typeof module !== "undefined") module.exports = ROOMS;

/* ------------------------------------------------------------- the explore mode */

var X = null;            /* the descent: yard, floor, the floor's rooms, where you are */
var ROOMDATA = null;     /* rooms.json: the travelers and the foes */
var MAPCH = { 0: ".", 1: "#", 2: "O", 3: "~", 4: "+", 5: "^", 6: "=", 7: ">" };

function exploreLoad() {
  return fetch("rooms.json").then(function (r) { return r.json(); }).then(function (d) { ROOMDATA = d; });
}

/* The intro's brief, for exploring: a class and a yard, then off. */
function exploreBrief() {
  var b = $("brief"), row = el("div", "classes"), yard = el("input"), go, cls = exploreBrief.cls || "WARDEN";
  b.textContent = "";
  b.append(el("p", "code", "Prototype · E13"), el("h2", null, "Explore the yards"),
           el("p", null, "Walk a floor of nine rooms, seen from overhead, one room to a screen (docs/rooms.md). " +
              "Coming into a room with foes in it starts a fight on that room's own map. Caches hold gear for your " +
              "pack; the stairs, once their guards are down, take you a floor deeper."),
           el("p", "watch", "What to watch: whether walking between fights feels good, whether fights on the " +
              "rooms' maps play well, and how the floors build up."));
  Object.keys(ROOMDATA.travelers).forEach(function (c) {
    var t = ROOMDATA.travelers[c], btn = el("button", null, t.name);
    btn.type = "button";
    btn.setAttribute("aria-pressed", String(c === cls));
    btn.onclick = function () { exploreBrief.cls = c; exploreBrief(); };
    row.append(btn);
  });
  yard.type = "number"; yard.min = 0; yard.max = 65535; yard.id = "yard";
  yard.value = exploreBrief.yard != null ? exploreBrief.yard : 1 + Math.floor(Math.random() * 65535);
  yard.onchange = function () { exploreBrief.yard = Number(yard.value); };
  var lab = el("label", null, "Yard "); lab.append(yard);
  go = el("button", "primary", "Begin");
  go.type = "button";
  go.onclick = function () { exploreStart(cls, Number(yard.value) & 0xFFFF); };
  b.append(el("h3", null, "Who goes down"), row, lab, go);
}

function exploreStart(cls, yard) {
  X = { cls: cls, yard: yard, floor: 1, pack: [], lost: false };
  exploreFloor(1);
}

function exploreFloor(n) {
  X.floor = n;
  X.f = ROOMS.build(X.yard, n);
  X.cleared = {}; X.taken = {}; X.seen = {};
  X.room = X.f.start;
  var r = X.f.rooms[X.room], d = r.doors[Object.keys(r.doors)[0]];
  X.x = 7; X.y = 3;
  if (!walkable(r, X.x, X.y)) { var p = inside(r, d); X.x = p[0]; X.y = p[1]; }
  show("fight");
  $("log").textContent = "";
  log("Yard " + X.yard + ", floor " + n + ". You come down into the dark.", "round");
  exploreEnter(null);
}

function roomOf() { return X.f.rooms[X.room]; }

function foesIn(r) { return X.cleared[r.i] ? [] : r.foes; }

/* A square you can stand on out of a fight: not wall, pit or hazard, nobody there. */
function walkable(r, x, y) {
  if (x < 0 || y < 0 || x >= ROOMS.W || y >= ROOMS.H) return false;
  var t = Number(r.rows[y][x]);
  if (t === 1 || t === 2 || t === 5) return false;
  return !foesIn(r).some(function (f) { return f.x === x && f.y === y; });
}

/* The square just inside a door. */
function inside(r, door) {
  var x = door[0] === 0 ? 1 : door[0] === ROOMS.W - 1 ? ROOMS.W - 2 : door[0];
  var y = door[1] === 0 ? 1 : door[1] === ROOMS.H - 1 ? ROOMS.H - 2 : door[1];
  return walkable(r, x, y) ? [x, y] : [door[0], door[1]];
}

/* Into the room you're in now (from the room `from`, or none): a fight if it holds foes. */
function exploreEnter(from) {
  var r = roomOf();
  X.came = from;
  X.seen[r.i] = 1;
  if (foesIn(r).length) {
    log("Room " + (r.i + 1) + ": " + foesIn(r).map(function (f) { return ROOMDATA.foes[f.name].name; }).join(", ") +
        ". They've seen you.", "bad");
    return exploreFight();
  }
  if (r.kind === "cache" && !X.taken[r.i]) log("Room " + (r.i + 1) + ": a crate, still shut.");
  else if (r.stairs) log("Room " + (r.i + 1) + ": the stairs down.");
  exploreView();
}

/* What the board draws while exploring: the room, you, and its foes (as the fight would). */
function exploreView() {
  var r = roomOf(), t = ROOMDATA.travelers[X.cls], fs = foesIn(r), all;
  all = [{ side: 0, state: 0, x: X.x, y: X.y, health: 1, health_max: 1, conds: [] }].concat(fs.map(function (f) {
    return { side: 1, state: 0, x: f.x, y: f.y, health: 1, health_max: 1, conds: [] };
  }));
  fight = { explore: true, st: { map: r.rows.slice(), fighters: all }, whose: -1, me: 0, effects: [], floaters: [],
            targets: [], shown: all.map(function (f) { return { x: f.x, y: f.y, health: 1, state: 0, alpha: 1, flash: 0 }; }) };
  S = { code: "E13", title: "Explore", native: { figures: [t.figure].concat(fs.map(function (f) { return ROOMDATA.foes[f.name].figure; })),
        names: [t.name].concat(fs.map(function (f) { return ROOMDATA.foes[f.name].name; })) } };
  $("where").textContent = "Yard " + X.yard + " · floor " + X.floor + " · room " + (r.i + 1);
  resize();
  setMode(X.lost ? "lost" : "explore");
}

/* The side panel while exploring: the floor's map, who you are, what's here. */
function exploreSide() {
  var c = $("cards"), t = ROOMDATA.travelers[X.cls], grid = el("div", "floormap"), r = roomOf(), i, cell, room;
  c.textContent = "";
  for (i = 0; i < 9; ++i) {
    room = X.f.rooms[i];
    cell = el("div", "fm" + (X.seen[i] ? " seen" : "") + (i === X.room ? " here" : ""));
    if (X.seen[i]) {
      Object.keys(room.doors).forEach(function (d) { cell.classList.add("door-" + d); });
      cell.textContent = room.stairs ? "▼" : room.kind === "cache" && !X.taken[i] ? "■" :
        foesIn(room).length ? "!" : "";
    }
    cell.title = X.seen[i] ? "Room " + (i + 1) : "Not seen yet";
    grid.append(cell);
  }
  var card = el("div", "card traveler");
  card.append(el("div", "nm", t.name + ", level 1"),
              el("div", "gear", "Powers: " + t.powers.map(function (p) { return powerByName(p[0]); }).join(", ")),
              el("div", "gear", "Pack: " + (X.pack.length ? X.pack.map(function (id) { return itemOf(id).display; }).join(", ") : "empty")));
  c.append(el("h2", null, "Floor " + X.floor), grid, card,
           el("p", "note", r.stairs ? (foesIn(r).length ? "The stairs, guarded." : "The stairs: step on them to go down.")
             : r.kind === "cache" && !X.taken[r.i] ? "A crate: step on it to open it." : "Doors lead on: step onto one."));
}

function powerByName(n) {
  var id = Object.keys(POWERS).filter(function (k) { return POWERS[k].name === n; })[0];
  return id ? POWERS[id].display : n;
}

/* A step (or a walk to a square clicked). */
function exploreStep(dx, dy) {
  if (mode !== "explore") return;
  var r = roomOf(), nx = X.x + dx, ny = X.y + dy, t;
  if (!walkable(r, nx, ny)) {
    t = nx >= 0 && ny >= 0 && nx < ROOMS.W && ny < ROOMS.H ? Number(r.rows[ny][nx]) : 1;
    if (t === 5) toast("You won't walk into that: go round.");
    else if (t === 2) toast("A pit: go round.");
    return;
  }
  X.x = nx; X.y = ny;
  arrive();
}

/* What happens where you've stepped: a door, a crate, the stairs. */
function arrive() {
  var r = roomOf(), d, n, there;
  d = Object.keys(r.doors).filter(function (k) { return r.doors[k][0] === X.x && r.doors[k][1] === X.y; })[0];
  if (d) {
    n = ROOMS.next(r.i, d);
    there = X.f.rooms[n];
    var p = inside(there, there.doors[ROOMS.BACK[d]]);
    X.from = { room: r.i, x: r.doors[d][0], y: r.doors[d][1], back: inside(r, r.doors[d]) };
    X.room = n; X.x = p[0]; X.y = p[1];
    return exploreEnter(r.i);
  }
  if (r.cache && !X.taken[r.i] && r.cache.x === X.x && r.cache.y === X.y) {
    X.taken[r.i] = 1;
    var id = ROOMDATA.cache[r.cache.item];
    if (X.pack.indexOf(id) < 0 && X.pack.length < 6) X.pack.push(id);
    log("In the crate: " + itemOf(id).display + ". It's in your pack (P in a fight).", "good");
  }
  if (r.stairs && r.stairs[0] === X.x && r.stairs[1] === X.y && !foesIn(r).length) {
    log("Down the stairs.", "round");
    return exploreFloor(X.floor + 1);
  }
  exploreView();
}

/* The way to a clicked square (breadth-first, 8 ways), walked a step at a time. */
function exploreTo(tx, ty) {
  var r = roomOf(), prev = {}, todo = [[X.x, X.y]], k = X.x + "," + X.y, p, dx, dy, nx, ny, path = [];
  prev[k] = null;
  while (todo.length) {
    p = todo.shift();
    if (p[0] === tx && p[1] === ty) break;
    for (dy = -1; dy <= 1; ++dy) for (dx = -1; dx <= 1; ++dx) {
      nx = p[0] + dx; ny = p[1] + dy;
      if (prev[nx + "," + ny] !== undefined || !walkable(r, nx, ny)) continue;
      prev[nx + "," + ny] = p;
      todo.push([nx, ny]);
    }
  }
  if (prev[tx + "," + ty] === undefined) { toast("You can't get there from here."); return; }
  for (p = [tx, ty]; p && !(p[0] === X.x && p[1] === X.y); p = prev[p[0] + "," + p[1]]) path.unshift(p);
  (function walk() {
    if (!path.length || mode !== "explore") return;
    var s = path.shift(), before = X.room;
    X.x = s[0]; X.y = s[1];
    arrive();
    if (X.room === before && mode === "explore") setTimeout(walk, 70);
  })();
}

/* A room's fight: the battle engine's, on the room's map (docs/rooms.md, Exploring). */
function exploreFight() {
  var r = roomOf(), t = ROOMDATA.travelers[X.cls], fs = foesIn(r), names = [t.name], lines;
  var seen = {};
  lines = ["map " + ROOMS.W + " " + ROOMS.H].concat(r.rows.map(function (row) {
    return row.split("").map(function (c) { return MAPCH[c]; }).join("");
  }));
  lines.push("traveler " + X.x + " " + X.y + " " + t.passport + " " + t.weapon);
  fs.forEach(function (f) {
    var fd = ROOMDATA.foes[f.name], same = fs.filter(function (g) { return g.name === f.name; }).length > 1;
    seen[f.name] = (seen[f.name] || 0) + 1;
    lines.push("foe " + f.x + " " + f.y + " " + fd.line + " level " + X.floor);
    names.push(fd.name + (same ? " " + seen[f.name] : ""));
  });
  t.powers.forEach(function (p) { lines.push("power 0 " + p[0] + " " + p[1]); });
  S = { code: "E13-" + X.yard + "-" + X.floor + "-" + (r.i + 1), title: "Floor " + X.floor + ", room " + (r.i + 1),
        explore: true, lab: { won: "?", rounds: "?" },
        native: { spec: lines.join("\n") + "\n", figures: [t.figure].concat(fs.map(function (f) { return ROOMDATA.foes[f.name].figure; })),
                  names: names, pack: X.pack.slice(), skills: t.skills } };
  newFight();
  resize();
  cards();
  advance();
}

/* The fight's over: back to walking (docs/rooms.md, Exploring). */
function exploreAfter(result) {
  var r = roomOf(), me0 = fight.st.fighters[0];
  X.pack = fight.pack.slice();
  if (result === 1) {
    X.cleared[r.i] = 1;
    X.x = me0.x; X.y = me0.y;
    if (!walkable(r, X.x, X.y)) { var p = inside(r, r.doors[Object.keys(r.doors)[0]]); X.x = p[0]; X.y = p[1]; }
    log("The room is yours. You catch your breath: full health again.", "good");
  } else if (result === 3 && X.from) {
    X.room = X.from.room; X.x = X.from.back[0]; X.y = X.from.back[1];
    log("You get back out the way you came.", "round");
  } else {
    X.lost = true;
    log("You go down. The descent ends here.", "bad");
  }
  exploreView();
}

function exploreButtons() {
  if (mode === "lost") {
    return [["", "The descent ends", null, false, "", false, "hint"],
            ["R", "This floor again", function () { X.lost = false; X.pack = []; exploreFloor(X.floor); }, false, "", true],
            ["N", "A new yard", function () { exploreStart(X.cls, 1 + Math.floor(Math.random() * 65535)); }],
            ["Esc", "Back to the scenarios", intro]];
  }
  return [["Arrows", "Walk (numpad: 8 ways; or click a square)", null, false, "", false, "hint"],
          ["N", "A new yard", function () { exploreStart(X.cls, 1 + Math.floor(Math.random() * 65535)); }],
          ["gap"],
          ["X", "Leave", intro]];
}

/* Stairs and crates, drawn over the room's tiles. */
function exploreDraw() {
  var r = roomOf(), x, y, k;
  if (r.stairs) {
    x = r.stairs[0] * SQ; y = r.stairs[1] * SQ;
    ctx.fillStyle = "#0b0b10";
    ctx.fillRect(x + 4, y + 4, SQ - 8, SQ - 8);
    for (k = 0; k < 4; ++k) {
      ctx.fillStyle = "rgba(232,197,71," + (0.9 - k * 0.2) + ")";
      ctx.fillRect(x + 6 + k * 2, y + 7 + k * 5, SQ - 12 - k * 4, 3);
    }
  }
  if (r.cache && !X.taken[r.i]) {
    x = r.cache.x * SQ; y = r.cache.y * SQ;
    ctx.fillStyle = "#6b4a2b"; ctx.fillRect(x + 7, y + 11, 18, 13);
    ctx.fillStyle = "#a0753f"; ctx.fillRect(x + 7, y + 11, 18, 4);
    ctx.fillStyle = "#e8c547"; ctx.fillRect(x + 15, y + 15, 2, 3);
  }
}

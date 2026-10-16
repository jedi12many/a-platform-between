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
    people(yard, floor, rooms);
    return { yard: yard, floor: floor, start: start, stairs: stairs, rooms: rooms };
  }

  /* Where someone stands in a room (docs/rooms.md, People): the open square nearest
   * (8, 3), counting 8 ways, then the topmost, then the leftmost; reachable from the first
   * door; not a door, the stairs, a foe's or the cache's square, or (7, 3); and not in the
   * way: with someone there, every door, the stairs, the cache and every foe still reached. */
  function spot(room) {
    var tiles = room.rows.map(function (row) { return row.split("").map(Number); }), order = [], x, y, k, clear;
    var first = room.doors[DIRS.map(function (q) { return q[0]; }).filter(function (d) { return room.doors[d]; })[0]];
    var got = reach(tiles, first[0], first[1]);
    var must = Object.keys(room.doors).map(function (d) { return room.doors[d]; })
      .concat(room.foes.map(function (f) { return [f.x, f.y]; }))
      .concat(room.stairs ? [room.stairs] : []).concat(room.cache ? [[room.cache.x, room.cache.y]] : []);
    function taken(px, py) {
      return (px === 7 && py === 3) || (room.stairs && room.stairs[0] === px && room.stairs[1] === py) ||
        (room.cache && room.cache.x === px && room.cache.y === py) ||
        room.foes.some(function (f) { return f.x === px && f.y === py; });
    }
    for (y = 0; y < H; ++y) {
      for (x = 0; x < W; ++x) {
        if (tiles[y][x] === 0 && got[x + "," + y] && !taken(x, y)) order.push([Math.max(Math.abs(x - 8), Math.abs(y - 3)), y, x]);
      }
    }
    order.sort(function (a, b) { return a[0] - b[0] || a[1] - b[1] || a[2] - b[2]; });
    for (k = 0; k < order.length; ++k) {
      x = order[k][2]; y = order[k][1];
      tiles[y][x] = 1;
      clear = reach(tiles, first[0], first[1]);
      tiles[y][x] = 0;
      if (must.every(function (m) { return clear[m[0] + "," + m[1]]; })) return [x, y];
    }
    return null;
  }

  /* Who's in the rooms besides foes (docs/rooms.md, People): Vell's camp, the courier Pell
   * on floors 2 and 3, and which fights start with a parley; without the rooms' dice. */
  function people(yard, floor, rooms) {
    var empty, vell, rest, pell, at;
    rooms.forEach(function (room) {
      room.talk = null;
      room.parley = room.kind === "fight" && mix((yard ^ 0x7A1C) & 0xFFFF, floor * 16 + room.i) % 3 === 0;
    });
    empty = rooms.filter(function (r) { return r.kind === "empty"; });
    vell = empty.length ? empty.reduce(function (a, b) { return b.depth < a.depth ? b : a; })
      : rooms.filter(function (r) { return r.kind === "start"; })[0];
    at = spot(vell);
    if (at) vell.talk = { who: "trader", x: at[0], y: at[1] };
    if (floor === 2 || floor === 3) {
      rest = empty.filter(function (r) { return r !== vell; });
      if (!rest.length) rest = rooms.filter(function (r) { return r.kind === "cache"; });
      if (rest.length) {
        pell = rest.reduce(function (a, b) { return b.depth > a.depth ? b : a; });
        at = spot(pell);
        if (at) pell.talk = { who: "courier", x: at[0], y: at[1] };
      }
    }
  }

  /* Where a party stands when a fight starts (docs/rooms.md, The party): the leader where
   * they are; the rest, in marching order, on the nearest squares to the leader found
   * breadth-first (N, E, S, W, NE, SE, SW, NW) that are open ground, rough, cover or high
   * ground with no foe on them (never a door, a wall, a pit or a hazard). */
  var FAN = [[0, -1], [1, 0], [0, 1], [-1, 0], [1, -1], [1, 1], [-1, 1], [-1, -1]];
  function fanOut(room, lead, n) {
    var out = [lead.slice()], seen = {}, todo = [lead.slice()], p, k, nx, ny;
    seen[lead[0] + "," + lead[1]] = 1;
    while (todo.length && out.length < n) {
      p = todo.shift();
      for (k = 0; k < 8 && out.length < n; ++k) {
        nx = p[0] + FAN[k][0]; ny = p[1] + FAN[k][1];
        if (nx < 0 || ny < 0 || nx >= W || ny >= H || seen[nx + "," + ny]) continue;
        seen[nx + "," + ny] = 1;
        if (STANDS.indexOf(Number(room.rows[ny][nx])) < 0) continue;
        if (room.foes.some(function (f) { return f.x === nx && f.y === ny; })) continue;
        out.push([nx, ny]);
        todo.push([nx, ny]);
      }
    }
    return out;
  }

  /* ------------------------------------------------------------ open floors
   * docs/open-floors.md, "A floor, from a yard": one open area, clusters for walls, bands
   * set apart by distance. The same as tools/rooms/rooms.py's build_open. */
  var STEP8 = [[0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1]];
  var STEP4 = [[0, -1], [1, 0], [0, 1], [-1, 0]];

  function openSize(floor) { return floor <= 2 ? [48, 24] : floor <= 5 ? [64, 32] : [80, 40]; }
  function crow(a, b) { return Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1])); }
  function walks(t) { return t !== 1 && t !== 2 && t !== 5; }
  function stands(t) { return t === 0 || t === 3 || t === 4 || t === 6; }

  /* Steps on foot from s, 8 ways: {"x,y": steps}. */
  function byFoot(t, s) {
    var h = t.length, w = t[0].length, dist = {}, todo = [s], k, p, q, i;
    dist[s[0] + "," + s[1]] = 0;
    for (i = 0; i < todo.length; ++i) {
      p = todo[i];
      for (k = 0; k < 8; ++k) {
        q = [p[0] + STEP8[k][0], p[1] + STEP8[k][1]];
        if (q[0] < 0 || q[1] < 0 || q[0] >= w || q[1] >= h || (q[0] + "," + q[1]) in dist || !walks(t[q[1]][q[0]])) continue;
        dist[q[0] + "," + q[1]] = dist[p[0] + "," + p[1]] + 1;
        todo.push(q);
      }
    }
    return dist;
  }

  /* The first of `list` by `key` (an array, compared in order). */
  function least(list, key) {
    var best = null, bk = null, i, k, j, c;
    for (i = 0; i < list.length; ++i) {
      k = key(list[i]);
      c = 0;
      if (bk) for (j = 0; j < k.length && !c; ++j) c = k[j] < bk[j] ? -1 : k[j] > bk[j] ? 1 : 0;
      if (!bk || c < 0) { best = list[i]; bk = k; }
    }
    return best;
  }

  function buildOpen(yard, floor, w, h) {
    var size = openSize(floor), state, t = [], x, y, i, k, c, n, blob, p, q, d, kind, ok, sy, start, dist,
        squares = [], standing, stairs, spots, tries, bands = [], taken = {}, caches = [], foes = {}, clear,
        people = [], v, half, rest, hiding, g, count, L, names, where, seen, todo, key;
    w = w || size[0]; h = h || size[1];
    state = mix((yard ^ 0x0F10) & 0xFFFF, (floor * 256 + 254) & 0xFFFF);
    function r(m) { state = xs(state); return state % m; }
    function inside(a) { return a[0] >= 1 && a[0] <= w - 2 && a[1] >= 1 && a[1] <= h - 2; }
    function has(list, a) { return list.some(function (b) { return b[0] === a[0] && b[1] === a[1]; }); }
    /* 1. The shell. */
    for (y = 0; y < h; ++y) {
      t.push([]);
      for (x = 0; x < w; ++x) t[y].push(x === 0 || y === 0 || x === w - 1 || y === h - 1 ? 1 : 0);
    }
    /* 2. Clusters. */
    n = Math.floor((w - 2) * (h - 2) / 24);
    for (c = 0; c < n; ++c) {
      p = [2 + r(w - 4), 2 + r(h - 4)];
      kind = 5 + r(20);
      blob = [p];
      for (i = 0; i < kind - 1; ++i) {
        p = blob[r(blob.length)];
        d = STEP4[r(4)];
        q = [p[0] + d[0], p[1] + d[1]];
        if (inside(q) && !has(blob, q)) blob.push(q);
      }
      ok = blob.every(function (b) {
        return t[b[1]][b[0]] !== 1 && STEP8.every(function (e) { return t[b[1] + e[1]][b[0] + e[0]] !== 1; });
      });
      if (!ok) continue;
      blob.forEach(function (b) { t[b[1]][b[0]] = 1; });
      for (i = r(3); i > 0; --i) {
        p = blob[r(blob.length)];
        d = STEP8[r(8)];
        k = [4, 4, 3, 6][r(4)];
        q = [p[0] + d[0], p[1] + d[1]];
        if (t[q[1]][q[0]] === 0) t[q[1]][q[0]] = k;
      }
    }
    /* 3. Open ground. */
    n = Math.floor((w - 2) * (h - 2) / 96);
    for (c = 0; c < n; ++c) {
      x = 1 + r(w - 2); y = 1 + r(h - 2); k = r(5);
      if (t[y][x] === 0 && STEP8.every(function (e) { var u = t[y + e[1]][x + e[0]]; return u !== 1 && u !== 2 && u !== 5; }))
        t[y][x] = [3, 3, 2, 5, 4][k];
    }
    /* 4. The start. */
    sy = 1 + r(h - 2);
    for (y = 0; y < h; ++y) for (x = 0; x < w; ++x) if (walks(t[y][x])) squares.push([x, y]);
    start = least(squares, function (a) { return [a[0], Math.abs(a[1] - sy), a[1]]; });
    /* 5. One region. */
    dist = byFoot(t, start);
    for (y = 0; y < h; ++y) for (x = 0; x < w; ++x) if (walks(t[y][x]) && !((x + "," + y) in dist)) t[y][x] = 1;
    squares = squares.filter(function (a) { return (a[0] + "," + a[1]) in dist; });
    function far(a) { return dist[a[0] + "," + a[1]]; }
    /* 6. The stairs. */
    stairs = least(squares.filter(function (a) { return t[a[1]][a[0]] === 0; }), function (a) { return [-far(a), a[1], a[0]]; });
    /* 7. Bands. */
    n = Math.max(1, Math.floor(squares.length / 150));
    standing = squares.filter(function (a) { return stands(t[a[1]][a[0]]); });
    spots = [least(standing.filter(function (a) { return crow(a, stairs) >= 2; }),
                   function (a) { return [crow(a, stairs), a[1], a[0]]; })];
    tries = 0;
    while (spots.length < n && tries < 64 * n) {
      ++tries;
      q = [1 + r(w - 2), 1 + r(h - 2)];
      if (stands(t[q[1]][q[0]]) && (q[0] + "," + q[1]) in dist && !(q[0] === stairs[0] && q[1] === stairs[1]) &&
          crow(q, start) >= 10 && spots.every(function (o) { return crow(q, o) >= 10; })) spots.push(q);
    }
    spots.forEach(function (spot, b) {
      hiding = r(4) !== 0;
      g = floor + Math.floor(far(spot) / 16);
      count = Math.min(4, 1 + Math.floor(g / 3) + (b === 0 ? 1 : 0));
      L = Math.min(4, 1 + Math.floor(g / 2));
      names = [];
      for (i = 0; i < count; ++i) names.push(POOL[r(L)]);
      where = [spot];
      seen = {}; seen[spot[0] + "," + spot[1]] = 1;
      todo = [spot];
      while (todo.length && where.length < count) {
        p = todo.shift();
        for (k = 0; k < 8 && where.length < count; ++k) {
          q = [p[0] + FAN[k][0], p[1] + FAN[k][1]];
          key = q[0] + "," + q[1];
          if (seen[key] || q[0] < 0 || q[1] < 0 || q[0] >= w || q[1] >= h) continue;
          seen[key] = 1;
          if (!stands(t[q[1]][q[0]]) || (q[0] === stairs[0] && q[1] === stairs[1]) ||
              (q[0] === start[0] && q[1] === start[1]) || taken[key]) continue;
          where.push(q);
          todo.push(q);
        }
      }
      where.forEach(function (a) { taken[a[0] + "," + a[1]] = 1; });
      bands.push({ x: spot[0], y: spot[1], hiding: hiding, stairs: b === 0,
                   parley: b > 0 && mix((yard ^ 0x7A1C) & 0xFFFF, (floor * 64 + b) & 0xFFFF) % 3 === 0,
                   foes: names.slice(0, where.length).map(function (nm, j) {
                     return { name: nm, x: where[j][0], y: where[j][1] };
                   }) });
    });
    /* 8. Caches. */
    n = 1 + Math.floor(squares.length / 600);
    for (c = 0; c < n; ++c) {
      for (i = 0; i < 64; ++i) {
        q = [1 + r(w - 2), 1 + r(h - 2)];
        if (stands(t[q[1]][q[0]]) && (q[0] + "," + q[1]) in dist && !(q[0] === stairs[0] && q[1] === stairs[1]) &&
            crow(q, start) >= 6 && spots.every(function (o) { return crow(q, o) >= 4; }) &&
            caches.every(function (o) { return crow(q, [o.x, o.y]) >= 4; })) {
          caches.push({ item: CACHE[r(5)], x: q[0], y: q[1] });
          break;
        }
      }
    }
    /* 9. People. */
    bands.forEach(function (b) { b.foes.forEach(function (f) { foes[f.x + "," + f.y] = [f.x, f.y]; }); });
    clear = standing.filter(function (a) {
      return !(a[0] === stairs[0] && a[1] === stairs[1]) && spots.every(function (o) { return crow(a, o) >= 6; }) &&
        Object.keys(foes).every(function (f) { return crow(a, foes[f]) >= 6; }) &&
        caches.every(function (o) { return !(o.x === a[0] && o.y === a[1]); });
    });
    if (clear.length) {
      v = least(clear, function (a) { return [Math.abs(far(a) - 8), a[1], a[0]]; });
      people.push({ who: "trader", x: v[0], y: v[1] });
      if (floor === 2 || floor === 3) {
        rest = clear.filter(function (a) { return crow(a, v) >= 4; });
        if (rest.length) {
          half = Math.floor(far(stairs) / 2);
          p = least(rest, function (a) { return [Math.abs(far(a) - half), a[1], a[0]]; });
          people.push({ who: "courier", x: p[0], y: p[1] });
        }
      }
    }
    return { yard: yard, floor: floor, w: w, h: h,
             rows: t.map(function (row) { return row.join(""); }),
             start: start, stairs: stairs, bands: bands, caches: caches, people: people };
  }

  return { build: build, buildOpen: buildOpen, openSize: openSize, next: next, fanOut: fanOut, BACK: BACK, COLS: COLS, ROWS: ROWS, W: W, H: H };
})();

if (typeof module !== "undefined") module.exports = ROOMS;

/* ------------------------------------------------------------- the explore mode */

var X = null;            /* the descent: yard, floor, the floor's rooms, where you are */
var ROOMDATA = null;     /* rooms.json: the travelers and the foes */
var MAPCH = { 0: ".", 1: "#", 2: "O", 3: "~", 4: "+", 5: "^", 6: "=", 7: ">" };
var SPEED = 4.5;         /* squares a second, walking */
var BODY = 0.3;          /* half a figure's footprint, in squares */
var held = {};           /* the walking keys held down: their steps */
var GAP = 0.85;          /* squares between travelers in marching order, walking */

/* Scrolling (docs/rooms.md, "Scrolling, to compare"): the floor's nine rooms side by side
 * as one area of 48 x 24 squares, their doors meeting; a view follows you: 16 x 8, a room's
 * size, or zoomed out (Z) to 24 x 12 or the whole floor. Then X.x, X.y, X.px and X.py are
 * the area's; one room a screen, they're the room's. */
var ZOOMS = [[16, 8], [24, 12], [48, 24]], zoom = 0;
function viewSize() { return X && X.open && zoom === ZOOMS.length - 1 ? [X.o.w, X.o.h] : ZOOMS[zoom]; }

/* The area you walk: the nine rooms side by side, or an open floor (docs/open-floors.md). */
function areaW() { return X.open ? X.o.w : ROOMS.COLS * ROOMS.W; }
function areaH() { return X.open ? X.o.h : ROOMS.ROWS * ROOMS.H; }
/* How the explore was begun: one room a screen (false), scrolling (true), or "open". */
function viewArg() { return X.open ? "open" : X.scroll; }
function ox(i) { return X.scroll ? (i % ROOMS.COLS) * ROOMS.W : 0; }
function oy(i) { return X.scroll ? Math.floor(i / ROOMS.COLS) * ROOMS.H : 0; }

/* The room a square of the area is in, or -1. */
function roomAt(x, y) {
  if (X.open) return x < 0 || y < 0 || x >= X.o.w || y >= X.o.h ? -1 : 0;
  if (x < 0 || y < 0 || x >= ROOMS.COLS * ROOMS.W || y >= ROOMS.ROWS * ROOMS.H) return -1;
  return Math.floor(y / ROOMS.H) * ROOMS.COLS + Math.floor(x / ROOMS.W);
}

/* Can you stand on (x, y), in X's own squares? */
function free(x, y) {
  if (X.open) return openFree(x, y);
  if (!X.scroll) return walkable(roomOf(), x, y);
  var i = roomAt(x, y);
  return i >= 0 && walkable(X.f.rooms[i], x - ox(i), y - oy(i));
}

/* Standing at square (x, y) of the room you're in, drawn there too (a door, a floor's
 * start, after a fight). */
function at(x, y) {
  X.x = x + ox(X.room); X.y = y + oy(X.room); X.px = X.x; X.py = X.y; X.path = null;
  X.trail = [[X.px, X.py]];                             /* the others start at the leader's heels */
  reveal();
}

/* The minimap's fog (scrolling): the squares the party has come within SIGHT of, kept for
 * the floor. Cleared by distance, not by room, so it holds when rooms open into each other. */
var SIGHT = 6;
function reveal() {
  if (!X.scroll) return;
  var w = areaW(), h = areaH(), x, y, R = X.open ? openSight() : SIGHT;    /* (open: the party's range) */
  if (!X.fog) X.fog = new Uint8Array(w * h);
  for (y = Math.max(0, X.y - R); y <= Math.min(h - 1, X.y + R); ++y)
    for (x = Math.max(0, X.x - R); x <= Math.min(w - 1, X.x + R); ++x)
      if ((x - X.x) * (x - X.x) + (y - X.y) * (y - X.y) <= R * R) X.fog[y * w + x] = 1;
}

/* The minimap (scrolling): the floor a few pixels a square, black where it's not been seen;
 * the stairs, crates and foes seen; the view's rectangle and the party. */
var MM = 4, MM_COLOUR = ["#3d3d46", "#9a9aa6", "#2a2a9a", "#6b4a1e", "#3f7a3a", "#a83a2e", "#c8c8d0", "#c8b848"];
function drawMinimap() {
  var c = $("minimap"), g, w = areaW(), h = areaH(), x, y, cam = fight && fight.cam;
  if (!c || !X.fog) return;
  if (X.open) return openMinimap(c);
  g = c.getContext("2d");
  g.fillStyle = "#000";
  g.fillRect(0, 0, c.width, c.height);
  for (y = 0; y < h; ++y)
    for (x = 0; x < w; ++x)
      if (X.fog[y * w + x]) { g.fillStyle = MM_COLOUR[Number(X.area[y][x])] || MM_COLOUR[0]; g.fillRect(x * MM, y * MM, MM, MM); }
  X.f.rooms.forEach(function (r) {
    var x0 = ox(r.i), y0 = oy(r.i), seen = function (sx, sy) { return X.fog[(y0 + sy) * w + x0 + sx]; };
    if (r.stairs && seen(r.stairs[0], r.stairs[1])) { g.fillStyle = "#fff"; g.fillRect((x0 + r.stairs[0]) * MM, (y0 + r.stairs[1]) * MM, MM, MM); }
    if (r.cache && !X.taken[r.i] && seen(r.cache.x, r.cache.y)) { g.fillStyle = "#e0a030"; g.fillRect((x0 + r.cache.x) * MM, (y0 + r.cache.y) * MM, MM, MM); }
    foesIn(r).forEach(function (f) {
      if (seen(f.x, f.y)) { g.fillStyle = "#ff4040"; g.fillRect((x0 + f.x) * MM + 1, (y0 + f.y) * MM + 1, MM - 2, MM - 2); }
    });
  });
  if (cam && fight.view) {
    g.strokeStyle = "#fff";
    g.lineWidth = 1;
    g.strokeRect(Math.round(cam.x * MM) + 0.5, Math.round(cam.y * MM) + 0.5,     /* (on whole pixels: crisp) */
                 fight.view[0] * MM - 1, fight.view[1] * MM - 1);
  }
  g.fillStyle = "#40ff80";
  g.fillRect(Math.round(X.px * MM) - 1, Math.round(X.py * MM) - 1, MM + 2, MM + 2);
}

/* Where the k-th in marching order walks: k gaps back along the leader's trail, and how
 * much of them shows (they come out from behind the leader as the trail grows). */
function follower(k) {
  var want = k * GAP, got = 0, i, a, b, d;
  for (i = X.trail.length - 1; i > 0; --i) {
    a = X.trail[i]; b = X.trail[i - 1];
    d = Math.hypot(a[0] - b[0], a[1] - b[1]);
    if (got + d >= want) {
      return { x: a[0] + (b[0] - a[0]) * (want - got) / d, y: a[1] + (b[1] - a[1]) * (want - got) / d, alpha: 1 };
    }
    got += d;
  }
  a = X.trail[0];
  return { x: a[0], y: a[1], alpha: Math.max(0, Math.min(1, (got - (k - 1) * GAP) / GAP)) };
}

/* The leader's trail, as they walk: a point every few hundredths of a square, enough of it
 * for the party. */
function trailOn() {
  var last = X.trail[X.trail.length - 1];
  if (Math.hypot(X.px - last[0], X.py - last[1]) < 0.04) return;
  X.trail.push([X.px, X.py]);
  if (X.trail.length > 400) X.trail.splice(0, X.trail.length - 400);
}

/* The party's classes, in marching order: "WARDEN", "WARDEN,ROGUE" or a list. */
function partyOf(p) {
  var list = (Array.isArray(p) ? p : String(p || "WARDEN").split(",")).map(function (c) { return String(c).toUpperCase(); })
    .filter(function (c, i, all) { return ROOMDATA.travelers[c] && all.indexOf(c) === i; });
  return (list.length ? list : ["WARDEN"]).slice(0, 4);
}

function exploreLoad() {
  return fetch("rooms.json").then(function (r) { return r.json(); }).then(function (d) { ROOMDATA = d; });
}

/* The intro's brief, for exploring: a class and a yard, then off. */
function exploreBrief() {
  var b = $("brief"), row = el("div", "classes"), yard = el("input"), go;
  var party = exploreBrief.party = exploreBrief.party || ["WARDEN", "ROGUE", "CHANNELER", "MEDIC"];
  b.textContent = "";
  b.append(el("p", "code", "Prototype · E13"), el("h2", null, "Explore the yards"),
           el("p", null, "Walk a floor of nine rooms, seen from overhead, one room to a screen (docs/rooms.md). " +
              "Coming into a room with foes in it starts a fight on that room's own map, unless they talk first. " +
              "Caches hold gear for your pack; the stairs, once their guards are down, take you a floor deeper."),
           el("p", null, "People: Vell trades gear from a camp on every floor, and someone is lost on the floors " +
              "below. What they say, and what you say back, is a Quest Script played by the game's own story VM; " +
              "the leader's checks are rolled by the rules, and the story remembers the whole descent."),
           el("p", "watch", "What to watch: whether walking between fights feels good, whether fights on the " +
              "rooms' maps play well, how the floors build up, and whether talking feels like a real way round a fight."));
  /* The party: up to four, in the order picked (marching order: the first leads). */
  Object.keys(ROOMDATA.travelers).forEach(function (c) {
    var t = ROOMDATA.travelers[c], k = party.indexOf(c), btn = el("button", null, (k >= 0 ? (k + 1) + " " : "") + t.name);
    btn.type = "button";
    btn.setAttribute("aria-pressed", String(k >= 0));
    btn.onclick = function () {
      if (k >= 0) { if (party.length > 1) party.splice(k, 1); }
      else if (party.length < 4) party.push(c);
      exploreBrief();
    };
    row.append(btn);
  });
  yard.type = "number"; yard.min = 0; yard.max = 65535; yard.id = "yard";
  yard.value = exploreBrief.yard != null ? exploreBrief.yard : 1 + Math.floor(Math.random() * 65535);
  yard.onchange = function () { exploreBrief.yard = Number(yard.value); };
  var lab = el("label", null, "Yard "); lab.append(yard);
  var views = el("div", "classes");
  [["One room a screen", false], ["Scrolling", true], ["Open floor", "open"]].forEach(function (v) {
    var btn = el("button", null, v[0]);
    btn.type = "button";
    btn.setAttribute("aria-pressed", String((exploreBrief.scroll || false) === v[1]));
    btn.onclick = function () { exploreBrief.scroll = v[1]; exploreBrief(); };
    views.append(btn);
  });
  var looks = el("div", "classes");
  [["By floor", ""]].concat(LOOKS.map(function (l) { return [l[0].toUpperCase() + l.slice(1), l]; })).forEach(function (v) {
    var btn = el("button", null, v[0]);
    btn.type = "button";
    btn.setAttribute("aria-pressed", String((exploreBrief.look || "") === v[1]));
    btn.onclick = function () { exploreBrief.look = v[1]; exploreBrief(); };
    looks.append(btn);
  });
  go = el("button", "primary", "Begin");
  go.type = "button";
  go.onclick = function () { exploreStart(party, Number(yard.value) & 0xFFFF, exploreBrief.scroll || false, exploreBrief.look); };
  b.append(el("h3", null, "Who goes down"), el("p", "note", "Up to four, in marching order: the first leads, " +
           "the rest follow; click again to leave one out."), row, el("h3", null, "The view"), el("p", "note", "An open floor (docs/open-floors.md) is one wide space, " +
           "walls in clusters; bands of foes stand about it unseen, and roll to see you as you come near (S to sneak), " +
           "as you roll to spot them: the rolls are in the log."), views,
           el("h3", null, "The look"), el("p", "note", "How the floors are drawn (docs/art.md, Looks): by floor, " +
           "a forest, then the mountains, a town and a dungeon, and round again; or one look all the way down."),
           looks, lab, go);
}

function exploreStart(party, yard, scroll, look) {
  party = partyOf(party);
  X = { party: party, cls: party[0], yard: yard, floor: 1, pack: [], lost: false, scroll: !!scroll, open: scroll === "open",
        look: LOOKS.indexOf(look) >= 0 ? look : "", pell: "" };
  storyBoard();
  exploreFloor(1);
}

function exploreFloor(n) {
  if (X.open) return openFloor(n);
  X.floor = n;
  X.f = ROOMS.build(X.yard, n);
  X.cleared = {}; X.taken = {}; X.seen = {}; X.parleyed = {};
  X.fog = null;
  X.room = X.f.start;
  X.settle = false;
  if (X.scroll) {
    /* The area: the rooms' rows side by side. */
    X.area = [];
    for (var ay = 0; ay < ROOMS.ROWS * ROOMS.H; ++ay) {
      var line = "";
      for (var ax = 0; ax < ROOMS.COLS; ++ax) line += X.f.rooms[Math.floor(ay / ROOMS.H) * ROOMS.COLS + ax].rows[ay % ROOMS.H];
      X.area.push(line);
    }
  }
  var r = X.f.rooms[X.room], d = r.doors[Object.keys(r.doors)[0]];
  at(7, 3);
  if (!walkable(r, 7, 3)) { var p = inside(r, d); at(p[0], p[1]); }
  X.cam = camFor();
  show("fight");
  $("log").textContent = "";
  log("Yard " + X.yard + ", floor " + n + ". You come down into the dark.", "round");
  exploreEnter(null);
}

function roomOf() { return X.f.rooms[X.room]; }

/* The looks (docs/art.md, Looks): the same terrain drawn as a place. Floor by floor, unless
 * one was picked. */
var LOOKS = ["forest", "mountain", "town", "dungeon"];

function lookOf(floor) { return X.look || LOOKS[(floor - 1) % LOOKS.length]; }

/* A square's tile in the floor's look (docs/rooms.md, Looks): its terrain's, or one of
 * that terrain's variants (open2, open3...), and on open ground with nothing on it, now
 * and then scenery, picked by a hash of where the square is, so it's the same each time
 * it's drawn and decides nothing. Room r's square (x, y); t its terrain. */
function dress(r, x, y, t) {
  var look = ART.looks[lookOf(X.floor)], base = ART.terrain[t], n, h, scen, vars;
  if (!look || !base) return base || "open";
  n = ((X.floor * 9 + r.i) * 8 + y) * 16 + x;
  h = Math.imul((n ^ (X.yard << 4)) >>> 0, 0x9E3779B1) >>> 24;     /* 0-255 */
  if (!look.split) {
    look.split = { scenery: [], variants: {} };
    look.order.slice(8).forEach(function (name) {
      var b = name.replace(/[0-9]+$/, "");
      if (b !== name && ART.terrain.indexOf(b) >= 0) (look.split.variants[b] = look.split.variants[b] || []).push(name);
      else look.split.scenery.push(name);
    });
  }
  scen = look.split.scenery;
  if (t === 0 && scen.length && h < 16 && !(r.stairs && r.stairs[0] === x && r.stairs[1] === y) &&
      !(r.cache && r.cache.x === x && r.cache.y === y) &&
      !r.foes.some(function (f) { return f.x === x && f.y === y; })) return scen[h % scen.length];
  vars = look.split.variants[base] || [];
  if (!vars.length || (h & 7) !== 0) return base;                   /* seven squares in eight plain */
  return vars[(h >> 3) % vars.length];
}

/* What the board draws for the floor: its look, and each square's tile (the area's, or
 * one room's). */
function dressFight(room) {
  fight.look = lookOf(X.floor);
  fight.dress = function (x, y, t) {
    var r = room || X.f.rooms[roomAt(x, y)];
    return dress(r, room ? x : x - ox(r.i), room ? y : y - oy(r.i), t);
  };
}

function foesIn(r) { return X.cleared[r.i] ? [] : r.foes; }

/* A square you can stand on out of a fight: not wall, pit or hazard, nobody there. */
function walkable(r, x, y) {
  if (x < 0 || y < 0 || x >= ROOMS.W || y >= ROOMS.H) return false;
  var t = Number(r.rows[y][x]);
  if (t === 1 || t === 2 || t === 5) return false;
  if (npcIn(r) && r.talk.x === x && r.talk.y === y) return false;
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
    if (X.scroll && fight && fight.explore) {
      /* The view settles on the room first (exploreTick), and you step in off the doorway
       * (as you'd stand one room a screen); then the fight begins. */
      var lx = X.x - ox(r.i), ly = X.y - oy(r.i), inn = inside(r, [lx, ly]);
      X.settle = true;
      X.walkIn = [inn[0] + ox(r.i), inn[1] + oy(r.i)];
      if (fight.view[0] !== ROOMS.W) { fight.view = [ROOMS.W, ROOMS.H]; resize(); }  /* (zoomed out: in to the room) */
      held = {};
      X.path = null;
      return exploreSide();
    }
    return exploreMeet();
  }
  if (r.kind === "cache" && !X.taken[r.i]) log("Room " + (r.i + 1) + ": a crate, still shut.");
  else if (r.stairs) log("Room " + (r.i + 1) + ": the stairs down.");
  exploreView();
}

/* What the board draws while exploring: the room, you, and its foes (as the fight would). */
function exploreView() {
  var r = roomOf(), fs = [], all, team = X.party.map(function (c) { return ROOMDATA.travelers[c]; });
  /* The foes in view: this room's, or, scrolling, every room's, where they stand in the area. */
  if (X.open) fs = openShown();
  else (X.scroll ? X.f.rooms : [r]).forEach(function (room) {
    foesIn(room).forEach(function (f) { fs.push({ name: f.name, x: f.x + ox(room.i), y: f.y + oy(room.i) }); });
  });
  all = team.map(function () { return { side: 0, state: 0, x: X.x, y: X.y, health: 1, health_max: 1, conds: [] }; })
    .concat(fs.map(function (f) { return { side: 1, state: 0, x: f.x, y: f.y, health: 1, health_max: 1, conds: [] }; }));
  fight = { explore: true, st: { map: X.scroll ? X.area.slice() : r.rows.slice(), fighters: all }, whose: -1, me: 0,
            effects: [], floaters: [], targets: [],
            shown: all.map(function (f) { return { x: f.x, y: f.y, health: 1, state: 0, alpha: 1, flash: 0 }; }) };
  if (X.scroll) { fight.cam = X.cam; fight.view = viewSize().slice(); }
  dressFight(X.scroll ? null : r);
  showParty();                                          /* where you're drawn: between squares, walking */
  S = { code: "E13", title: "Explore", native: {
        figures: team.map(function (t) { return t.figure; }).concat(fs.map(function (f) { return ROOMDATA.foes[f.name].figure; })),
        names: team.map(function (t) { return t.name; }).concat(fs.map(function (f) { return ROOMDATA.foes[f.name].name; })) } };
  $("where").textContent = "Yard " + X.yard + " · floor " + X.floor + (X.open ? " · open" : " · room " + (r.i + 1));
  resize();
  setMode(X.lost ? "lost" : "explore");
}

/* The party where it's drawn: the leader, and the rest along the leader's trail. The
 * followers are drawn behind the leader where they overlap (later in the list, lower down). */
function showParty() {
  var k, f;
  fight.shown[0].x = X.px; fight.shown[0].y = X.py;
  for (k = 1; k < X.party.length; ++k) {
    f = follower(k);
    fight.shown[k].x = f.x; fight.shown[k].y = f.y - 0.001 * k; fight.shown[k].alpha = f.alpha;
  }
}

/* The side panel while exploring: the floor's map, who you are, what's here. */
function exploreSide() {
  if (X.open) return openSide();
  var c = $("cards"), grid = el("div", "floormap"), r = roomOf(), i, cell, room, cards = [];
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
  X.party.forEach(function (cls, k) {
    var t = ROOMDATA.travelers[cls], card = el("div", "card traveler");
    card.append(el("div", "nm", (k + 1) + ". " + t.name + ", level 1" + (k ? "" : " · leads")),
                el("div", "gear", "Powers: " + t.powers.map(function (p) { return powerByName(p[0]); }).join(", ")));
    cards.push(card);
  });
  cards.push(el("p", "note", "Pack (the party's): " +
                (X.pack.length ? X.pack.map(function (id) { return itemOf(id).display; }).join(", ") : "empty")));
  if (X.scroll) {
    grid = el("canvas", "minimap");
    grid.id = "minimap";
    grid.width = ROOMS.COLS * ROOMS.W * MM;
    grid.height = ROOMS.ROWS * ROOMS.H * MM;
    grid.title = "The floor: what you've seen, and the view's rectangle";
  }
  c.append(el("h2", null, "Floor " + X.floor), grid);
  if (X.scroll) drawMinimap();
  cards.forEach(function (card) { c.append(card); });
  c.append(
           el("p", "note", r.stairs ? (foesIn(r).length ? "The stairs, guarded." : "The stairs: step on them to go down.")
             : r.kind === "cache" && !X.taken[r.i] ? "A crate: step on it to open it." : "Doors lead on: step onto one."));
  var who = npcIn(r);
  if (who) c.append(el("p", "note", who.name + (who.who === "trader" ? "'s camp" : ", lost") + ": walk up and press T, or click them, to talk."));
  if (X.pell === "follows") c.append(el("p", "note", "Pell is following you. Vell's camp is somewhere on every floor."));
}

function powerByName(n) {
  var id = Object.keys(POWERS).filter(function (k) { return POWERS[k].name === n; })[0];
  return id ? POWERS[id].display : n;
}

/* Walking (docs/rooms.md, Exploring): smooth, while a key's held, a figure's footprint
 * sliding along walls and nudged round corners, so a doorway is easy to find. You're "on"
 * the square under your middle: that's where a door, a crate or the stairs take effect,
 * and where you stand when a fight starts. */
function fits(px, py) {
  var x0 = Math.floor(px + 0.5 - BODY), x1 = Math.floor(px + 0.5 + BODY - 1e-6);
  var y0 = Math.floor(py + 0.5 - BODY), y1 = Math.floor(py + 0.5 + BODY - 1e-6), x, y;
  for (y = y0; y <= y1; ++y) for (x = x0; x <= x1; ++x) if (!free(x, y)) return false;
  return true;
}

/* Move by (dx, dy) along one axis; blocked, slide toward the middle of the way through. */
function slide(dx, dy) {
  var c;
  if (fits(X.px + dx, X.py + dy)) { X.px += dx; X.py += dy; return true; }
  if (dx) {
    c = Math.round(X.py);
    if (Math.abs(X.py - c) < 0.45 && fits(X.px + dx, c)) {
      X.py += Math.sign(c - X.py) * Math.min(Math.abs(dx), Math.abs(c - X.py));
      return true;
    }
  } else if (dy) {
    c = Math.round(X.px);
    if (Math.abs(X.px - c) < 0.45 && fits(c, X.py + dy)) {
      X.px += Math.sign(c - X.px) * Math.min(Math.abs(dy), Math.abs(c - X.px));
      return true;
    }
  }
  return false;
}

/* Where the view would be, scrolling: you in its middle, kept inside the area. */
function camFor() {
  if (!X.scroll) return null;
  var w = viewSize()[0], h = viewSize()[1];
  return { x: Math.max(0, Math.min(areaW() - w, X.px + 0.5 - w / 2)),
           y: Math.max(0, Math.min(areaH() - h, X.py + 0.5 - h / 2)) };
}

/* Z: the view zoomed out a step (or back in from the whole floor), straight away. */
function exploreZoom() {
  zoom = (zoom + 1) % ZOOMS.length;
  X.cam = camFor();
  fight.cam = { x: Math.round(X.cam.x * 16) / 16, y: Math.round(X.cam.y * 16) / 16 };
  fight.view = viewSize().slice();
  resize();
  actions();
}

/* The view eases toward where it should be, a C64 pixel at a time (1/16 of a square: the
 * fine scroll's step). Settling on a room for its fight, it goes straight there. */
function camStep(dt) {
  var want = X.settle ? { x: ox(X.room), y: oy(X.room) } : camFor(), k = Math.min(1, dt * (X.settle ? 9 : 6));
  X.cam.x += (want.x - X.cam.x) * k;
  X.cam.y += (want.y - X.cam.y) * k;
  if (Math.abs(want.x - X.cam.x) < 1 / 16 && Math.abs(want.y - X.cam.y) < 1 / 16) { X.cam.x = want.x; X.cam.y = want.y; }
  fight.cam = { x: Math.round(X.cam.x * 16) / 16, y: Math.round(X.cam.y * 16) / 16 };
  return X.cam.x === want.x && X.cam.y === want.y;
}

/* Each frame while exploring (arena.js's frame calls it). */
function exploreTick(now) {
  var dt = Math.min(0.05, X.t ? (now - X.t) / 1000 : 0), dx = 0, dy = 0, sp, t, d, before = X.room, i, back;
  X.t = now;
  if (mode !== "explore" || !fight || !fight.explore) return;
  if (X.settle && X.walkIn) {
    /* Stepping in off the doorway while the view settles. */
    t = X.walkIn;
    d = Math.hypot(t[0] - X.px, t[1] - X.py);
    sp = SPEED * dt;
    if (d <= sp) { X.px = t[0]; X.py = t[1]; X.x = t[0]; X.y = t[1]; X.walkIn = null; }
    else { X.px += (t[0] - X.px) / d * sp; X.py += (t[1] - X.py) / d * sp; }
    trailOn();
    showParty();
  }
  if (X.scroll) drawMinimap();
  if (X.scroll && camStep(dt) && X.settle && !X.walkIn) { X.settle = false; return exploreMeet(); }
  if (X.settle) return;
  Object.keys(held).forEach(function (k) { dx += held[k][0]; dy += held[k][1]; });
  dx = Math.sign(dx); dy = Math.sign(dy);
  sp = SPEED * dt * (X.open && X.sneak ? 0.5 : 1);     /* sneaking: half speed */
  if (dx || dy) {
    X.path = null;
    if (dx && dy) sp *= Math.SQRT1_2;
    if (dx) slide(dx * sp, 0);
    if (dy) slide(0, dy * sp);
  } else if (X.path && X.path.length) {
    /* A walk to a square clicked: glide from square to square along the way found. */
    t = X.path[0];
    d = Math.hypot(t[0] - X.px, t[1] - X.py);
    if (d <= sp) { X.px = t[0]; X.py = t[1]; X.path.shift(); }
    else { X.px += (t[0] - X.px) / d * sp; X.py += (t[1] - X.py) / d * sp; }
  } else {
    if (X.talkAfter) { X.talkAfter = false; if (nearNpc()) talkTo(nearNpc()); }
    return;
  }
  trailOn();
  showParty();
  t = [Math.floor(X.px + 0.5), Math.floor(X.py + 0.5)];
  if (t[0] !== X.x || t[1] !== X.y) {
    back = [X.x - ox(X.room), X.y - oy(X.room)];
    X.x = t[0]; X.y = t[1];
    reveal();
    fight.st.fighters[0].x = X.x; fight.st.fighters[0].y = X.y;
    i = X.scroll ? roomAt(X.x, X.y) : X.room;
    if (i !== X.room) {
      /* Scrolling, across a doorway into the next room: no redraw, the view just follows. */
      X.from = { room: X.room, back: back };
      X.room = i;
      $("where").textContent = "Yard " + X.yard + " · floor " + X.floor + " · room " + (i + 1);
      return exploreEnter(before);
    }
    arrive();
    if (X.room !== before) held = {};                   /* a new room: let go, look about */
    if (mode === "explore" && !!nearNpc() !== !!X.near) { X.near = nearNpc(); actions(); }
  }
}

/* The walking keys: down and up (arena.js's keys hand them over while exploring). */
function exploreHold(e, step) {
  e.preventDefault();
  held[e.code || e.key] = step;
}
if (typeof document !== "undefined") {
  document.addEventListener("keyup", function (e) { delete held[e.code || e.key]; });
  window.addEventListener("blur", function () { held = {}; });
}

/* What happens where you've stepped: a door, a crate, the stairs. */
function arrive() {
  if (X.open) return openArrive();
  var r = roomOf(), d, n, there, lx = X.x - ox(r.i), ly = X.y - oy(r.i);
  d = X.scroll ? null : Object.keys(r.doors).filter(function (k) { return r.doors[k][0] === lx && r.doors[k][1] === ly; })[0];
  if (d) {
    n = ROOMS.next(r.i, d);
    there = X.f.rooms[n];
    var p = inside(there, there.doors[ROOMS.BACK[d]]);
    X.from = { room: r.i, x: r.doors[d][0], y: r.doors[d][1], back: inside(r, r.doors[d]) };
    X.room = n;
    at(p[0], p[1]);
    return exploreEnter(r.i);
  }
  if (r.cache && !X.taken[r.i] && r.cache.x === lx && r.cache.y === ly) {
    X.taken[r.i] = 1;
    var id = ROOMDATA.cache[r.cache.item];
    if (X.pack.indexOf(id) < 0 && X.pack.length < 6) X.pack.push(id);
    log("In the crate: " + itemOf(id).display + ". It's in your pack (P in a fight).", "good");
    exploreSide();
  }
  if (r.stairs && r.stairs[0] === lx && r.stairs[1] === ly && !foesIn(r).length) {
    log("Down the stairs.", "round");
    held = {};
    return exploreFloor(X.floor + 1);
  }
}

/* The way to a clicked square (breadth-first, 8 ways), glided along (exploreTick). */
function exploreTo(tx, ty) {
  var prev = {}, todo = [[X.x, X.y]], k = X.x + "," + X.y, p, dx, dy, nx, ny, path = [], who = npcAt(tx, ty);
  if (X.settle) return;
  X.talkAfter = false;
  if (who) {
    /* Someone to talk to: next to them already, talk; or walk up to them first. */
    if (Math.max(Math.abs(X.x - tx), Math.abs(X.y - ty)) <= 1) return talkTo(who);
    X.talkAfter = true;
  }
  prev[k] = null;
  while (todo.length) {
    p = todo.shift();
    if (who && Math.max(Math.abs(p[0] - tx), Math.abs(p[1] - ty)) <= 1) { tx = p[0]; ty = p[1]; break; }
    if (p[0] === tx && p[1] === ty) break;
    for (dy = -1; dy <= 1; ++dy) for (dx = -1; dx <= 1; ++dx) {
      nx = p[0] + dx; ny = p[1] + dy;
      if (prev[nx + "," + ny] !== undefined || !free(nx, ny)) continue;
      prev[nx + "," + ny] = p;
      todo.push([nx, ny]);
    }
  }
  if (prev[tx + "," + ty] === undefined) { toast("You can't get there from here."); return; }
  for (p = [tx, ty]; p && !(p[0] === X.x && p[1] === X.y); p = prev[p[0] + "," + p[1]]) path.unshift(p);
  X.path = [[X.x, X.y]].concat(path);                   /* from the middle of your square first */
}

/* ------------------------------------------------------------ open floors */

/* Walking an open floor (docs/open-floors.md): one wide space, its bands of foes unseen
 * until you spot them. Each step onto a new square is a step of the rules lab's seeing
 * (core/next/seeing.c, in the arena's WebAssembly): every band in range checks, you
 * looking at it and it looking back, the rolls in the log. A band that sees you starts the
 * fight (an ambush, if you hadn't spotted it), on a 16 x 8 window of the floor. */
var LIGHT_OF = { forest: "day", mountain: "day", town: "dusk", dungeon: "night" };
var LIGHTS = ["day", "dusk", "night"];
var OUTCOME = ["not yet", "heard", "spotted", "seen"];
var WIN = [16, 8];       /* a fight's window: the battle's map, and the view */
var AMBUSH = 6;          /* how near a band you've spotted you can fall on it from */

function openFloor(n) {
  var o = X.o = ROOMS.buildOpen(X.yard, n);
  X.floor = n;
  X.f = { rooms: [{ i: 0, rows: o.rows, foes: [], doors: {}, stairs: o.stairs, cache: null, kind: "open" }], start: 0 };
  X.cleared = {}; X.taken = {}; X.seen = {}; X.parleyed = {};
  X.heard = [];
  X.seeTrace = [];
  X.fog = null;
  X.room = 0;
  X.settle = false;
  X.area = o.rows.slice();
  X.light = LIGHT_OF[lookOf(n).replace(/[0-9]+$/, "")] || "day";
  X.bands = o.bands.map(function (b, k) {
    return { k: k, x: b.x, y: b.y, foes: b.foes, hiding: b.hiding, stairs: b.stairs, parley: b.parley,
             spotted: 0, seen: 0, alert: 0, party_last: 255, band_last: 255, cleared: false };
  });
  at(o.start[0], o.start[1]);
  X.cam = camFor();
  show("fight");
  $("log").textContent = "";
  log("Yard " + X.yard + ", floor " + n + ": an open floor, " + o.w + " x " + o.h + ", by " + X.light +
      ". Somewhere on it, " + o.bands.length + " band" + (o.bands.length === 1 ? "" : "s") + " of foes.", "round");
  /* The dice of seeing: the yard's and the floor's, so a floor walked the same way rolls
   * the same (for tests, and to compare). */
  seeBegin(((X.yard * 31 + n * 977) & 0xFFFF) || 1);
  exploreView();
  seeStep();
}

/* Can you stand on (x, y): not wall, pit or hazard, nobody there (seen or not). */
function openFree(x, y) {
  if (x < 0 || y < 0 || x >= X.o.w || y >= X.o.h) return false;
  var t = Number(X.area[y][x]);
  if (t === 1 || t === 2 || t === 5) return false;
  if (openNpcs().some(function (n) { return n.x === x && n.y === y; })) return false;
  return !X.bands.some(function (b) {
    return !b.cleared && b.foes.some(function (f) { return f.x === x && f.y === y; });
  });
}

function openNpcs() {
  return X.o.people.filter(function (p) { return !(p.who === "courier" && X.pell); }).map(function (p) {
    return { who: p.who, name: NPC[p.who].name, figure: NPC[p.who].figure, x: p.x, y: p.y };
  });
}

/* The best of a list: the first of the highest (as the rules pick a group's best). */
function bestOf(list) {
  var b = 0, i;
  for (i = 1; i < list.length; ++i) if (list[i] > list[b]) b = i;
  return b;
}

function team() { return X.party.map(function (c) { return ROOMDATA.travelers[c]; }); }

/* The party's range: its best Notice / 5 squares, doubled by day, halved at night. */
function openSight() {
  var r = Math.floor(Math.max.apply(null, team().map(function (t) { return t.notice; })) / 5);
  r = X.light === "day" ? r * 2 : X.light === "night" ? Math.floor(r / 2) : r;
  return Math.max(1, r);
}

/* A band in words: "2 ash rats and a rust guard" (Cap: "2 ash rats...", "An ash rat"). */
function cap(t) { return t.replace(/^./, function (c) { return c.toUpperCase(); }); }
function bandName(b) {
  var count = {}, order = [];
  b.foes.forEach(function (f) {
    if (!count[f.name]) { count[f.name] = 0; order.push(f.name); }
    ++count[f.name];
  });
  return order.map(function (n) {
    var nm = ROOMDATA.foes[n].name.toLowerCase();
    return count[n] === 1 ? (/^[aeiou]/.test(nm) ? "an " : "a ") + nm : count[n] + " " + nm + "s";
  }).join(" and ");
}
/* "It" or "They", "looks" or "look": a band of one or more. */
function they(b, verb) { return b.foes.length > 1 ? verb : verb + "s"; }

/* The floor, the light, the party and the bands, as the seeing engine takes them (and the
 * bands as they stand: a rebuild after a fight carries them over). */
function seeBegin(seed) {
  var lines = ["floor " + X.o.w + " " + X.o.h].concat(X.area), r;
  lines.push("light " + X.light);
  team().forEach(function (t) { lines.push("traveler " + t.stealth + " " + t.notice); });
  X.seeMap = [];
  X.bands.forEach(function (b) {
    if (b.cleared) return;
    X.seeMap.push(b.k);
    lines.push(["band", b.x, b.y,
                Math.max.apply(null, b.foes.map(function (f) { return ROOMDATA.foes[f.name].sense; })),
                Math.max.apply(null, b.foes.map(function (f) { return ROOMDATA.foes[f.name].stealth; })),
                b.hiding ? 1 : 0, b.spotted, b.seen, b.alert, b.party_last, b.band_last].join(" "));
  });
  r = JSON.parse(rules.ar_see_begin(seed || 0, lines.join("\n") + "\n"));
  if (r.error) log("Seeing couldn't start: " + r.error, "bad");
}

/* A step onto a new square: the checks. True if it started something (a fight, a talk). */
function seeStep() {
  var r = JSON.parse(rules.ar_see_step(X.x, X.y, X.sneak ? 1 : 0, 0)), spotted = false, b;
  if (r.error) return false;
  r.bands.forEach(function (s, j) {
    b = X.bands[X.seeMap[j]];
    if (s[0] && !b.spotted) spotted = true;
    b.spotted = s[0]; b.seen = s[1]; b.alert = s[2]; b.party_last = s[3]; b.band_last = s[4];
  });
  r.events.forEach(function (e) { seeLog(e, X.bands[X.seeMap[e.band]]); });
  X.seeTrace.push({ x: X.x, y: X.y, sneak: !!X.sneak, events: r.events.map(function (e) {   /* for tests */
    return Object.assign({}, e, { band: X.seeMap[e.band] });
  }), fight: r.fight ? X.seeMap[r.fight - 1] + 1 : 0, ambush: r.ambush });
  if (r.fight) { openMeet(X.bands[X.seeMap[r.fight - 1]], r.ambush ? "foes" : ""); return true; }
  if (spotted) exploreView();                           /* a band spotted: drawn now */
  return false;
}

function signed(n) { return (n < 0 ? "−" : "+") + Math.abs(n); }

/* A check's TN, in words: its base and each modifier. */
function tnWords(e) {
  var parts = [e.base_rating ? "50 + Stealth " + e.base_rating : "80"];
  if (e.shift) parts.push(signed(e.shift) + " the others sneaking");
  [[1, 10, "dusk"], [2, 20, "night"], [4, e.dist_mod, "far"], [8, 20, "cover between"], [16, 10, "in cover"],
   [32, -20, "alert"], [64, -20, "a light"]].forEach(function (m) {
    if (e.mods & m[0]) parts.push(signed(m[1]) + " " + m[2]);
  });
  return parts.join(" ") + (parts.length > 1 ? " = " + e.tn : "");
}

/* One of the seeing engine's events, in the log. */
function seeLog(e, b) {
  var ts = team(), best, others, words, cls;
  if (e.kind === "party") {
    if (e.automatic) return log("Right beside you: " + bandName(b) + ".", "round");
    best = bestOf(ts.map(function (t) { return t.notice; }));
    others = ts.filter(function (t, i) { return i !== best; });
    words = "You look (" + e.d + " squares off): TN " + tnWords(e) + ".";
    e.help.forEach(function (h, i) {
      words += " " + others[i].name + " " + h.roll + " + " + h.rating + " = " + (h.roll + h.rating) + ", " +
        CHECKED[h.result] + (h.shift ? " (" + signed(h.shift) + ")" : "") + ";";
    });
    words += " " + ts[best].name + " rolls " + e.roll + " + " + e.rating + " = " + e.total + " against " + e.look_tn + ": " +
      CHECKED[e.result] + ". " + (e.outcome === 2 ? "Spotted: " + bandName(b) + ", not looking your way."
        : e.outcome === 1 ? "You hear something out there." : "Nothing yet.");
    if (e.outcome === 1) X.heard.push([b.x, b.y]);
    cls = "roll " + (e.outcome === 2 ? "good" : "");
  } else {
    if (e.automatic) return log(cap(bandName(b)) + ", right beside you, " + they(b, "see") + " you.", "bad");
    words = (b.spotted ? cap(bandName(b)) + " " + they(b, "look") : "Something out there looks") + " your way (" + e.d +
      " squares): TN " + tnWords(e) + ".";
    if (e.sneak.length) {
      best = bestOf(ts.map(function (t) { return t.stealth; }));
      others = ts.filter(function (t, i) { return i !== best; });
      words += " Sneaking: " + e.sneak.map(function (h, i) {
        return others[i].name + " " + h.roll + " + " + h.rating + " = " + (h.roll + h.rating) + ", " + CHECKED[h.result] +
          (h.shift ? " (" + signed(h.shift) + ")" : "");
      }).join("; ") + ".";
    }
    words += " " + (b.spotted && b.foes.length > 1 ? "They roll " : "It rolls ") + e.roll + " + " + e.rating + " = " + e.total + ": " + CHECKED[e.result] + ". " +
      (e.outcome === 3 ? "Seen!" : e.outcome === 1 ? "Heard something: alert now." : "Not seen.");
    cls = "roll " + (e.outcome === 3 ? "bad" : e.outcome === 1 ? "" : "good");
  }
  log(words, cls);
}

/* The foes drawn while walking: the bands you've spotted. */
function openShown() {
  var fs = [];
  X.bands.forEach(function (b) {
    if (b.cleared || !b.spotted) return;
    b.foes.forEach(function (f) { fs.push({ name: f.name, x: f.x, y: f.y }); });
  });
  return fs;
}

/* A band has seen you (or you fall on it): a parley first if it talks, else the fight. */
function openMeet(b, surprise) {
  held = {};
  X.path = null;
  if (b.parley && !X.parleyed[b.k] && TALK && TALK.park) {
    X.parleyed[b.k] = 1;
    b.spotted = 1;
    exploreView();
    log(cap(bandName(b)) + ": " + (b.foes.length > 1 ? "they call" : "it calls") + " out before anyone draws.", "round");
    return talk(b.foes[0].name, ROOMDATA.foes[b.foes[0].name].name + (b.foes.length > 1 ? " and the rest" : ""), function (sig) {
      if (sig.indexOf("leave") >= 0) {
        b.cleared = true;
        seeBegin(0);
        log("They let you by.", "good");
        exploreView();
      } else {
        openFight(b, "");
      }
    });
  }
  log(surprise === "foes" ? cap(bandName(b)) + ", on you before you saw them: an ambush. The first round is theirs."
      : surprise === "travelers" ? "You fall on " + bandName(b) + " before they see you: the first round is yours."
      : cap(bandName(b)) + ": " + (b.foes.length > 1 ? "they've" : "it's") + " seen you.", surprise === "travelers" ? "good" : "bad");
  return openFight(b, surprise);
}

/* The window a fight is on (docs/open-floors.md, Where the fight is): 16 x 8 inside the
 * floor, holding the band and the leader, its middle nearest the middle between them; if
 * they can't both fit, round the band. */
function fightWindow(b) {
  var xs = b.foes.map(function (f) { return f.x; }), ys = b.foes.map(function (f) { return f.y; }), best = null, bk, x0, y0, k;
  var mx = (Math.min.apply(null, xs) + Math.max.apply(null, xs)) / 2, my = (Math.min.apply(null, ys) + Math.max.apply(null, ys)) / 2;
  var cx = (mx + X.x) / 2, cy = (my + X.y) / 2;
  function holds(x0, y0, x, y) { return x >= x0 && y >= y0 && x < x0 + WIN[0] && y < y0 + WIN[1]; }
  for (y0 = 0; y0 <= X.o.h - WIN[1]; ++y0) {
    for (x0 = 0; x0 <= X.o.w - WIN[0]; ++x0) {
      if (!b.foes.every(function (f) { return holds(x0, y0, f.x, f.y); })) continue;
      k = (holds(x0, y0, X.x, X.y) ? 0 : 1000) +
        Math.abs(x0 + WIN[0] / 2 - (holds(x0, y0, X.x, X.y) ? cx : mx)) + Math.abs(y0 + WIN[1] / 2 - (holds(x0, y0, X.x, X.y) ? cy : my));
      if (best === null || k < bk) { best = [x0, y0]; bk = k; }
    }
  }
  return best || [0, 0];
}

/* The fight on the window: the battle engine's, as a room's (exploreFight). */
function openFight(b, surprise) {
  var ts = team(), win = fightWindow(b), wx = win[0], wy = win[1], rows = [], k, room, lead, fan, lines, was, names, seen = {};
  for (k = 0; k < WIN[1]; ++k) rows.push(X.area[wy + k].slice(wx, wx + WIN[0]));
  room = { rows: rows, foes: b.foes.map(function (f) { return { name: f.name, x: f.x - wx, y: f.y - wy }; }) };
  lead = [Math.max(0, Math.min(WIN[0] - 1, X.x - wx)), Math.max(0, Math.min(WIN[1] - 1, X.y - wy))];
  fan = ROOMS.fanOut(room, lead, ts.length + 1);
  if (fan.length > 1 && (STANDS_OPEN.indexOf(Number(rows[lead[1]][lead[0]])) < 0 ||
                         room.foes.some(function (f) { return f.x === lead[0] && f.y === lead[1]; }))) fan.shift();
  lines = ["map " + WIN[0] + " " + WIN[1]].concat(rows.map(function (row) {
    return row.split("").map(function (c) { return MAPCH[c]; }).join("");
  }));
  names = ts.map(function (t) { return t.name; });
  was = ts.map(function (t, k) { return [fight.shown[k].x - wx, fight.shown[k].y - wy]; });
  ts.forEach(function (t, k) {
    var p = fan[Math.min(k, fan.length - 1)];
    lines.push("traveler " + p[0] + " " + p[1] + " " + t.passport + " " + t.weapon);
  });
  room.foes.forEach(function (f) {
    var fd = ROOMDATA.foes[f.name], same = room.foes.filter(function (g) { return g.name === f.name; }).length > 1;
    seen[f.name] = (seen[f.name] || 0) + 1;
    lines.push("foe " + f.x + " " + f.y + " " + fd.line + " level " + X.floor);
    names.push(fd.name + (same ? " " + seen[f.name] : ""));
  });
  ts.forEach(function (t, k) { t.powers.forEach(function (p) { lines.push("power " + k + " " + p[0] + " " + p[1]); }); });
  if (surprise) lines.push("surprise " + surprise);
  X.fightBand = b;
  X.win = win;
  X.before = X.trail.map(function (p) { return [Math.round(p[0]), Math.round(p[1])]; }).reverse();
  X.before.unshift([X.x, X.y]);
  S = { code: "E14-" + X.yard + "-" + X.floor + "-" + (b.k + 1), title: "Floor " + X.floor + ", band " + (b.k + 1),
        explore: true, lab: { won: "?", rounds: "?" },
        native: { spec: lines.join("\n") + "\n",
                  figures: ts.map(function (t) { return t.figure; }).concat(room.foes.map(function (f) { return ROOMDATA.foes[f.name].figure; })),
                  names: names, pack: X.pack.slice(), skills: ts[0].skills } };
  held = {};
  newFight();
  fight.look = lookOf(X.floor);
  fight.dress = function (x, y, t) { return dress(X.f.rooms[0], x + wx, y + wy, t); };
  fight.gridFrom = performance.now();
  ts.forEach(function (t, k) {
    var s = fight.shown[k], to = fight.st.fighters[k];
    s.x = was[k][0]; s.y = was[k][1];
    tween(s, to.x, to.y, 260);
  });
  resize();
  cards();
  advance();
}
var STANDS_OPEN = [0, 3, 4, 6];

/* After a fight on the window: won, the band's gone and you walk on from where you
 * stood; fled, you're back along your way, the band still there and alert; lost, it ends. */
function openAfter(result) {
  var me0 = fight.st.fighters[0], b = X.fightBand, w = X.win, back;
  X.pack = fight.pack.slice();
  if (result === 1) {
    b.cleared = true;
    at(me0.x + w[0], me0.y + w[1]);
    if (!openFree(X.x, X.y)) at(X.before[0][0], X.before[0][1]);
    log("The band is gone. You catch your breath: full health again.", "good");
  } else if (result === 3) {
    /* Back along your way: the first square of it 6 from them, or the farthest it goes. */
    var gap = function (p) { return Math.min.apply(null, b.foes.map(function (f) { return Math.max(Math.abs(f.x - p[0]), Math.abs(f.y - p[1])); })); };
    back = X.before.filter(function (p) { return openFree(p[0], p[1]); });
    back = back.filter(function (p) { return gap(p) >= 6; })[0] ||
      back.reduce(function (a, p) { return gap(p) > gap(a) ? p : a; }, back[0] || X.before[0]);
    at(back[0], back[1]);
    b.seen = 0; b.alert = 1; b.spotted = 1;
    b.band_last = b.party_last = Math.max(Math.abs(b.x - X.x), Math.abs(b.y - X.y));
    log("You get back the way you came. They're still there, and alert now.", "round");
  } else {
    X.lost = true;
    log("You go down. The descent ends here.", "bad");
  }
  X.cam = camFor();
  seeBegin(0);
  exploreView();
}

/* Where you've stepped: what sees you, then a crate or the stairs. */
function openArrive() {
  var o = X.o, id;
  if (seeStep()) return;
  o.caches.forEach(function (c, k) {
    if (X.taken[k] || c.x !== X.x || c.y !== X.y) return;
    X.taken[k] = 1;
    id = ROOMDATA.cache[c.item];
    if (X.pack.indexOf(id) < 0 && X.pack.length < 6) X.pack.push(id);
    log("In the crate: " + itemOf(id).display + ". It's in your pack (P in a fight).", "good");
    exploreSide();
  });
  if (X.x === o.stairs[0] && X.y === o.stairs[1]) {
    log("Down the stairs.", "round");
    held = {};
    return exploreFloor(X.floor + 1);
  }
}

/* A band you've spotted, not yet seen you, near enough to fall on. */
function ambushable() {
  var near = null, nd = AMBUSH + 1;
  X.bands.forEach(function (b) {
    if (b.cleared || !b.spotted || b.seen) return;
    var d = Math.max(Math.abs(b.x - X.x), Math.abs(b.y - X.y));
    if (d < nd) { near = b; nd = d; }
  });
  return near;
}

function openButtons() {
  var b = ambushable();
  return [["S", X.sneak ? "Sneaking: half speed" : "Walking: S to sneak", function () {
            X.sneak = !X.sneak;
            log(X.sneak ? "You sneak: half speed, and a band rolls against 50 + your best Stealth, the others helping or not."
                        : "You walk openly: a band rolls against 80.", "round");
            actions(); exploreSide();
          }, false, "", false, "toggle"],
          ["L", "Light: " + X.light, function () {
            X.light = LIGHTS[(LIGHTS.indexOf(X.light) + 1) % LIGHTS.length];
            seeBegin(0);
            log("Now it's " + X.light + ".", "round");
            actions(); exploreSide();
          }, false, "", false, "toggle"]]
    .concat(b ? [["A", "Ambush " + bandName(b),
                  function () { openMeet(b, "travelers"); }, false, "", true]] : []);
}

/* The side panel, on an open floor. */
function openSide() {
  var c = $("cards"), mm = el("canvas", "minimap"), ts = team(), here = nearNpc(), spotted;
  c.textContent = "";
  mm.id = "minimap";
  mm.width = X.o.w * MM;
  mm.height = X.o.h * MM;
  mm.title = "The floor: what you've seen, the bands spotted (red), sounds (yellow), the view's rectangle";
  c.append(el("h2", null, "Floor " + X.floor), mm);
  drawMinimap();
  c.append(el("p", "note", (X.sneak ? "Sneaking" : "Walking openly") + ", by " + X.light + "; you see " + openSight() + " squares."));
  ts.forEach(function (t, k) {
    var card = el("div", "card traveler");
    card.append(el("div", "nm", (k + 1) + ". " + t.name + ", level 1" + (k ? "" : " · leads")),
                el("div", "gear", "Notice " + t.notice + " · Stealth " + t.stealth));
    c.append(card);
  });
  spotted = X.bands.filter(function (b) { return b.spotted && !b.cleared; });
  c.append(el("p", "note", spotted.length ? "Spotted: " + spotted.map(function (b) {
    return bandName(b) + (b.seen ? "" : b.alert ? " (alert)" : " (not looking)");
  }).join("; ") + "." : "No band spotted yet."));
  c.append(el("p", "note", "Pack (the party's): " +
              (X.pack.length ? X.pack.map(function (id) { return itemOf(id).display; }).join(", ") : "empty")));
  if (here) c.append(el("p", "note", here.name + ": press T, or click them, to talk."));
  if (X.pell === "follows") c.append(el("p", "note", "Pell is following you."));
}

function openMinimap(c) {
  var g = c.getContext("2d"), w = X.o.w, h = X.o.h, x, y, cam = fight && fight.cam;
  function seen(x, y) { return X.fog[y * w + x]; }
  g.fillStyle = "#000";
  g.fillRect(0, 0, c.width, c.height);
  for (y = 0; y < h; ++y)
    for (x = 0; x < w; ++x)
      if (seen(x, y)) { g.fillStyle = MM_COLOUR[Number(X.area[y][x])] || MM_COLOUR[0]; g.fillRect(x * MM, y * MM, MM, MM); }
  if (seen(X.o.stairs[0], X.o.stairs[1])) { g.fillStyle = "#fff"; g.fillRect(X.o.stairs[0] * MM, X.o.stairs[1] * MM, MM, MM); }
  X.o.caches.forEach(function (o, k) {
    if (!X.taken[k] && seen(o.x, o.y)) { g.fillStyle = "#e0a030"; g.fillRect(o.x * MM, o.y * MM, MM, MM); }
  });
  X.heard.forEach(function (p) { g.fillStyle = "#e8e040"; g.fillRect(p[0] * MM, p[1] * MM, MM, MM); });
  openShown().forEach(function (f) { g.fillStyle = "#ff4040"; g.fillRect(f.x * MM, f.y * MM, MM, MM); });
  if (cam && fight.view) {
    g.strokeStyle = "#fff";
    g.lineWidth = 1;
    g.strokeRect(Math.round(cam.x * MM) + 0.5, Math.round(cam.y * MM) + 0.5, fight.view[0] * MM - 1, fight.view[1] * MM - 1);
  }
  g.fillStyle = "#40ff80";
  g.fillRect(Math.round(X.px * MM) - 1, Math.round(X.py * MM) - 1, MM + 2, MM + 2);
}

/* The stairs, the crates and the people, over the floor's tiles. */
function openDraw() {
  drawStairs(X.o.stairs[0] * SQ, X.o.stairs[1] * SQ);
  X.o.caches.forEach(function (c, k) { if (!X.taken[k]) drawCrate(c.x * SQ, c.y * SQ); });
  openNpcs().forEach(function (n) { figureAt(n.figure, n.x, n.y); });
}

/* ------------------------------------------------------------------ talk */

/* Talk (docs/rooms.md, Talk): the people in the rooms, and parleys, are a Departure in
 * Quest Script (content/sidings/yards-talk/), played by the game's own story VM
 * (story.js, tools/arena/web/story.c). The leader boards it at the top of a descent; it
 * waits at a menu for the page (every label @...) between conversations, so it remembers
 * the descent; a menu of one @ label is a signal back (@fight, @leave, @join, @gone,
 * @stay). Checks are rolled for the leader by the rules (v0, as the story VM is). */
var NPC = { trader: { name: "Vell", figure: "GLASSFOLK" }, courier: { name: "Pell", figure: "HUMAN" } };
var TALK = null;            /* the story now: {want, run, park, labels, now: {who, signals, done}} */
var CHECKED = ["fail", "cost", "success", "crit"];

/* Board the leader (a new descent). One story at a time: the last descent's is told to
 * end first (its @end), and only then is this one boarded. */
var STORY = { M: null, loading: false, want: null };

function storyBoard() {
  if (typeof ArenaStory === "undefined") return;
  STORY.want = { passport: ROOMDATA.travelers[X.party[0]].passport, yard: X.yard };
  storyNext();
}

function storyNext() {
  var t = TALK, M = STORY.M, want = STORY.want;
  if (!M) {
    if (STORY.loading) return;
    STORY.loading = true;
    ArenaStory({
      onText: function (text) { if (TALK && TALK.now) talkLine(text); },
      onCheck: function (rating, roll, total, tn, result) {
        if (TALK && TALK.now) {
          talkLine(rating + " check: rolled " + roll + ", " + total + " against " + tn + ": " + CHECKED[result] + ".",
                   "roll " + (result >= 2 ? "good" : result === 1 ? "" : "bad"));
        }
      },
      onError: function (msg) { log("The story stopped: " + msg, "bad"); },
      onMenu: storyMenu
    }).then(function (m) { STORY.M = m; storyNext(); });
    return;
  }
  if (t) {
    if (t.want !== want && t.park && !t.now) {          /* waiting: end it; this one boards after */
      var park = t.park;
      t.park = null;
      park(t.labels.indexOf("@end"));
    }
    return;
  }
  t = TALK = { want: want, park: null, labels: null, now: null };
  t.run = M.ccall("st_start", "number", ["string", "number"], [want.passport, want.yard], { async: true })
    .then(function (r) {
      if (r === 2) log("The story couldn't start: " + M.ccall("st_error", "string", [], []), "bad");
      if (TALK === t) TALK = null;
      if (STORY.want !== t.want) storyNext();
    });
}

/* A menu from the story: the page's own (@...), or the player's. */
function storyMenu(labels) {
  var t = TALK;
  if (labels.every(function (l) { return l.charAt(0) === "@"; })) {
    if (labels.indexOf("@end") >= 0) {                  /* waiting: a conversation is over */
      if (t.now) talkDone();
      return new Promise(function (res) {
        t.park = res; t.labels = labels;
        if (t.want !== STORY.want) storyNext();         /* a new descent began meanwhile */
      });
    }
    if (labels.length === 1) { if (t.now) t.now.signals.push(labels[0].slice(1)); return 0; }
    return Math.max(0, labels.indexOf("@" + (t.now ? t.now.who : "")));
  }
  return new Promise(function (res) { talkChoices(labels, res); });
}

/* Someone in room r to talk to, if they're still there: {who, name, figure}. */
function npcIn(r) {
  if (!r || !r.talk) return null;
  if (r.talk.who === "courier" && X.pell) return null;  /* following, or gone */
  return { who: r.talk.who, name: NPC[r.talk.who].name, figure: NPC[r.talk.who].figure, room: r };
}

function npcAt(x, y) {
  if (X.open) return openNpcs().filter(function (n) { return n.x === x && n.y === y; })[0] || null;
  var i = X.scroll ? roomAt(x, y) : X.room, r = i >= 0 ? X.f.rooms[i] : null, n = npcIn(r);
  return n && r.talk.x === x - ox(i) && r.talk.y === y - oy(i) ? n : null;
}

/* Who's next to the leader to talk to (8 ways). */
function nearNpc() {
  if (X.open) return openNpcs().filter(function (n) { return Math.max(Math.abs(X.x - n.x), Math.abs(X.y - n.y)) <= 1; })[0] || null;
  var r = roomOf(), n = npcIn(r);
  if (!n) return null;
  return Math.max(Math.abs(X.x - ox(r.i) - r.talk.x), Math.abs(X.y - oy(r.i) - r.talk.y)) <= 1 ? n : null;
}

function talkTo(n) {
  if (mode !== "explore") return;
  talk(n.who, n.name, function (sig) {
    if (n.who === "courier") {
      if (sig.indexOf("join") >= 0) { X.pell = "follows"; log("Pell follows you, a step behind.", "good"); }
      if (sig.indexOf("gone") >= 0) { X.pell = "gone"; log("Pell is gone.", "round"); }
    }
    if (sig.indexOf("stay") >= 0) { X.pell = "safe"; log("Pell stays at Vell's camp.", "good"); }
    setMode("explore");
  });
}

/* A room with foes: if they talk first (docs/rooms.md, People), a parley, which ends in
 * the fight or with them letting you by; else the fight. */
function exploreMeet() {
  var r = roomOf();
  if (r.parley && !X.parleyed[r.i] && TALK && TALK.park) {
    X.parleyed[r.i] = 1;
    if (!X.scroll) exploreView();
    held = {};
    var f = r.foes[0];
    return talk(f.name, ROOMDATA.foes[f.name].name + (r.foes.length > 1 ? " and the rest" : ""), function (sig) {
      if (sig.indexOf("leave") >= 0) {
        X.cleared[r.i] = 1;
        log("They let you by. Room " + (r.i + 1) + " is clear without a fight.", "good");
        exploreView();
      } else {
        exploreFight();
      }
    });
  }
  return exploreFight();
}

/* A conversation: with `who` (the story's @label: trader, courier, or a foe's name), the
 * panel titled `title`; done(signals) when the story is waiting again. */
function talk(who, title, done) {
  var t = TALK, p, k;
  if (!t || !t.park) { toast("Nobody's listening (the story hasn't started)."); return done([]); }
  setMode("talk");
  $("talk").hidden = false;
  $("talk-who").textContent = title;
  $("talk-lines").textContent = "";
  $("talk-choices").textContent = "";
  /* The pack, into the story's copy of the leader, so `has` and `take` see it. */
  p = STORY.M._malloc(4 * 6);
  for (k = 0; k < 6; ++k) STORY.M.HEAP32[(p >> 2) + k] = X.pack[k] || 0;
  STORY.M._st_pack(p, Math.min(6, X.pack.length));
  STORY.M._free(p);
  t.now = { who: who, signals: [], done: done };
  var park = t.park;
  t.park = null;
  park(t.labels.indexOf("@" + Math.min(X.floor, 8)));
}

function talkLine(text, cls) {
  var lines = $("talk-lines"), para = el("p", cls || null, text);
  lines.append(para);
  lines.scrollTop = lines.scrollHeight;
}

function talkChoices(labels, answer) {
  var ol = $("talk-choices");
  ol.textContent = "";
  TALK.answer = function (k) {
    if (k < 0 || k >= labels.length) return;
    ol.textContent = "";
    TALK.answer = null;
    if (!TALK.reading) talkLine("“" + labels[k] + "”", "said");
    answer(k);
  };
  labels.forEach(function (l, k) {
    var li = el("li"), b = el("button");
    b.type = "button";
    b.append(el("kbd", null, String(k + 1)), document.createTextNode(" " + l));
    b.onclick = function () { if (TALK && TALK.answer) TALK.answer(k); };
    li.append(b);
    ol.append(li);
  });
  var first = ol.querySelector("button");
  if (first) first.focus({ preventScroll: true });
}

/* The story is waiting again: what it gave and took lands in the pack. */
function talkDone() {
  var t = TALK, now = t.now, p = STORY.M._malloc(4 * 6), n = STORY.M._st_pack_now(p), after = [], k;
  for (k = 0; k < n; ++k) after.push(STORY.M.HEAP32[(p >> 2) + k]);
  STORY.M._free(p);
  after.filter(function (id) { return X.pack.indexOf(id) < 0; }).forEach(function (id) {
    log("You get " + itemOf(id).display + ": it's in your pack.", "good");
  });
  X.pack.filter(function (id) { return after.indexOf(id) < 0; }).forEach(function (id) {
    log("You hand over " + itemOf(id).display + ".", "round");
  });
  X.pack = after;
  t.now = null;
  /* What the story said last stays up until it's read. */
  var lines = $("talk-lines").children, last = lines[lines.length - 1];
  if (last && !last.classList.contains("said")) {
    TALK.reading = true;
    return talkChoices(["Go on"], function () {
      TALK.reading = false;
      $("talk").hidden = true;
      now.done(now.signals);
    });
  }
  $("talk").hidden = true;
  now.done(now.signals);
}

/* For tests: the panel as it stands, and a choice. */
function talkState() {
  return { open: !$("talk").hidden, who: $("talk-who").textContent,
           lines: Array.from($("talk-lines").children).map(function (p) { return p.textContent; }),
           choices: Array.from($("talk-choices").querySelectorAll("button")).map(function (b) { return b.textContent.replace(/^\d+ /, ""); }),
           waiting: !!(TALK && TALK.park && !TALK.reading), pell: X && X.pell, pack: X && X.pack };
}

/* A room's fight: the battle engine's, on the room's map (docs/rooms.md, Exploring). */
function exploreFight() {
  var r = roomOf(), team = X.party.map(function (c) { return ROOMDATA.travelers[c]; }), fs = foesIn(r);
  var names = team.map(function (t) { return t.name; }), lines, seen = {}, was, fan;
  lines = ["map " + ROOMS.W + " " + ROOMS.H].concat(r.rows.map(function (row) {
    return row.split("").map(function (c) { return MAPCH[c]; }).join("");
  }));
  /* The party fans out round the leader, in marching order (docs/rooms.md, The party). */
  var lx = X.x - ox(r.i), ly = X.y - oy(r.i);
  fan = ROOMS.fanOut(r, [lx, ly], team.length);
  was = team.map(function (t, k) { return [fight.shown[k].x - ox(r.i), fight.shown[k].y - oy(r.i)]; });
  team.forEach(function (t, k) {
    var at0 = fan[Math.min(k, fan.length - 1)];
    lines.push("traveler " + at0[0] + " " + at0[1] + " " + t.passport + " " + t.weapon);
  });
  fs.forEach(function (f) {
    var fd = ROOMDATA.foes[f.name], same = fs.filter(function (g) { return g.name === f.name; }).length > 1;
    seen[f.name] = (seen[f.name] || 0) + 1;
    lines.push("foe " + f.x + " " + f.y + " " + fd.line + " level " + X.floor);
    names.push(fd.name + (same ? " " + seen[f.name] : ""));
  });
  team.forEach(function (t, k) { t.powers.forEach(function (p) { lines.push("power " + k + " " + p[0] + " " + p[1]); }); });
  S = { code: "E13-" + X.yard + "-" + X.floor + "-" + (r.i + 1), title: "Floor " + X.floor + ", room " + (r.i + 1),
        explore: true, lab: { won: "?", rounds: "?" },
        native: { spec: lines.join("\n") + "\n",
                  figures: team.map(function (t) { return t.figure; }).concat(fs.map(function (f) { return ROOMDATA.foes[f.name].figure; })),
                  names: names, pack: X.pack.slice(), skills: team[0].skills } };
  held = {};
  newFight();
  dressFight(r);
  /* Everyone to their squares, and the grid comes up (docs/rooms.md, Exploring). */
  fight.gridFrom = performance.now();
  team.forEach(function (t, k) {
    var s = fight.shown[k], to = fight.st.fighters[k];
    s.x = was[k][0]; s.y = was[k][1];
    tween(s, to.x, to.y, 260);
  });
  resize();
  cards();
  advance();
}

/* The fight's over: back to walking (docs/rooms.md, Exploring). */
function exploreAfter(result) {
  if (X.open) return openAfter(result);
  var r = roomOf(), me0 = fight.st.fighters[0];
  X.pack = fight.pack.slice();
  if (result === 1) {
    /* Everyone's up again (turn.md, After a fight), and the leader leads on from where
     * they stood. */
    X.cleared[r.i] = 1;
    at(me0.x, me0.y);
    if (!walkable(r, me0.x, me0.y)) { var p = inside(r, r.doors[Object.keys(r.doors)[0]]); at(p[0], p[1]); }
    log("The room is yours. You catch your breath: full health again.", "good");
  } else if (result === 3 && X.from) {
    X.room = X.from.room;
    at(X.from.back[0], X.from.back[1]);
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
            ["N", "A new yard", function () { exploreStart(X.party, 1 + Math.floor(Math.random() * 65535), viewArg(), X.look); }],
            ["Esc", "Back to the scenarios", intro]];
  }
  if (mode === "talk") {
    return [["1-9", "Say something: a number, or click it", null, false, "", false, "hint"]];
  }
  var near = nearNpc();
  return [["Arrows", "Walk: hold them down (numpad: 8 ways), or click a square", null, false, "", false, "hint"]]
    .concat(near ? [["T", "Talk to " + near.name, function () { talkTo(near); }, false, "", true]] : [])
    .concat([
          ["N", "A new yard", function () { exploreStart(X.party, 1 + Math.floor(Math.random() * 65535), viewArg(), X.look); }],
          ["V", X.open ? "View: open floor" : X.scroll ? "View: scrolling" : "View: one room a screen", function () {
            exploreStart(X.party, X.yard, X.open ? false : X.scroll ? "open" : true, X.look);
          }, false, "", false, "toggle"]]).concat(X.open ? openButtons() : []).concat(X.scroll ? [
          ["Z", "Zoom: " + viewSize()[0] + " x " + viewSize()[1] + " squares", exploreZoom, false, "", false, "toggle"]] : []).concat([
          ["gap"],
          ["X", "Leave", intro]]);
}

/* Stairs, crates and people, drawn over the room's tiles; and the courier, following. */
function exploreDraw() {
  if (X.open) openDraw();
  else (X.scroll ? X.f.rooms : [roomOf()]).forEach(drawThings);
  if (X.pell === "follows") {
    var f = follower(X.party.length);
    figureAt(NPC.courier.figure, f.x, f.y, f.alpha);
  }
}

function figureAt(name, x, y, alpha) {
  ctx.globalAlpha = alpha === undefined ? 1 : alpha;
  ctx.fillStyle = "rgba(0,0,0,.35)";
  ctx.beginPath();
  ctx.ellipse(x * SQ + 16, y * SQ + 29, 9, 2.5, 0, 0, 2 * Math.PI);
  ctx.fill();
  ctx.drawImage(figureSprite(name), x * SQ + 3, y * SQ + 8);
  ctx.globalAlpha = 1;
}

function drawThings(r) {
  var x, y, k, x0 = ox(r.i) * SQ, y0 = oy(r.i) * SQ, who = npcIn(r);
  if (who) figureAt(who.figure, ox(r.i) + r.talk.x, oy(r.i) + r.talk.y);
  if (r.stairs) drawStairs(x0 + r.stairs[0] * SQ, y0 + r.stairs[1] * SQ);
  if (r.cache && !X.taken[r.i]) drawCrate(x0 + r.cache.x * SQ, y0 + r.cache.y * SQ);
}

/* The stairs down and a crate, at pixel x, y. */
function drawStairs(x, y) {
  var k;
  ctx.fillStyle = "#0b0b10";
  ctx.fillRect(x + 4, y + 4, SQ - 8, SQ - 8);
  for (k = 0; k < 4; ++k) {
    ctx.fillStyle = "rgba(232,197,71," + (0.9 - k * 0.2) + ")";
    ctx.fillRect(x + 6 + k * 2, y + 7 + k * 5, SQ - 12 - k * 4, 3);
  }
}

function drawCrate(x, y) {
  ctx.fillStyle = "#6b4a2b"; ctx.fillRect(x + 7, y + 11, 18, 13);
  ctx.fillStyle = "#a0753f"; ctx.fillRect(x + 7, y + 11, 18, 4);
  ctx.fillStyle = "#e8c547"; ctx.fillRect(x + 15, y + 15, 2, 3);
}

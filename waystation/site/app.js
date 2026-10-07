// The Waystation website (W1, docs/waystation-web.md). Every rule here is the rules
// core's own, through WebAssembly (waystation/ws.c); this file only draws the pages.
"use strict";

var Module = {
  onRuntimeInitialized: function () { start(); }
};

var REG = null;          // names, from registry.json
var RULES = null;        // the creation rules' numbers, from the core
var traveler = null;     // the traveler on the Passport and sheet pages

function call(name, types, args) {
  var out = Module.ccall(name, "string", types || [], args || []);
  return out.charAt(0) === "{" || out.charAt(0) === "[" ? JSON.parse(out) : out;
}

function $(id) { return document.getElementById(id); }

function el(tag, attrs, children) {
  var e = document.createElement(tag);
  Object.keys(attrs || {}).forEach(function (k) {
    if (k === "text") e.textContent = attrs[k];
    else if (k === "class") e.className = attrs[k];
    else e.setAttribute(k, attrs[k]);
  });
  (children || []).forEach(function (c) { if (c) e.appendChild(c); });
  return e;
}

function lines(password) {
  return (password.match(/.{1,20}/g) || []).join("\n");
}

/* ------------------------------------------------------------------- tabs */

function show(tab) {
  document.querySelectorAll(".tab").forEach(function (t) {
    t.setAttribute("aria-selected", String(t.dataset.tab === tab));
  });
  document.querySelectorAll(".panel").forEach(function (p) { p.hidden = p.id !== tab; });
  if (tab === "sheet") drawSheet();
  if (tab === "stamp") $("t-who").textContent = traveler
    ? "Stamping into " + traveler.name + "'s Passport."
    : "Read a Passport first (Your Passport), then stamp it here.";
}

/* ---------------------------------------------------------------- creator */

var rolled = null;       // the rolled set, if rolling
var rollsLeft = 0;

function creatorMode() {
  return document.querySelector("input[name=c-mode]:checked").value;
}

function drawCreatorStats() {
  var t = $("c-stats");
  var buy = creatorMode() === "buy";
  t.innerHTML = "";
  t.appendChild(el("tr", {}, [el("th", { text: "Stat" }),
    el("th", { class: "num", text: buy ? "Bought" : "Rolled" })]));
  REG.stats.forEach(function (name, i) {
    var cell;
    if (buy) {
      cell = el("input", { type: "number", id: "c-stat-" + i, min: RULES.buy_base,
                           max: RULES.buy_max, value: RULES.buy_base + 25, "aria-label": name });
    } else {
      cell = el("select", { id: "c-stat-" + i, "aria-label": name });
      (rolled || []).forEach(function (v, j) {
        var o = el("option", { value: j, text: String(v) });
        if (j === i) o.selected = true;
        cell.appendChild(o);
      });
    }
    cell.addEventListener("input", preview);
    t.appendChild(el("tr", {}, [el("td", { text: name }), el("td", { class: "num" }, [cell])]));
  });
}

function baseStats() {
  var out = [];
  var used = {};
  for (var i = 0; i < 6; ++i) {
    var v = $("c-stat-" + i).value;
    if (creatorMode() === "roll") {
      if (!rolled) return { error: "Roll a set first." };
      if (used[v]) return { error: "Use each rolled number once." };
      used[v] = true;
      out.push(rolled[Number(v)]);
    } else {
      out.push(Number(v));
    }
  }
  return { stats: out };
}

function create() {
  var base = baseStats();
  if (base.error) return { ok: false, error: base.error };
  return call("ws_create",
    ["string", "number", "number", "number", "number", "number", "number", "number", "number",
     "number", "number"],
    [$("c-name").value.trim(), Number($("c-race").value), Number($("c-class").value)]
      .concat(base.stats, [Number($("c-tag").value), creatorMode() === "roll" ? 1 : 0]));
}

function preview() {
  var note = $("c-mode-note");
  var spent = 0;
  if (creatorMode() === "buy") {
    for (var i = 0; i < 6; ++i) spent += Number($("c-stat-" + i).value) - RULES.buy_base;
    note.textContent = "Every stat starts at " + RULES.buy_base + ". Spend " + RULES.buy_points +
      " points, one for each +1, none above " + RULES.buy_max + ". Points left: " +
      (RULES.buy_points - spent) + ".";
  } else {
    note.textContent = "Each stat is 3d6 x 5 (15 to 90). Roll a set, then put the numbers " +
      "where you like. You can roll again " + RULES.rerolls + " times; the last set stands.";
  }
  var tags = REG.classes[$("c-class").value].tags;
  Array.prototype.forEach.call($("c-tag").options, function (o) {
    o.disabled = tags.indexOf(Number(o.value)) >= 0;
  });
  if ($("c-tag").selectedOptions[0] && $("c-tag").selectedOptions[0].disabled) {
    var free = Array.prototype.find.call($("c-tag").options, function (o) { return !o.disabled; });
    $("c-tag").value = free.value;
  }
  var made = $("c-name").value.trim() ? create() : { ok: false, error: "Name your traveler." };
  var box = $("c-preview");
  box.innerHTML = "";
  $("c-error").textContent = made.ok ? "" : made.error.charAt(0).toUpperCase() + made.error.slice(1) + (/[.!?]$/.test(made.error) ? "" : ".");
  if (!made.ok) return;
  box.appendChild(el("p", { text: "With your race and class: " + REG.stats.map(function (s, i) {
    return s + " " + made.stats[i];
  }).join(", ") + ". Health " + made.health + ". Tagged: " + made.skills.map(function (s, i) {
    return s.tagged ? REG.skills[i].name : null;
  }).filter(Boolean).join(", ") + "." }));
}

function setupCreator() {
  Object.keys(REG.races).forEach(function (id) {
    var r = REG.races[id];
    $("c-race").appendChild(el("option", { value: id, text: r.name + " (+" + RULES.race_bonus + " " + REG.stats[r.bonus] + ")" }));
  });
  Object.keys(REG.classes).forEach(function (id) {
    var c = REG.classes[id];
    $("c-class").appendChild(el("option", { value: id, text: c.name + " (+" + RULES.class_bonus + " " +
      REG.stats[c.bonus] + "; " + c.tags.map(function (t) { return REG.skills[t].name; }).join(", ") + ")" }));
  });
  Object.keys(REG.skills).forEach(function (id) {
    $("c-tag").appendChild(el("option", { value: id, text: REG.skills[id].name }));
  });
  document.querySelectorAll("input[name=c-mode]").forEach(function (r) {
    r.addEventListener("change", function () {
      $("c-roll").hidden = creatorMode() !== "roll";
      drawCreatorStats();
      preview();
    });
  });
  rollsLeft = RULES.rerolls + 1;
  $("c-roll-button").addEventListener("click", function () {
    if (rollsLeft <= 0) return;
    var seed = new Uint16Array(1);
    crypto.getRandomValues(seed);
    rolled = call("ws_roll", ["number"], [seed[0]]);
    rollsLeft -= 1;
    $("c-rolled").textContent = "Rolled: " + rolled.join(", ");
    $("c-rolls-left").textContent = rollsLeft ? "Rolls left: " + rollsLeft : "That set stands.";
    $("c-roll-button").disabled = rollsLeft <= 0;
    drawCreatorStats();
    preview();
  });
  ["c-name", "c-race", "c-class", "c-tag"].forEach(function (id) {
    $(id).addEventListener("input", preview);
  });
  $("creator").addEventListener("submit", function (e) {
    e.preventDefault();
    var made = create();
    if (!made.ok) return;
    traveler = made;
    $("p-text").value = lines(made.passport);
    drawPassport();
    show("passport");
  });
  drawCreatorStats();
  preview();
}

/* --------------------------------------------------------------- passport */

function drawPassport() {
  var t = traveler;
  $("p-view").hidden = !t;
  if (!t) return;
  var s = $("p-summary");
  s.innerHTML = "";
  s.appendChild(el("p", { class: "big", text: t.name + ", " + REG.races[t.race].name + " " +
    REG.classes[t.class].name + ", level " + t.level }));
  s.appendChild(el("p", { text: "XP " + t.xp + " of 100 to the next level. Health " + t.health +
    ". Debt " + t.debt + "." }));
  $("p-points").textContent = t.stat_points || t.skill_points
    ? "To spend: " + t.stat_points + " stat point" + (t.stat_points === 1 ? "" : "s") + " and " +
      t.skill_points + " skill point" + (t.skill_points === 1 ? "" : "s") + "."
    : "No points to spend. Levelling up brings 1 stat point and " + t.skill_points_per_level +
      " skill point" + (t.skill_points_per_level === 1 ? "" : "s") + " (1 + Wits / 20).";

  var st = $("p-stats");
  st.innerHTML = "";
  st.appendChild(el("tr", {}, [el("th", { text: "Stat" }), el("th", { class: "num", text: "" }), el("th", {})]));
  REG.stats.forEach(function (name, i) {
    var b = el("button", { type: "button", class: "small", "aria-label": "Raise " + name, text: "+1" });
    b.disabled = !t.stat_points || t.stats[i] >= 100;
    b.addEventListener("click", function () { spend("ws_raise_stat", i); });
    st.appendChild(el("tr", {}, [el("td", { text: name }), el("td", { class: "num", text: String(t.stats[i]) }),
      el("td", {}, [b])]));
  });

  var sk = $("p-skills");
  sk.innerHTML = "";
  sk.appendChild(el("tr", {}, [el("th", { text: "Skill" }), el("th", { class: "num", text: "Rating" }),
    el("th", { class: "num", text: "Trained" }), el("th", {})]));
  t.skills.forEach(function (s, i) {
    var b = el("button", { type: "button", class: "small",
      "aria-label": "Raise " + REG.skills[i].name + " for " + s.cost, text: "+" + (s.tagged ? 2 : 1) });
    b.title = "Costs " + s.cost + " skill point" + (s.cost === 1 ? "" : "s");
    b.disabled = t.skill_points < s.cost || s.training >= 100;
    b.addEventListener("click", function () { spend("ws_raise_skill", i); });
    sk.appendChild(el("tr", {}, [
      el("td", { class: s.tagged ? "tagged" : "", text: REG.skills[i].name + (s.tagged ? " (tagged)" : "") }),
      el("td", { class: "num", text: String(s.rating) }), el("td", { class: "num", text: String(s.training) }),
      el("td", {}, [b])]));
  });
  $("p-out").textContent = lines(t.passport);
}

function spend(fn, i) {
  if (Module.ccall(fn, "number", ["number"], [i])) {
    traveler = call("ws_traveler");
    drawPassport();
  }
}

function setupPassport() {
  $("p-load").addEventListener("click", function () {
    var got = call("ws_load", ["string"], [$("p-text").value]);
    if (!got.ok) {
      $("p-error").textContent = "That Passport can't be read: " + got.error +
        (got.line ? " on line " + got.line : "") + ".";
      return;
    }
    $("p-error").textContent = "";
    traveler = got;
    drawPassport();
  });
  document.querySelectorAll(".copy").forEach(function (b) {
    b.addEventListener("click", function () {
      navigator.clipboard.writeText($(b.dataset.copy).textContent).then(function () {
        b.textContent = "Copied";
        setTimeout(function () { b.textContent = "Copy"; }, 1500);
      });
    });
  });
}

/* ------------------------------------------------------------------ sheet */

function itemName(id) { return REG.items[id] || "Item " + id; }

function drawSheet() {
  var t = traveler;
  var box = $("s-sheet");
  box.innerHTML = "";
  $("s-print").disabled = !t;
  if (!t) {
    box.appendChild(el("p", { class: "note", text: "No traveler yet." }));
    return;
  }
  box.appendChild(el("div", { class: "head" }, [
    el("span", { class: "big", text: t.name }),
    el("span", { text: REG.races[t.race].name + " " + REG.classes[t.class].name + " - Level " + t.level +
      " - XP " + t.xp + "/100 - Debt " + t.debt })]));
  var stats = el("table", {}, REG.stats.map(function (n, i) {
    return el("tr", {}, [el("td", { text: n }), el("td", { class: "num", text: String(t.stats[i]) })]);
  }));
  var derived = el("table", {}, [
    ["Health", t.health], ["Dodge", t.dodge], ["Speed (squares)", t.speed], ["Armor", t.armor],
    ["Melee bonus", t.melee_bonus], ["Unspent stat points", t.stat_points],
    ["Unspent skill points", t.skill_points]
  ].map(function (r) {
    return el("tr", {}, [el("td", { text: r[0] }), el("td", { class: "num", text: String(r[1]) })]);
  }));
  var skills = el("table", {}, t.skills.map(function (s, i) {
    return el("tr", {}, [
      el("td", { text: REG.skills[i].name + " (" + REG.stats[REG.skills[i].stat].slice(0, 3) + ")" + (s.tagged ? " *" : "") }),
      el("td", { class: "num", text: String(s.rating) })]);
  }));
  var gear = el("div", {}, [
    el("h3", { text: "Equipped" }),
    el("p", { text: t.equipped.filter(Boolean).map(itemName).join(", ") || "Nothing." }),
    el("h3", { text: "Pack" }),
    el("p", { text: t.pack.filter(Boolean).map(itemName).join(", ") || "Nothing." }),
    el("h3", { text: "Echoes" }),
    el("p", { text: t.echoes.map(function (e) {
      var d = REG.echoes[e[0]];
      return d ? d.name + ": " + (d.states[e[1] - 1] || "?") : "Echo " + e[0];
    }).join("; ") || "None yet." })]);
  box.appendChild(el("div", { class: "cols" }, [
    el("div", { class: "box" }, [el("h3", { text: "Stats" }), stats]),
    el("div", { class: "box" }, [el("h3", { text: "On the table" }), derived]),
    el("div", { class: "box" }, [el("h3", { text: "Skills (* tagged)" }), skills,
      el("p", { class: "note", text: "Roll d100 + rating against the target number." })]),
    el("div", { class: "box" }, [gear])]));
  box.appendChild(el("h3", { text: "Passport" }));
  box.appendChild(el("pre", { class: "password", text: lines(t.passport) }));
}

/* ------------------------------------------------------------------ stamp */

function setupStamp() {
  $("t-apply").addEventListener("click", function () {
    var out = $("t-result");
    out.innerHTML = "";
    if (!traveler) {
      $("t-error").textContent = "Read a Passport first.";
      return;
    }
    var r = call("ws_stamp", ["string", "number"], [$("t-text").value, $("t-rewind").checked ? 1 : 0]);
    if (!r.ok) {
      $("t-error").textContent = "That Travel Stamp can't be read: " + r.error +
        (r.line ? " on line " + r.line : "") + ".";
      return;
    }
    $("t-error").textContent = "";
    traveler = call("ws_traveler");
    var said = ["Departure " + r.departure + ", ticket " + r.ticket + ": " +
      (r.outcome ? "the trip failed." : "the trip is complete.")];
    if (r.xp) said.push(r.xp + " XP" + (r.levels ? ", and " + r.levels + " level" + (r.levels === 1 ? "" : "s") + " gained" : "") + ".");
    if (r.debt_added) said.push(r.debt_added + " Debt added.");
    if (r.debt_paid) said.push(r.debt_paid + " Debt paid off.");
    if (r.gained.length) said.push("Gained: " + r.gained.map(itemName).join(", ") + ".");
    if (r.stored.length) said.push("Your pack was full, so the lost-and-found is keeping: " + r.stored.map(itemName).join(", ") + ".");
    if (r.lost.length) said.push("Lost: " + r.lost.map(itemName).join(", ") + ".");
    if (r.shifted.length) said.push("The timeline shifted while you were away.");
    said.forEach(function (s) { out.appendChild(el("p", { text: s })); });
    out.appendChild(el("p", { text: "Your new Passport:" }));
    out.appendChild(el("pre", { class: "password", id: "t-out", text: lines(traveler.passport) }));
    $("p-text").value = lines(traveler.passport);
    drawPassport();
  });
}

/* ------------------------------------------------------------------ start */

function start() {
  fetch("registry.json").then(function (r) { return r.json(); }).then(function (reg) {
    REG = reg;
    RULES = call("ws_rules");
    $("loading").hidden = true;
    document.querySelectorAll(".tab").forEach(function (t) {
      t.addEventListener("click", function () { show(t.dataset.tab); });
    });
    setupCreator();
    setupPassport();
    setupStamp();
    show("create");
    document.body.dataset.ready = "1";
  });
}

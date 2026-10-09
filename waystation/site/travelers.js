// A player's travelers: their Passports, each with a note, kept for them (docs/waystation-web.md,
// "Your travelers"). The Waystation and the game in the browser both use it.
//
// Where they're kept: when this page runs inside the site's shell (site/index.html), the shell
// keeps them, signed in, on the player's own account (on claude.ai, the page's private store);
// otherwise in this browser (localStorage), so the pages work anywhere they're served.
//
//   Travelers.ready              a promise: resolves once it knows where they're kept
//   Travelers.where()            {account: true|false, who: "Name" or ""}
//   Travelers.list()             a promise of [{id, name, about, note, passport, stamp, updated}]
//   Travelers.save(t)            add or replace one (t.id, or a new one); resolves its id
//   Travelers.remove(id)
//   Travelers.onChange(fn)       fn(list) whenever the list changes, here or elsewhere
//
// A traveler: `passport` (its letters, no breaks), `name` and `about` (what the Waystation read
// from it, to show), `note` (the player's), `stamp` (a Travel Stamp waiting to be landed, or ""),
// `previous` (the Passports it had before, newest first, a few), `updated` (an ISO time).
"use strict";

var Travelers = (function () {
  var KEY = "apb-travelers";
  var listeners = [];
  var shell = null;                 // the window that keeps them, when there's a shell
  var account = { account: false, who: "" };
  var waiting = {};
  var nextId = 1;

  function local() {
    try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch (e) { return []; }
  }

  function keep(list) {
    try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (e) { /* private mode */ }
  }

  function newId() {
    return "t" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  }

  function changed(list) {
    listeners.forEach(function (fn) { fn(list); });
  }

  // The shell answers {apb: "travelers", re, ok, result}; and says when the list changes.
  function ask(op, arg) {
    return new Promise(function (resolve, reject) {
      var id = nextId++;
      waiting[id] = { resolve: resolve, reject: reject };
      shell.postMessage({ apb: "travelers", op: op, arg: arg, id: id }, "*");
    });
  }

  window.addEventListener("message", function (e) {
    var m = e.data;
    if (!m || typeof m !== "object" || e.source !== window.parent) return;
    if (m.apb === "travelers-reply" && waiting[m.id]) {
      var w = waiting[m.id];
      delete waiting[m.id];
      if (m.ok) w.resolve(m.result); else w.reject(new Error(m.error || "not saved"));
    } else if (m.apb === "travelers-changed") {
      if (m.where) account = m.where;
      changed(m.list || []);
    }
  });
  window.addEventListener("storage", function (e) {
    if (!shell && e.key === KEY) changed(local());
  });

  // Is there a shell? Ask the parent; no answer soon means there isn't one.
  var ready = new Promise(function (resolve) {
    if (window.parent === window) return resolve();
    var done = false;
    function hello(e) {
      var m = e.data;
      if (!m || m.apb !== "travelers-hello" || e.source !== window.parent) return;
      done = true;
      shell = window.parent;
      account = m.where || account;
      window.removeEventListener("message", hello);
      resolve();
    }
    window.addEventListener("message", hello);
    window.parent.postMessage({ apb: "travelers-hello" }, "*");
    setTimeout(function () { if (!done) { window.removeEventListener("message", hello); resolve(); } }, 1500);
  });

  function sorted(list) {
    return list.slice().sort(function (a, b) { return (b.updated || "").localeCompare(a.updated || ""); });
  }

  return {
    ready: ready,
    where: function () { return account; },
    list: function () {
      return ready.then(function () { return shell ? ask("list") : sorted(local()); });
    },
    save: function (t) {
      return ready.then(function () {
        var copy = JSON.parse(JSON.stringify(t));
        copy.id = copy.id || newId();
        copy.updated = new Date().toISOString();
        if (shell) return ask("save", copy).then(function () { return copy.id; });
        var list = local().filter(function (x) { return x.id !== copy.id; });
        list.push(copy);
        keep(list);
        changed(sorted(list));
        return copy.id;
      });
    },
    remove: function (id) {
      return ready.then(function () {
        if (shell) return ask("remove", id);
        var list = local().filter(function (x) { return x.id !== id; });
        keep(list);
        changed(sorted(list));
      });
    },
    onChange: function (fn) { listeners.push(fn); }
  };
})();

// A new Passport for a traveler: the old one goes to the front of `previous` (a few kept, in
// case a stamp was landed by mistake), unless it's the same.
function travelerWithPassport(t, passport) {
  var copy = JSON.parse(JSON.stringify(t || {}));
  if (copy.passport && copy.passport !== passport) {
    copy.previous = [copy.passport].concat(copy.previous || []).slice(0, 5);
  }
  copy.passport = passport;
  return copy;
}

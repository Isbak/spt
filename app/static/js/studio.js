/* Modelling Studio workbench (studio.html).
 *
 * A VS Code-style shell: an activity bar switches the side-bar view (Explorer /
 * Source Control / Search / Validation / Advisory); a tabbed CodeMirror editor sits
 * centre; a collapsible bottom panel hosts a *governed* tool console (Problems /
 * Query / Output / Analytics — never a raw shell); a status bar shows live state.
 *
 * Vanilla JS, no build step, matching main.js / chat-panel.js. Every feature is
 * guarded so a missing element never breaks the rest, and every fetch failure
 * degrades to a visible inline message. */
(function () {
  "use strict";

  var shell = document.getElementById("studio-shell");
  if (!shell) return; // empty state (no domains) — nothing to wire up.

  /* --- shared helpers ----------------------------------------------------- */
  var domainSel = document.getElementById("studio-domain");
  function domain() { return domainSel ? domainSel.value : ""; }
  function qs(obj) {
    return Object.keys(obj).map(function (k) {
      return encodeURIComponent(k) + "=" + encodeURIComponent(obj[k]);
    }).join("&");
  }
  function jget(url) {
    return fetch(url).then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); });
  }
  function jpost(url, body) {
    return fetch(url, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); });
  }
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }
  function store(key, value) { try { localStorage.setItem(key, value); } catch (e) {} }
  function restore(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }

  /* --- status bar (central updater other modules call) -------------------- */
  var statusbar = (function () {
    var branch = document.getElementById("status-branch");
    var changes = document.getElementById("status-changes");
    var problems = document.getElementById("status-problems");
    var cursor = document.getElementById("status-cursor");
    var fileEl = document.getElementById("status-file");
    var modelEl = document.getElementById("status-model");
    if (modelEl) {
      var prov = shell.getAttribute("data-provider") || "";
      var mod = shell.getAttribute("data-model") || "";
      modelEl.textContent = mod ? prov + " · " + mod : prov;
    }
    return {
      setBranch: function (name, count) {
        if (branch) branch.textContent = "⑂ " + (name || "—");
        if (changes) changes.textContent = (count || 0) + " change" + (count === 1 ? "" : "s");
      },
      setProblems: function (errors, warnings) {
        if (!problems) return;
        if (!errors && !warnings) { problems.textContent = "✓ no problems"; return; }
        problems.textContent = "✕ " + (errors || 0) + "  ⚠ " + (warnings || 0);
      },
      setCursor: function (line, col) { if (cursor) cursor.textContent = "Ln " + line + ", Col " + col; },
      setFile: function (path) { if (fileEl) fileEl.textContent = path || "No file open"; },
    };
  })();

  /* --- editor: tabbed CodeMirror with a graceful textarea fallback -------- */
  var editor = (function () {
    var ta = document.getElementById("editor");
    var tabsBar = document.getElementById("editor-tabs");
    var breadcrumb = document.getElementById("breadcrumb");
    var saveBtn = document.getElementById("save-btn");
    var graphBox = document.getElementById("studio-graph");
    if (!ta) return null;

    var cm = window.CodeMirror ? window.CodeMirror.fromTextArea(ta, {
      lineNumbers: true, mode: "text/turtle", viewportMargin: Infinity,
    }) : null;

    var GRAPH_TAB = "‹graph›"; // ‹graph› — a non-file editor surface
    var tabs = []; // [{ path, content, mode, dirty } | { path, graph: true }]
    var active = null;

    function isGraphPath(path) { return path === GRAPH_TAB; }
    function showSurface(graphActive) {
      if (graphBox) graphBox.hidden = !graphActive;
      var wrap = cm ? cm.getWrapperElement() : ta;
      if (wrap) wrap.style.display = graphActive ? "none" : "";
      if (!graphActive && cm) setTimeout(function () { cm.refresh(); }, 0);
    }

    function modeFor(path) {
      if (path.endsWith(".ttl")) return "text/turtle";
      if (path.endsWith(".rq")) return "application/sparql-query";
      if (path.endsWith(".sql")) return "text/x-sql";
      if (path.endsWith(".json")) return { name: "javascript", json: true };
      return "text/plain";
    }
    function render(content, mode) {
      if (cm) { cm.setOption("mode", mode); cm.setValue(content); }
      else { ta.value = content; }
    }
    function liveContent() { return cm ? cm.getValue() : ta.value; }
    function tabFor(path) { for (var i = 0; i < tabs.length; i++) if (tabs[i].path === path) return tabs[i]; return null; }
    function stashActive() { var t = tabFor(active); if (t && !t.graph) t.content = liveContent(); }

    function renderTabs() {
      tabsBar.innerHTML = "";
      tabs.forEach(function (t) {
        var tab = el("button", "wb-tab" + (t.path === active ? " is-active" : "") + (t.dirty ? " is-dirty" : ""));
        tab.setAttribute("role", "tab");
        tab.appendChild(el("span", "wb-tab__dot"));
        tab.appendChild(el("span", null, t.path.split("/").pop()));
        var close = el("span", "wb-tab__close", "×");
        tab.appendChild(close);
        tab.addEventListener("click", function (e) {
          if (e.target === close) { closeTab(t.path); return; }
          activate(t.path);
        });
        tabsBar.appendChild(tab);
      });
      if (explorer) explorer.syncTree(active);
    }
    function setMeta(path) {
      var graphActive = isGraphPath(path);
      if (breadcrumb) breadcrumb.textContent = graphActive ? "Knowledge graph" : (path || "No file open");
      if (saveBtn) saveBtn.disabled = graphActive || !path;
      statusbar.setFile(graphActive ? "Knowledge graph" : path);
    }
    function activate(path) {
      if (active === path) return;
      stashActive();
      active = path;
      var t = tabFor(path);
      if (t && t.graph) { showSurface(true); setMeta(path); renderTabs(); if (graphView) graphView.render(); return; }
      showSurface(false);
      render(t.content, t.mode);
      setMeta(path);
      renderTabs();
    }
    function openGraph() {
      if (tabFor(GRAPH_TAB)) { activate(GRAPH_TAB); return; }
      stashActive();
      tabs.push({ path: GRAPH_TAB, graph: true });
      active = GRAPH_TAB;
      showSurface(true);
      setMeta(GRAPH_TAB);
      renderTabs();
      if (graphView) graphView.render();
    }
    function open(path) {
      if (tabFor(path)) { activate(path); return; }
      jget("/api/studio/file?" + qs({ domain_id: domain(), path: path })).then(function (res) {
        if (res.data.error) { panel.log("Open failed: " + res.data.error); return; }
        stashActive();
        tabs.push({ path: path, content: res.data.content, mode: modeFor(path), dirty: false });
        active = path;
        showSurface(false);
        render(res.data.content, modeFor(path));
        setMeta(path);
        renderTabs();
      });
    }
    function closeTab(path) {
      var idx = -1;
      tabs = tabs.filter(function (t, i) { if (t.path === path) { idx = i; return false; } return true; });
      if (active === path) {
        if (tabs.length) { active = null; activate(tabs[Math.max(0, idx - 1)].path); }
        else { active = null; showSurface(false); render("", "text/plain"); setMeta(null); renderTabs(); }
      } else { renderTabs(); }
    }
    function markDirty() { var t = tabFor(active); if (t && !t.dirty) { t.dirty = true; renderTabs(); } }
    function save() {
      if (!active) return;
      var path = active;
      jpost("/api/studio/file", { domain_id: domain(), path: path, content: liveContent() }).then(function (res) {
        if (res.ok) {
          var t = tabFor(path); if (t) { t.dirty = false; t.content = liveContent(); renderTabs(); }
          panel.log("Saved " + path);
          if (sourceControl) sourceControl.refresh();
        } else { panel.log("Save failed: " + (res.data.error || "")); }
      });
    }
    function reset() { tabs = []; active = null; showSurface(false); render("", "text/plain"); setMeta(null); renderTabs(); }

    if (cm) {
      cm.on("change", markDirty);
      cm.on("cursorActivity", function () {
        var c = cm.getCursor();
        statusbar.setCursor(c.line + 1, c.ch + 1);
      });
    } else {
      ta.addEventListener("input", markDirty);
    }
    if (saveBtn) saveBtn.addEventListener("click", save);
    document.addEventListener("keydown", function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); }
    });

    return { open: open, openGraph: openGraph, reset: reset, refresh: renderTabs };
  })();

  /* --- explorer: file tree (with git badges) + quick scaffold ------------- */
  var explorer = (function () {
    var tree = document.getElementById("file-tree");
    if (!tree) return null;
    var badges = {}; // path -> git code

    function iconFor(path) {
      if (path.endsWith(".ttl")) return "🐢";
      if (path.endsWith(".rq")) return "❖";
      if (path.endsWith(".sql")) return "🗄";
      if (path.endsWith(".json")) return "{}";
      return "📄";
    }
    function load() {
      jget("/api/studio/tree?" + qs({ domain_id: domain() })).then(function (res) {
        tree.innerHTML = "";
        var files = (res.data && res.data.files) || [];
        if (!files.length) {
          tree.appendChild(el("li", "wb-tree__empty", "No files yet — scaffold or chat to begin."));
          return;
        }
        files.forEach(function (path) {
          var li = el("li", "wb-tree__item");
          var a = el("a", "wb-tree__link");
          a.href = "#"; a.setAttribute("data-path", path);
          a.appendChild(el("span", "wb-tree__icon", iconFor(path)));
          a.appendChild(el("span", "wb-tree__name", path));
          var badge = el("span", "wb-tree__badge");
          a.appendChild(badge);
          a.addEventListener("click", function (e) { e.preventDefault(); if (editor) editor.open(path); });
          li.appendChild(a);
          tree.appendChild(li);
        });
        applyBadges();
      });
    }
    function applyBadges() {
      tree.querySelectorAll(".wb-tree__link").forEach(function (a) {
        var code = badges[a.getAttribute("data-path")];
        var badge = a.querySelector(".wb-tree__badge");
        badge.textContent = code || "";
        badge.className = "wb-tree__badge" + (code ? " wb-git--" + code : "");
      });
    }
    function setBadges(map) { badges = map || {}; applyBadges(); }
    function syncTree(activePath) {
      tree.querySelectorAll(".wb-tree__link").forEach(function (a) {
        a.classList.toggle("is-open", a.getAttribute("data-path") === activePath);
      });
    }

    var scaffoldBtn = document.getElementById("scaffold-btn");
    if (scaffoldBtn) {
      scaffoldBtn.addEventListener("click", function () {
        var raw = (document.getElementById("sc-classes").value || "").split(",");
        var classes = raw.map(function (s) { return s.trim(); }).filter(Boolean);
        jpost("/api/studio/chat", {
          domain_id: domain(),
          answers: {
            domain_label: document.getElementById("sc-label").value,
            prefix: document.getElementById("sc-prefix").value,
            base_namespace: document.getElementById("sc-ns").value,
            classes: classes, properties: [],
          },
        }).then(function (res) {
          panel.log("Scaffold: " + (res.data.reply || "done"));
          load();
          if (sourceControl) sourceControl.refresh();
        });
      });
    }

    return { load: load, setBadges: setBadges, syncTree: syncTree };
  })();

  /* --- side bar: activity-bar view switching ------------------------------ */
  (function () {
    var acts = shell.querySelectorAll(".wb-act[data-view]");
    var views = shell.querySelectorAll(".wb-view[data-view]");
    function show(name) {
      acts.forEach(function (a) {
        var on = a.getAttribute("data-view") === name;
        a.classList.toggle("is-active", on);
        a.setAttribute("aria-pressed", on ? "true" : "false");
      });
      views.forEach(function (v) { v.hidden = v.getAttribute("data-view") !== name; });
      store("studio.sidebarView", name);
      if (name === "scm" && sourceControl) sourceControl.refresh();
    }
    acts.forEach(function (a) {
      a.addEventListener("click", function () { show(a.getAttribute("data-view")); });
    });
    show(restore("studio.sidebarView") || "explorer");
  })();

  /* --- splitters: drag to resize side bar width and panel height ---------- */
  (function () {
    function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
    function dragger(handle, apply, persistKey) {
      if (!handle) return;
      function start(startEvt) {
        startEvt.preventDefault();
        function move(e) { apply(e); }
        function up() {
          document.removeEventListener("pointermove", move);
          document.removeEventListener("pointerup", up);
          store(persistKey, getComputedStyle(shell).getPropertyValue(persistKey === "studio.sidebarW" ? "--sidebar-w" : "--panel-h"));
        }
        document.addEventListener("pointermove", move);
        document.addEventListener("pointerup", up);
      }
      handle.addEventListener("pointerdown", start);
    }
    var sidebarHandle = document.getElementById("resizer-sidebar");
    dragger(sidebarHandle, function (e) {
      var w = clamp(e.clientX - shell.getBoundingClientRect().left - 48, 160, 480);
      shell.style.setProperty("--sidebar-w", w + "px");
    }, "studio.sidebarW");
    var panelHandle = document.getElementById("resizer-panel");
    dragger(panelHandle, function (e) {
      var h = clamp(shell.getBoundingClientRect().bottom - e.clientY - 24, 80, 520);
      shell.style.setProperty("--panel-h", h + "px");
    }, "studio.panelH");

    // Keyboard nudges for accessibility.
    function nudge(handle, prop, sign, lo, hi) {
      if (!handle) return;
      handle.addEventListener("keydown", function (e) {
        var keys = prop === "--sidebar-w" ? ["ArrowLeft", "ArrowRight"] : ["ArrowUp", "ArrowDown"];
        if (keys.indexOf(e.key) === -1) return;
        e.preventDefault();
        var cur = parseInt(getComputedStyle(shell).getPropertyValue(prop), 10) || lo;
        var delta = (e.key === keys[0] ? -16 : 16) * sign;
        shell.style.setProperty(prop, clamp(cur + delta, lo, hi) + "px");
      });
    }
    nudge(sidebarHandle, "--sidebar-w", 1, 160, 480);
    nudge(panelHandle, "--panel-h", -1, 80, 520);

    var w = restore("studio.sidebarW"); if (w) shell.style.setProperty("--sidebar-w", w.trim());
    var h = restore("studio.panelH"); if (h) shell.style.setProperty("--panel-h", h.trim());
  })();

  /* --- bottom panel: tabs, collapse, maximize ----------------------------- */
  var panel = (function () {
    var panelEl = document.getElementById("wb-panel");
    var tabs = shell.querySelectorAll(".wb-panel__tab");
    var panes = shell.querySelectorAll(".wb-pane");
    var log = document.getElementById("output-log");

    function showPane(name) {
      tabs.forEach(function (t) { t.classList.toggle("is-active", t.getAttribute("data-pane") === name); });
      panes.forEach(function (p) { p.hidden = p.getAttribute("data-pane") !== name; });
      store("studio.panelTab", name);
    }
    function setCollapsed(on) {
      shell.classList.toggle("is-panel-collapsed", on);
      store("studio.panelCollapsed", on ? "1" : "0");
    }
    function toggle() { setCollapsed(!shell.classList.contains("is-panel-collapsed")); }

    tabs.forEach(function (t) {
      t.addEventListener("click", function () {
        if (shell.classList.contains("is-panel-collapsed")) setCollapsed(false);
        showPane(t.getAttribute("data-pane"));
      });
    });
    var collapseBtn = document.getElementById("panel-collapse");
    if (collapseBtn) collapseBtn.addEventListener("click", toggle);
    var maxBtn = document.getElementById("panel-maximize");
    if (maxBtn) maxBtn.addEventListener("click", function () { shell.classList.toggle("is-panel-max"); });

    document.addEventListener("keydown", function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key === "`") { e.preventDefault(); toggle(); }
    });

    showPane(restore("studio.panelTab") || "problems");
    setCollapsed(restore("studio.panelCollapsed") === "1");

    return {
      showPane: showPane,
      reveal: function (name) { setCollapsed(false); showPane(name); },
      log: function (text) {
        if (!log) return;
        var stamp = new Date().toLocaleTimeString();
        log.textContent += "[" + stamp + "] " + text + "\n";
        log.scrollTop = log.scrollHeight;
      },
    };
  })();

  /* --- source control: status badges, inline diff, commit & PR ------------ */
  var sourceControl = (function () {
    var list = document.getElementById("scm-changes");
    var diffEl = document.getElementById("scm-diff");
    var branchEl = document.getElementById("scm-branch");
    var badge = document.getElementById("scm-badge");
    if (!list) return null;

    function refresh() {
      jget("/api/studio/status?" + qs({ domain_id: domain() })).then(function (res) {
        var data = res.data || {};
        var files = data.files || [];
        if (branchEl) branchEl.textContent = data.branch || "";
        statusbar.setBranch(data.branch, files.length);
        if (badge) { badge.hidden = !files.length; badge.textContent = files.length; }
        var map = {};
        files.forEach(function (f) { map[f.path] = f.code; });
        if (explorer) explorer.setBadges(map);
        list.innerHTML = "";
        if (!files.length) { list.appendChild(el("li", "wb-changes__empty", "No changes")); return; }
        files.forEach(function (f) {
          var li = el("li", "wb-change");
          li.appendChild(el("span", "wb-change__badge wb-git--" + f.code, f.code));
          li.appendChild(el("span", "wb-change__path", f.path));
          li.addEventListener("click", function () { showDiff(f.path); });
          list.appendChild(li);
        });
      });
    }
    function showDiff(path) {
      jget("/api/studio/diff?" + qs({ domain_id: domain(), path: path })).then(function (res) {
        if (!diffEl) return;
        diffEl.hidden = false;
        diffEl.innerHTML = "";
        var text = (res.data && res.data.diff) || "(no diff)";
        text.split("\n").forEach(function (line) {
          var cls = "wb-diff__line";
          if (line[0] === "+" && line.indexOf("+++") !== 0) cls += " wb-diff__add";
          else if (line[0] === "-" && line.indexOf("---") !== 0) cls += " wb-diff__del";
          else if (line.indexOf("@@") === 0) cls += " wb-diff__hunk";
          diffEl.appendChild(el("div", cls, line || " "));
        });
      });
    }
    var prBtn = document.getElementById("scm-pr-btn");
    if (prBtn) {
      prBtn.addEventListener("click", function () {
        var out = document.getElementById("scm-pr-result");
        var msg = (document.getElementById("scm-message") || {}).value || "";
        if (out) out.textContent = "Working…";
        jpost("/api/studio/pr", { domain_id: domain(), title: msg || null, body: msg || null }).then(function (res) {
          var d = res.data || {};
          if (!out) return;
          if (d.pull_request_url) out.innerHTML = 'PR: <a href="' + d.pull_request_url + '">' + d.pull_request_url + "</a>";
          else if (d.compare_url) out.innerHTML = '<a href="' + d.compare_url + '">' + (d.message || "Open PR") + "</a>";
          else out.textContent = d.message || "Done.";
          refresh();
        });
      });
    }
    return { refresh: refresh };
  })();

  /* --- problems: workspace validation ------------------------------------- */
  var problems = (function () {
    var sideList = document.getElementById("problems-side");
    var panelList = document.getElementById("problems-list");
    var count = document.getElementById("problems-count");
    var valBadge = document.getElementById("val-badge");
    var btn = document.getElementById("validate-btn");

    function row(p) {
      var li = el("li", "wb-problem wb-problem--" + p.severity);
      li.appendChild(el("span", "wb-problem__icon", p.severity === "error" ? "✕" : p.severity === "warning" ? "⚠" : "ℹ"));
      var body = el("span", "wb-problem__body");
      body.appendChild(el("span", "wb-problem__msg", p.message));
      if (p.file) body.appendChild(el("span", "wb-problem__file", p.file));
      li.appendChild(body);
      if (p.file && p.kind === "syntax") {
        li.classList.add("is-clickable");
        li.addEventListener("click", function () { if (editor) editor.open(p.file); });
      }
      return li;
    }
    function run() {
      panel.log("Validating workspace…");
      jpost("/api/studio/validate", { domain_id: domain() }).then(function (res) {
        var d = res.data || {};
        var items = d.problems || [];
        [sideList, panelList].forEach(function (target) {
          if (!target) return;
          target.innerHTML = "";
          if (!items.length) { target.appendChild(el("li", "wb-problems__empty", "No problems found.")); return; }
          items.forEach(function (p) { target.appendChild(row(p)); });
        });
        statusbar.setProblems(d.errors, d.warnings);
        if (count) { count.hidden = !items.length; count.textContent = items.length; }
        if (valBadge) { valBadge.hidden = !d.errors; valBadge.textContent = d.errors || 0; }
        panel.log("Validation: " + (d.errors || 0) + " error(s), " + (d.warnings || 0) + " warning(s).");
      });
    }
    if (btn) btn.addEventListener("click", function () { run(); panel.reveal("problems"); });
    return { run: run };
  })();

  /* --- query: SPARQL runner over the workspace ---------------------------- */
  (function () {
    var input = document.getElementById("query-input");
    var runBtn = document.getElementById("query-run");
    var results = document.getElementById("query-results");
    var status = document.getElementById("query-status");
    if (!runBtn) return;
    runBtn.addEventListener("click", function () {
      var text = (input.value || "").trim();
      if (!text) return;
      if (status) status.textContent = "Running…";
      results.innerHTML = "";
      jpost("/api/studio/query", { domain_id: domain(), query: text }).then(function (res) {
        var d = res.data || {};
        if (d.error) { if (status) status.textContent = "Error: " + d.error; return; }
        var cols = d.columns || [];
        var rows = d.rows || [];
        if (status) status.textContent = rows.length + " row(s)";
        if (!rows.length) { results.appendChild(el("p", "muted", "No results.")); return; }
        var table = el("table", "wb-table");
        var thead = el("thead"); var htr = el("tr");
        cols.forEach(function (c) { htr.appendChild(el("th", null, c)); });
        thead.appendChild(htr); table.appendChild(thead);
        var tbody = el("tbody");
        rows.forEach(function (r) {
          var tr = el("tr");
          cols.forEach(function (c) { tr.appendChild(el("td", null, r[c] != null ? r[c] : "")); });
          tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        results.appendChild(table);
      });
    });
  })();

  /* --- analytics: workspace graph metrics --------------------------------- */
  var analytics = (function () {
    var cards = document.getElementById("analytics-cards");
    var LABELS = {
      triples: "Triples", node_count: "Nodes", edge_count: "Edges", class_count: "Classes",
      property_count: "Properties", hierarchy_depth: "Hierarchy depth", graph_density: "Density",
      subjects: "Subjects", predicates: "Predicates", objects: "Objects",
    };
    function run() {
      if (!cards) return;
      jpost("/api/studio/analytics", { domain_id: domain() }).then(function (res) {
        var d = res.data || {};
        cards.innerHTML = "";
        Object.keys(LABELS).forEach(function (key) {
          if (d[key] == null) return;
          var card = el("div", "wb-metric");
          var val = typeof d[key] === "number" && d[key] % 1 !== 0 ? d[key].toFixed(3) : d[key];
          card.appendChild(el("div", "wb-metric__value", String(val)));
          card.appendChild(el("div", "wb-metric__label", LABELS[key]));
          cards.appendChild(card);
        });
        panel.log("Analytics computed for " + domain() + ".");
      });
    }
    return { run: run };
  })();

  /* --- output: governed tool console (NOT a raw shell) -------------------- */
  (function () {
    var runBtn = document.getElementById("output-run");
    var clearBtn = document.getElementById("output-clear");
    var sel = document.getElementById("output-command");
    var logEl = document.getElementById("output-log");
    if (runBtn) {
      runBtn.addEventListener("click", function () {
        var cmd = sel ? sel.value : "validate";
        if (cmd === "validate") { problems.run(); }
        else if (cmd === "analytics") { analytics.run(); panel.reveal("analytics"); }
        else if (cmd === "status" && sourceControl) {
          sourceControl.refresh();
          panel.log("Refreshed git status.");
        }
      });
    }
    if (clearBtn && logEl) clearBtn.addEventListener("click", function () { logEl.textContent = ""; });
  })();

  /* --- search: semantic search over the workspace ------------------------- */
  (function () {
    var form = document.getElementById("search-form");
    var input = document.getElementById("search-input");
    var out = document.getElementById("search-results");
    if (!form) return;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var q = (input.value || "").trim();
      if (!q) return;
      out.innerHTML = "";
      jpost("/api/studio/search", { domain_id: domain(), query: q }).then(function (res) {
        var items = (res.data && res.data.results) || [];
        if (!items.length) { out.appendChild(el("li", "muted", "No matches.")); return; }
        items.forEach(function (r) {
          var li = el("li", "wb-result");
          li.appendChild(el("span", "wb-result__label", r.label || r.uri));
          li.appendChild(el("span", "wb-result__meta", r.match_type + " · " + (r.predicate || "")));
          out.appendChild(li);
        });
      });
    });
  })();

  /* --- advisory: governed decision support -------------------------------- */
  (function () {
    var btn = document.getElementById("advisory-btn");
    var out = document.getElementById("advisory-results");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var objective = (document.getElementById("adv-objective").value || "").trim();
      var type = (document.getElementById("adv-type").value || "").trim();
      out.innerHTML = "Working…";
      jpost("/api/advisory", { objective: objective, candidate_type: type, criteria: [] }).then(function (res) {
        var d = res.data || {};
        out.innerHTML = "";
        if (d.error) { out.appendChild(el("p", "error", d.error)); return; }
        if (d.recommendation) out.appendChild(el("p", "wb-advisory__rec", d.recommendation));
        if (d.explanation) out.appendChild(el("p", "muted", d.explanation));
        (d.ranked || []).forEach(function (item) {
          var li = el("div", "wb-result");
          li.appendChild(el("span", "wb-result__label", item.label || item.uri));
          li.appendChild(el("span", "wb-result__meta", "score " + (item.score != null ? item.score.toFixed(3) : "—")));
          out.appendChild(li);
        });
      });
    });
  })();

  /* --- graph view: interactive knowledge graph in the main editor area ---- */
  var graphView = (function () {
    var box = document.getElementById("studio-graph");
    if (!box || !window.GraphExplorer) return null;
    var canvas = box.querySelector("[data-graph-canvas]");
    var stats = box.querySelector("[data-graph-stats]");
    var instance = null;
    var loaded = null; // domain the current render reflects

    function load() {
      if (instance) { instance.destroy(); instance = null; }
      jpost("/api/studio/graph", { domain_id: domain() }).then(function (res) {
        var d = res.data || {};
        canvas.dataset.nodes = JSON.stringify(d.nodes || []);
        canvas.dataset.edges = JSON.stringify(d.edges || []);
        if (stats) stats.textContent = (d.node_count || 0) + " nodes · " + (d.edge_count || 0) + " links";
        instance = window.GraphExplorer.init(box, {
          fetchDetail: function (uri) {
            return jpost("/api/studio/graph/node", { domain_id: domain(), uri: uri }).then(function (r) { return r.data; });
          },
        });
        loaded = domain();
      });
    }
    function render() { if (!instance || loaded !== domain()) load(); }
    function invalidate() { if (instance) { instance.destroy(); instance = null; } loaded = null; }
    return { render: render, invalidate: invalidate };
  })();

  var graphAct = document.getElementById("act-graph");
  if (graphAct && editor) {
    graphAct.addEventListener("click", function () { editor.openGraph(); });
  }

  /* --- boot + domain switching -------------------------------------------- */
  function loadAll() {
    if (explorer) explorer.load();
    if (sourceControl) sourceControl.refresh();
  }
  if (domainSel) {
    domainSel.addEventListener("change", function () {
      if (graphView) graphView.invalidate();
      if (editor) editor.reset();
      loadAll();
    });
  }
  loadAll();
})();

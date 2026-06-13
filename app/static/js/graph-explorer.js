/* Knowledge-graph exploration renderer (vis-network).
 *
 * One reusable module drives both the System Graph Explorer page and the Studio's
 * in-editor graph view. The caller supplies the data (via data-* attributes on the
 * canvas element) and an async `fetchDetail(uri)` that returns the node-detail payload
 * for the right-hand inspector sidebar — decoupling transport (GET vs POST) from the UI.
 *
 * Expected DOM inside `root` (all located by data-attribute, so layout is flexible):
 *   [data-graph-canvas]   data-nodes='[...]' data-edges='[...]'  → vis-network mount
 *   [data-graph-detail]                                          → inspector sidebar
 *   [data-graph-legend]                                          → type legend / filter
 *   [data-graph-minimap]                                         → optional minimap <canvas>
 *   [data-graph-search]                                          → optional live-highlight input
 *   [data-graph-stats]                                           → optional "n nodes · m links"
 *   buttons: [data-graph-fit] [data-graph-physics] [data-graph-reset] [data-graph-export]
 *   select: [data-graph-layout]
 */
(function () {
  "use strict";

  // Curated, color-blind-friendly palette. Nodes render as solid dots, so labels use
  // the theme text colour and stay legible on both light and dark canvases.
  var PALETTE = [
    "#2563eb", "#16a34a", "#d97706", "#dc2626", "#7c3aed",
    "#0891b2", "#db2777", "#65a30d", "#ea580c", "#4f46e5",
    "#0d9488", "#9333ea",
  ];

  function token(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v && v.trim()) || fallback;
  }

  function colorFor(group) {
    var hash = 0;
    var key = group || "Resource";
    for (var i = 0; i < key.length; i++) {
      hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
    }
    return PALETTE[hash % PALETTE.length];
  }

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }

  function initGraphExplorer(root, options) {
    options = options || {};
    if (!root || typeof vis === "undefined") return null;
    var canvas = root.querySelector("[data-graph-canvas]");
    if (!canvas) return null;

    var rawNodes, rawEdges;
    try {
      rawNodes = JSON.parse(canvas.dataset.nodes || "[]");
      rawEdges = JSON.parse(canvas.dataset.edges || "[]");
    } catch (e) {
      rawNodes = [];
      rawEdges = [];
    }

    var detailEl = root.querySelector("[data-graph-detail]");
    var legendEl = root.querySelector("[data-graph-legend]");
    var statsEl = root.querySelector("[data-graph-stats]");
    var searchEl = root.querySelector("[data-graph-search]");
    var minimapEl = root.querySelector("[data-graph-minimap]");

    function styleNode(n) {
      var base = colorFor(n.group);
      return Object.assign({}, n, {
        shape: "dot",
        size: 10 + Math.min(n.degree || 0, 12) * 1.6,
        color: { background: base, border: base, highlight: { background: base, border: token("--text", "#12151a") } },
        font: { color: token("--text", "#12151a"), size: 12, face: "system-ui, sans-serif", strokeWidth: 0 },
        borderWidth: 1.5,
      });
    }

    var nodes = new vis.DataSet(rawNodes.map(styleNode));
    var edges = new vis.DataSet(rawEdges.map(function (e) {
      return Object.assign({}, e, {
        color: { color: token("--border-strong", "#cbd0d8"), highlight: token("--accent", "#2563eb"), opacity: 0.9 },
        font: { color: token("--text-muted", "#4d5560"), size: 10, strokeWidth: 4, strokeColor: token("--graph-canvas-bg", "#ffffff") },
      });
    }));

    var byId = {};
    rawNodes.forEach(function (n) { byId[n.id] = n; });
    var edgeById = {};
    rawEdges.forEach(function (e) { edgeById[e.id] = e; });

    function visOptions() {
      return {
        nodes: { scaling: { min: 8, max: 40 } },
        edges: { arrows: "to", smooth: { type: "dynamic" }, width: 1 },
        interaction: { hover: true, navigationButtons: true, zoomView: true, dragView: true, tooltipDelay: 150, keyboard: { enabled: true, bindToWindow: false } },
        physics: { stabilization: { iterations: 150 }, barnesHut: { springLength: 130, gravitationalConstant: -3500 } },
        layout: { improvedLayout: true },
      };
    }

    var network = new vis.Network(canvas, { nodes: nodes, edges: edges }, visOptions());

    if (statsEl) statsEl.textContent = rawNodes.length + " nodes · " + rawEdges.length + " links";

    /* ----- Right-hand inspector ------------------------------------------ */
    function emptyDetail() {
      if (!detailEl) return;
      detailEl.innerHTML = "";
      var empty = el("div", "graph-detail__empty");
      empty.appendChild(el("p", null, "Select a node or relationship"));
      empty.appendChild(el("small", null, "Click any node to inspect its type, properties and connections."));
      detailEl.appendChild(empty);
    }

    function section(title) {
      var s = el("div", "graph-detail__section");
      s.appendChild(el("h4", "graph-detail__heading", title));
      return s;
    }

    function neighborLink(uri, label, predicate) {
      var item = el("button", "graph-detail__link");
      item.type = "button";
      item.appendChild(el("span", "graph-detail__pred", predicate));
      item.appendChild(el("span", "graph-detail__target", label));
      item.addEventListener("click", function () { selectNode(uri); });
      return item;
    }

    function renderNodeDetail(detail) {
      if (!detailEl) return;
      detailEl.innerHTML = "";
      var head = el("div", "graph-detail__head");
      head.appendChild(el("h3", "graph-detail__title", detail.label || detail.id));
      (detail.type_labels && detail.type_labels.length ? detail.type_labels : ["Resource"]).forEach(function (t, i) {
        var badge = el("span", "graph-detail__type");
        badge.style.setProperty("--type-color", colorFor((detail.types && detail.types[i] || t).split(/[#/]/).pop()));
        badge.textContent = t;
        head.appendChild(badge);
      });
      detailEl.appendChild(head);

      var uriRow = el("div", "graph-detail__uri");
      uriRow.appendChild(el("code", null, detail.id));
      var copy = el("button", "graph-detail__copy", "Copy");
      copy.type = "button";
      copy.addEventListener("click", function () {
        navigator.clipboard && navigator.clipboard.writeText(detail.id);
        copy.textContent = "Copied";
        setTimeout(function () { copy.textContent = "Copy"; }, 1200);
      });
      uriRow.appendChild(copy);
      detailEl.appendChild(uriRow);

      var actions = el("div", "graph-detail__actions");
      var expand = el("button", "btn btn--sm", "Expand neighbors");
      expand.type = "button";
      expand.addEventListener("click", function () { expandNeighbors(detail); });
      actions.appendChild(expand);
      if (options.focusUrl) {
        var focus = el("a", "btn btn--sm btn--secondary", "Focus");
        focus.href = options.focusUrl(detail.id);
        actions.appendChild(focus);
      }
      detailEl.appendChild(actions);

      if (detail.comment) {
        var c = section("Description");
        c.appendChild(el("p", "graph-detail__comment", detail.comment));
        detailEl.appendChild(c);
      }
      if (detail.provenance && detail.provenance !== "Not recorded") {
        var prov = section("Provenance");
        prov.appendChild(el("code", "graph-detail__mono", detail.provenance));
        detailEl.appendChild(prov);
      }
      if (detail.properties && detail.properties.length) {
        var props = section("Properties");
        var dl = el("dl", "graph-detail__props");
        detail.properties.forEach(function (p) {
          dl.appendChild(el("dt", null, p.predicate_label));
          dl.appendChild(el("dd", null, p.value));
        });
        props.appendChild(dl);
        detailEl.appendChild(props);
      }
      if (detail.outgoing && detail.outgoing.length) {
        var out = section("Outgoing (" + detail.outgoing_count + ")");
        detail.outgoing.forEach(function (r) { out.appendChild(neighborLink(r.target, r.target_label, r.predicate_label)); });
        detailEl.appendChild(out);
      }
      if (detail.incoming && detail.incoming.length) {
        var inc = section("Incoming (" + detail.incoming_count + ")");
        detail.incoming.forEach(function (r) { inc.appendChild(neighborLink(r.source, r.source_label, r.predicate_label)); });
        detailEl.appendChild(inc);
      }
    }

    function renderEdgeDetail(edge) {
      if (!detailEl) return;
      detailEl.innerHTML = "";
      detailEl.appendChild(el("h3", "graph-detail__title", edge.label || "Relationship"));
      var dl = el("dl", "graph-detail__props");
      dl.appendChild(el("dt", null, "Predicate"));
      dl.appendChild(el("dd", null, edge.predicate));
      dl.appendChild(el("dt", null, "From"));
      dl.appendChild(el("dd", null, (byId[edge.from] || {}).label || edge.from));
      dl.appendChild(el("dt", null, "To"));
      dl.appendChild(el("dd", null, (byId[edge.to] || {}).label || edge.to));
      detailEl.appendChild(dl);
    }

    function selectNode(uri) {
      if (nodes.get(uri)) {
        network.selectNodes([uri]);
        network.focus(uri, { scale: 1.0, animation: true });
      }
      if (!options.fetchDetail) { if (byId[uri]) renderNodeDetail(byId[uri]); return; }
      if (detailEl) detailEl.innerHTML = "<p class='graph-detail__loading'>Loading…</p>";
      Promise.resolve(options.fetchDetail(uri)).then(renderNodeDetail).catch(function () {
        if (byId[uri]) renderNodeDetail(byId[uri]);
      });
    }

    function expandNeighbors(detail) {
      var rels = (detail.outgoing || []).map(function (r) { return { uri: r.target, label: r.target_label, dir: "out", pred: r }; })
        .concat((detail.incoming || []).map(function (r) { return { uri: r.source, label: r.source_label, dir: "in", pred: r }; }));
      rels.forEach(function (rel) {
        if (!nodes.get(rel.uri)) {
          nodes.add(styleNode({ id: rel.uri, label: rel.label, type: "Resource", group: "Resource", degree: 1 }));
          byId[rel.uri] = { id: rel.uri, label: rel.label, group: "Resource" };
        }
        var from = rel.dir === "out" ? detail.id : rel.uri;
        var to = rel.dir === "out" ? rel.uri : detail.id;
        var eid = "x:" + from + "|" + rel.pred.predicate + "|" + to;
        if (!edges.get(eid)) {
          edges.add({ id: eid, from: from, to: to, label: rel.pred.predicate_label,
            color: { color: token("--accent", "#2563eb") },
            font: { color: token("--text-muted", "#4d5560"), size: 10, strokeWidth: 4, strokeColor: token("--graph-canvas-bg", "#ffffff") } });
        }
      });
      buildLegend();
    }

    network.on("click", function (params) {
      if (params.nodes.length) { selectNode(params.nodes[0]); }
      else if (params.edges.length) {
        var e = edgeById[params.edges[0]] || edges.get(params.edges[0]);
        if (e) renderEdgeDetail(e);
      } else { emptyDetail(); }
    });
    network.on("doubleClick", function (params) {
      if (params.nodes.length && options.fetchDetail) {
        Promise.resolve(options.fetchDetail(params.nodes[0])).then(expandNeighbors).catch(function () {});
      }
    });

    /* ----- Legend + type filter ------------------------------------------ */
    var hidden = {};
    function buildLegend() {
      if (!legendEl) return;
      var groups = {};
      nodes.get().forEach(function (n) { groups[n.group] = (groups[n.group] || 0) + 1; });
      legendEl.innerHTML = "";
      Object.keys(groups).sort().forEach(function (g) {
        var chip = el("button", "graph-legend__chip" + (hidden[g] ? " is-off" : ""));
        chip.type = "button";
        chip.setAttribute("aria-pressed", hidden[g] ? "false" : "true");
        var sw = el("span", "graph-legend__swatch");
        sw.style.background = colorFor(g);
        chip.appendChild(sw);
        chip.appendChild(el("span", "graph-legend__label", g));
        chip.appendChild(el("span", "graph-legend__count", String(groups[g])));
        chip.addEventListener("click", function () { toggleType(g); });
        legendEl.appendChild(chip);
      });
    }
    function toggleType(group) {
      hidden[group] = !hidden[group];
      nodes.forEach(function (n) {
        if (n.group === group) nodes.update({ id: n.id, hidden: !!hidden[group] });
      });
      buildLegend();
    }

    /* ----- Search-to-highlight ------------------------------------------- */
    function applySearch(term) {
      term = (term || "").trim().toLowerCase();
      nodes.forEach(function (n) {
        var match = !term || (n.label || "").toLowerCase().indexOf(term) !== -1 || (n.id || "").toLowerCase().indexOf(term) !== -1;
        nodes.update({ id: n.id, opacity: match ? 1 : 0.15 });
      });
    }
    if (searchEl) searchEl.addEventListener("input", function () { applySearch(searchEl.value); });

    /* ----- Toolbar -------------------------------------------------------- */
    var physicsOn = true;
    function bind(sel, ev, fn) { var n = root.querySelector(sel); if (n) n.addEventListener(ev, fn); }
    bind("[data-graph-fit]", "click", function () { network.fit({ animation: true }); });
    bind("[data-graph-physics]", "click", function (e) {
      physicsOn = !physicsOn;
      network.setOptions({ physics: { enabled: physicsOn } });
      e.currentTarget.setAttribute("aria-pressed", physicsOn ? "true" : "false");
    });
    bind("[data-graph-reset]", "click", function () {
      hidden = {};
      nodes.forEach(function (n) { nodes.update({ id: n.id, hidden: false, opacity: 1 }); });
      if (searchEl) searchEl.value = "";
      buildLegend();
      network.fit({ animation: true });
    });
    bind("[data-graph-export]", "click", function () {
      var cnv = canvas.querySelector("canvas");
      if (!cnv) return;
      var link = document.createElement("a");
      link.href = cnv.toDataURL("image/png");
      link.download = "knowledge-graph.png";
      link.click();
    });
    bind("[data-graph-layout]", "change", function (e) {
      var hierarchical = e.target.value === "hierarchical";
      network.setOptions({ layout: { hierarchical: hierarchical ? { direction: "UD", sortMethod: "directed" } : false } });
    });

    /* ----- Minimap -------------------------------------------------------- */
    function drawMinimap() {
      if (!minimapEl || !minimapEl.getContext) return;
      var ctx = minimapEl.getContext("2d");
      var w = minimapEl.width, h = minimapEl.height;
      ctx.clearRect(0, 0, w, h);
      var ids = nodes.getIds();
      if (!ids.length) return;
      var pos = network.getPositions(ids);
      var xs = [], ys = [];
      ids.forEach(function (id) { if (pos[id]) { xs.push(pos[id].x); ys.push(pos[id].y); } });
      if (!xs.length) return;
      var minX = Math.min.apply(null, xs), maxX = Math.max.apply(null, xs);
      var minY = Math.min.apply(null, ys), maxY = Math.max.apply(null, ys);
      var pad = 6;
      var sx = (w - pad * 2) / Math.max(maxX - minX, 1);
      var sy = (h - pad * 2) / Math.max(maxY - minY, 1);
      var s = Math.min(sx, sy);
      function mx(x) { return pad + (x - minX) * s; }
      function my(y) { return pad + (y - minY) * s; }
      ids.forEach(function (id) {
        if (!pos[id]) return;
        var n = byId[id] || {};
        ctx.fillStyle = colorFor(n.group);
        ctx.beginPath();
        ctx.arc(mx(pos[id].x), my(pos[id].y), 1.6, 0, Math.PI * 2);
        ctx.fill();
      });
      var view = network.getViewPosition();
      var scale = network.getScale();
      var vw = (minimapEl.clientWidth || w) / scale * s * 0.0;
      ctx.strokeStyle = token("--accent", "#2563eb");
      ctx.lineWidth = 1;
      var cw = (canvas.clientWidth || 1) / scale, ch = (canvas.clientHeight || 1) / scale;
      ctx.strokeRect(mx(view.x - cw / 2), my(view.y - ch / 2), cw * s, ch * s);
      void vw;
    }
    var mmTimer = null;
    network.on("afterDrawing", function () {
      if (mmTimer) return;
      mmTimer = setTimeout(function () { mmTimer = null; drawMinimap(); }, 120);
    });

    /* ----- Theme awareness ------------------------------------------------ */
    var observer = new MutationObserver(function () {
      nodes.get().forEach(function (n) { nodes.update(styleNode(byId[n.id] || n)); });
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    buildLegend();
    emptyDetail();
    return {
      network: network,
      nodes: nodes,
      edges: edges,
      selectNode: selectNode,
      destroy: function () {
        observer.disconnect();
        if (mmTimer) clearTimeout(mmTimer);
        network.destroy();
      },
    };
  }

  window.GraphExplorer = { init: initGraphExplorer, colorFor: colorFor };
})();

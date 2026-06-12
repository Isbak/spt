/* Global, context-aware chat drawer.
 * "Ask this view" sends the current page's data scope so the read-only assist
 * answers against what the user is looking at; "Model a domain" enters the
 * governed authoring conversation for a selected domain. */
(function () {
  "use strict";

  var panel = document.getElementById("chat-panel");
  if (!panel) return;

  var fab = document.getElementById("chat-fab");
  var closeBtn = document.getElementById("chat-close");
  var log = document.getElementById("chat-log");
  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-input");
  var scopeEl = document.getElementById("chat-scope");
  var domainRow = document.getElementById("chat-domain-row");
  var domainSelect = document.getElementById("chat-domain");
  var modeButtons = panel.querySelectorAll(".chat-mode");

  var meta = document.querySelector('meta[name="chat-context"]');
  var context = {
    scope: meta ? meta.getAttribute("data-scope") : "reference",
    label: meta ? meta.getAttribute("data-label") : "Platform",
  };
  var mode = "ask";
  var history = [];
  var domainsLoaded = false;

  scopeEl.textContent = context.label;

  function open() {
    panel.hidden = false;
    fab.setAttribute("aria-expanded", "true");
    input.focus();
  }
  function close() {
    panel.hidden = true;
    fab.setAttribute("aria-expanded", "false");
  }
  fab.addEventListener("click", function () {
    panel.hidden ? open() : close();
  });
  closeBtn.addEventListener("click", close);

  function bubble(role, text) {
    var el = document.createElement("div");
    el.className = "chat-msg chat-msg--" + role;
    el.textContent = text;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  function loadDomains() {
    if (domainsLoaded) return;
    domainsLoaded = true;
    fetch("/api/chat/domains")
      .then(function (r) { return r.json(); })
      .then(function (items) {
        domainSelect.innerHTML = "";
        if (!items.length) {
          var opt = document.createElement("option");
          opt.value = "";
          opt.textContent = "No domains configured";
          domainSelect.appendChild(opt);
          return;
        }
        items.forEach(function (d) {
          var opt = document.createElement("option");
          opt.value = d.id;
          opt.textContent = d.label;
          domainSelect.appendChild(opt);
        });
      });
  }

  modeButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      mode = btn.getAttribute("data-mode");
      modeButtons.forEach(function (b) { b.classList.toggle("is-active", b === btn); });
      domainRow.hidden = mode !== "model";
      if (mode === "model") loadDomains();
      input.placeholder = mode === "model"
        ? "Describe the domain you want to model…"
        : "Ask about what you're looking at…";
    });
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var message = input.value.trim();
    if (!message) return;
    bubble("user", message);
    history.push({ role: "user", content: message });
    input.value = "";
    var pending = bubble("assistant", "…");

    var body = { message: message, mode: mode, context: context, history: history };
    if (mode === "model") body.domain_id = domainSelect.value || null;

    fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        var text = res.ok
          ? (res.data.reply || "(no response)")
          : (res.data.error || "Request failed.");
        pending.textContent = text;
        if (res.ok && res.data.model) {
          var tag = document.createElement("span");
          tag.className = "chat-msg__meta";
          tag.textContent = res.data.provider + " · " + res.data.model;
          pending.appendChild(tag);
        }
        history.push({ role: "assistant", content: text });
      })
      .catch(function () { pending.textContent = "Network error."; });
  });
})();

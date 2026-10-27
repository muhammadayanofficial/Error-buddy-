(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const state = { result: null, id: null, code: "", busy: false };

  // All dynamic content goes through textContent, never innerHTML.
  function h(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = text;
    return e;
  }
  async function api(path, opts = {}) {
    const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
    let data = null;
    try { data = await res.json(); } catch (_) { /* non-JSON response */ }
    if (!res.ok) throw new Error((data && data.error) || `Request failed (${res.status}).`);
    return data;
  }
  function notice(msg, kind) {
    const n = $("#notice");
    n.hidden = !msg; n.textContent = msg || ""; n.className = "notice" + (kind ? " " + kind : "");
  }
  async function loadStatus() {
    const box = $("#api-status");
    try {
      const s = await api("/api/status");
      box.className = "status " + (s.ai_configured ? "ok" : "off");
      $("#api-status-text").textContent = s.ai_configured ? `Gemini ready (${s.model})` : "API key missing";
    } catch (e) { box.className = "status off"; $("#api-status-text").textContent = "Server unreachable"; }
  }
  function setBusy(on, label) {
    state.busy = on;
    ["#btn-review", "#btn-debug", "#btn-local"].forEach((s) => { $(s).disabled = on; });
    if (on) $("#results").replaceChildren(h("p", "empty", label));
  }
  async function run(mode) {
    if (state.busy) return;
    notice("");
    const payload = { code: $("#code").value, language: $("#language").value, error_text: $("#error").value, mode };
    if (!payload.code.trim()) { notice("Paste some code into the editor before running a review.", "bad"); $("#code").focus(); return; }
    if (mode === "debug" && !payload.error_text.trim()) { notice("Add an error message or traceback to use Debug error.", "bad"); $("#error").focus(); return; }
    setBusy(true, "Analysing with Gemini. This usually takes a few seconds.");
    try {
      const data = await api("/api/review", { method: "POST", body: JSON.stringify(payload) });
      state.result = data.result; state.id = data.id; state.code = payload.code;
      setBusy(false);
      showTab(mode === "debug" && data.result.debug ? "debug" : "findings");
    } catch (e) {
      setBusy(false); showTab("findings"); notice(e.message, "bad");
    }
  }
  function updateExport() {
    const a = $("#btn-export");
    a.hidden = !state.id;
    if (state.id) a.href = `/api/reviews/${state.id}/export`;
    $("#count-findings").textContent = state.result ? String(state.result.findings.length) : "";
  }
  function codeBlock(text) { const p = h("pre", "code"); p.textContent = text; return p; }
  function copyBtn(text) {
    const b = h("button", "btn small", "Copy"); b.type = "button";
    b.addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(text); b.textContent = "Copied"; } catch (_) { b.textContent = "Copy failed"; }
      setTimeout(() => { b.textContent = "Copy"; }, 1500);
    });
    return b;
  }
  function list(items, cls) { const ul = h(cls === "ol" ? "ol" : "ul", "steps"); items.forEach((s) => ul.append(h("li", "", s))); return ul; }
  function section(title, ...kids) { const b = h("div", "block"); b.append(h("h3", "", title), ...kids); return b; }

  function renderFindings(r, root) {
    if (r.summary) root.append(h("p", "summary", r.summary));
    if (!r.findings.length) root.append(h("p", "empty", "No findings were reported for this code."));
    r.findings.forEach((f) => {
      const box = h("div", "finding"), t = h("h3");
      t.append(h("span", "sev sev-" + f.severity, f.severity.toUpperCase()), document.createTextNode(f.title));
      box.append(t);
      if (f.reference) box.append(h("span", "ref", f.reference));
      box.append(h("div", "label", "Why it matters"), h("p", "", f.why), h("div", "label", "Recommended fix"), h("p", "fix", f.fix));
      root.append(box);
    });
  }
  function renderDebug(r, root) {
    const d = r.debug;
    if (!d) { root.append(h("p", "empty", "No debugging analysis. Add an error message or traceback and choose Debug error.")); return; }
    [["Likely root cause", d.root_cause], ["Explanation", d.explanation], ["Proposed correction", d.correction]]
      .forEach(([k, v]) => { if (v) root.append(section(k, h("p", "", v))); });
    if (d.verification.length) root.append(section("How to verify the fix", list(d.verification, "ol")));
  }
  function renderImproved(r, root) {
    if (!r.improved) { root.append(h("p", "empty", "No improved version was suggested for this code.")); return; }
    const grid = h("div", "compare"), left = h("div"), right = h("div");
    left.append(h("h3", "", "Original"), codeBlock(state.code));
    right.append(h("h3", "", "Suggested"), codeBlock(r.improved.code), copyBtn(r.improved.code));
    grid.append(left, right); root.append(grid);
    if (r.improved.changes.length) root.append(section("Important changes", list(r.improved.changes)));
  }
  function renderTests(r, root) {
    const t = r.tests;
    if (!t) { root.append(h("p", "empty", "No tests were generated for this code.")); return; }
    root.append(h("p", "note", `${t.framework || "Test"} suggestions. These tests were generated by the model and have not been executed.`), codeBlock(t.code), copyBtn(t.code));
    if (t.explanations.length) root.append(section("What each test checks", list(t.explanations.map((e) => `${e.name}: ${e.checks}`))));
  }
  function showTab(tab) {
    document.querySelectorAll(".tab").forEach((b) => {
      const on = b.dataset.tab === tab; b.classList.toggle("is-active", on); b.setAttribute("aria-selected", String(on));
    });
    const root = $("#results"); root.replaceChildren();
    if (!state.result) root.append(h("p", "empty", "No review yet. Paste code on the left and choose Review code."));
    else ({ findings: renderFindings, debug: renderDebug, improved: renderImproved, tests: renderTests })[tab](state.result, root);
    updateExport();
  }
  async function localCheck() {
    notice("");
    try {
      const d = await api("/api/local-check", { method: "POST", body: JSON.stringify({ code: $("#code").value, language: $("#language").value }) });
      notice(d.message, d.ok === true ? "good" : d.ok === false ? "bad" : "");
    } catch (e) { notice(e.message, "bad"); }
  }
  function switchView(view) {
    document.querySelectorAll(".nav-btn").forEach((b) => {
      const on = b.dataset.view === view; b.classList.toggle("is-active", on);
      if (on) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
    });
    $("#view-workbench").hidden = view !== "workbench"; $("#view-history").hidden = view !== "history";
    if (view === "history") loadHistory();
  }
  async function loadHistory() {
    const box = $("#history-list"); box.replaceChildren(h("p", "empty", "Loading saved reviews."));
    try {
      const { reviews } = await api("/api/reviews");
      box.replaceChildren();
      if (!reviews.length) { box.append(h("p", "empty", "No saved reviews yet. Completed reviews are saved here automatically.")); return; }
      reviews.forEach((r) => {
        const row = h("div", "hrow"), info = h("div", "info");
        info.append(h("div", "sum", r.summary || "(no summary)"),
          h("div", "meta", `#${r.id}   ${r.language}   ${r.finding_count} findings   ${new Date(r.created_at).toLocaleString()}`));
        const open = h("button", "btn small", "Open"); open.type = "button"; open.addEventListener("click", () => openReview(r.id));
        const del = h("button", "btn small danger", "Delete"); del.type = "button";
        del.addEventListener("click", async () => {
          if (!confirm(`Delete review #${r.id}? This cannot be undone.`)) return;
          try {
            await api(`/api/reviews/${r.id}`, { method: "DELETE" });
            if (state.id === r.id) { state.id = null; state.result = null; showTab("findings"); }
          } catch (e) { alert(e.message); }
          loadHistory();
        });
        row.append(info, open, del); box.append(row);
      });
    } catch (e) { box.replaceChildren(h("p", "empty", e.message)); }
  }
  async function openReview(id) {
    try {
      const r = await api(`/api/reviews/${id}`);
      $("#code").value = r.code; $("#error").value = r.error_text; $("#language").value = r.language; syncLanguage(); countChars();
      state.result = r.result; state.id = r.id; state.code = r.code;
      switchView("workbench"); showTab("findings"); notice("");
    } catch (e) { alert(e.message); loadHistory(); }
  }
  const syncLanguage = () => { $("#top-language").textContent = $("#language").value; };
  const countChars = () => { $("#code-count").textContent = $("#code").value.length.toLocaleString(); };

  $("#btn-review").addEventListener("click", () => run("review"));
  $("#btn-debug").addEventListener("click", () => run("debug"));
  $("#btn-local").addEventListener("click", localCheck);
  $("#btn-clear").addEventListener("click", () => {
    $("#code").value = ""; $("#error").value = ""; state.result = null; state.id = null; state.code = "";
    notice(""); countChars(); showTab("findings"); $("#code").focus();
  });
  $("#language").addEventListener("change", syncLanguage);
  $("#code").addEventListener("input", countChars);
  $("#code").addEventListener("keydown", (e) => {  // Tab inserts spaces; Ctrl+Enter runs a review
    if (e.key === "Tab" && !e.shiftKey) { e.preventDefault(); const t = e.target; t.setRangeText("    ", t.selectionStart, t.selectionEnd, "end"); countChars(); }
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) run("review");
  });
  document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
  document.querySelectorAll(".nav-btn").forEach((b) => b.addEventListener("click", () => switchView(b.dataset.view)));
  loadStatus(); syncLanguage(); countChars();
})();

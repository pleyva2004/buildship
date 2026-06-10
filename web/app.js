// buildship trace viewer — renders a run trajectory as the styled TUI, phone-first.
// Mirrors demo_trace.py's beats; spotlights SELF-DEBUG (fail→fix→pass) and REUSE.

// Recorded trajectories bundled so the page works standalone (reliable demo + a public
// URL). A fresh run can be dropped in via the "＋ trace.json" picker.
const TRACES = {
  self_debug: {
    task: "Implement `def make_bar_chart(data: dict, out_path: str) -> str` that saves a bar chart PNG of the dict to out_path with matplotlib (Agg backend).",
    outcome: "built",
    events: [
      { kind: "task", needed_tool: "make_bar_chart" },
      { kind: "gap", tool: "make_bar_chart" },
      { kind: "research", result: "Use matplotlib with the Agg backend; plt.bar(labels, values); fig.savefig(out_path)." },
      { kind: "codegen", attempt: 1, name: "make_bar_chart" },
      { kind: "test", attempt: 1, passed: false, output: "Traceback (most recent call last):\nRuntimeError: no display; backend not set (call matplotlib.use('Agg') first)" },
      { kind: "reject", attempt: 1 },
      { kind: "codegen", attempt: 2, name: "make_bar_chart" },
      { kind: "test", attempt: 2, passed: true, output: "SELF_TEST_OK" },
      { kind: "admit", tool: "make_bar_chart" },
      { kind: "action", result: "SLACK_SENDS_A_MESSAGE_TO_A_CHANNEL successful=True artifact=make_bar_chart.png" },
    ],
  },
  reuse: {
    task: "Implement `def make_bar_chart(data: dict, out_path: str) -> str` … (same capability, requested again).",
    outcome: "reused",
    events: [
      { kind: "task", needed_tool: "make_bar_chart" },
      { kind: "reuse", tool: "make_bar_chart" },
      { kind: "action", result: "SLACK_SENDS_A_MESSAGE_TO_A_CHANNEL successful=True artifact=make_bar_chart.png" },
    ],
  },
};

const esc = (s) =>
  String(s == null ? "" : s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

// Turn one event into a beat line {html} given mutable state (fail counter).
function beatHTML(e, state) {
  switch (e.kind) {
    case "gap":
      return `  <span class="label">gap</span>       no tool for <b>${esc(e.tool)}</b> — must build it`;
    case "research": {
      const first = (e.result || "").split("\n")[0].slice(0, 64);
      return `  <span class="label">research</span>  ${esc(first)}  <span class="dim">(Tavily)</span>`;
    }
    case "reuse":
      return `  <span class="reuse">⚡ REUSE</span>   <b>${esc(e.tool)}</b> already in the library — <b>0 new builds</b>`;
    case "codegen":
      return `  <span class="label">codegen</span>  attempt ${esc(e.attempt)} → <b>${esc(e.name)}</b>  <span class="dim">(Nebius)</span>`;
    case "test":
      if (e.passed) {
        if (state.fails) {
          return `           <span class="selfdebug">✓ SELF-DEBUG — passed after ${state.fails} fix${state.fails > 1 ? "es" : ""}</span>`;
        }
        return `           <span class="ok">✓ test passed</span>`;
      }
      state.fails += 1;
      {
        const lines = (e.output || "").trim().split("\n");
        const why = (lines[lines.length - 1] || "failed").slice(0, 58);
        return `           <span class="fail">✗ test failed</span>  <span class="dim">${esc(why)}</span>  → traceback fed back`;
      }
    case "admit":
      return `  <span class="ok">admit ✓</span>   gated into the library as <b>${esc(e.tool)}</b>`;
    case "action":
      return `  <span class="label">action</span>   ${esc((e.result || "").slice(0, 64))}`;
    default:
      return null;
  }
}

const traceEl = () => document.getElementById("trace");

function clearTrace() {
  traceEl().innerHTML = "";
}

// Append a block (header + beats + outcome) for one trajectory, revealing beats in
// sequence for the "it unfolds" effect.
function renderTrace(traj, startDelay = 0) {
  const root = traceEl();
  const needed = (traj.events.find((e) => e.kind === "task") || {}).needed_tool || "?";

  const head = document.createElement("div");
  head.innerHTML =
    `<span class="head">buildship ▸ ${esc(needed)}</span>\n` +
    `<span class="task">${esc((traj.task || "").slice(0, 110))}</span>` +
    `<span class="rule">${"─".repeat(40)}</span>`;
  root.appendChild(head);

  const state = { fails: 0 };
  const beats = [];
  for (const e of traj.events) {
    const html = beatHTML(e, state);
    if (html != null) beats.push(html);
  }

  let i = 0;
  const step = () => {
    if (i >= beats.length) {
      const out = document.createElement("div");
      out.innerHTML =
        `<span class="rule">${"─".repeat(40)}</span>\n` +
        `  outcome   <span class="outcome ${esc(traj.outcome)}">[${esc(traj.outcome)}]</span>\n\n`;
      root.appendChild(out);
      root.scrollIntoView({ block: "end" });
      return;
    }
    const line = document.createElement("div");
    line.className = "beat";
    line.innerHTML = beats[i];
    root.appendChild(line);
    requestAnimationFrame(() => line.classList.add("show"));
    line.scrollIntoView({ block: "nearest" });
    i += 1;
    setTimeout(step, 650);
  };
  setTimeout(step, startDelay);
}

function play(which) {
  clearTrace();
  for (const b of document.querySelectorAll("#tabs button")) {
    b.classList.toggle("active", b.dataset.trace === which);
  }
  if (which === "both") {
    renderTrace(TRACES.self_debug, 0);
    // queue the reuse trace after the first finishes (rough estimate by beat count)
    setTimeout(() => renderTrace(TRACES.reuse, 0), (TRACES.self_debug.events.length + 2) * 650 + 400);
  } else if (TRACES[which]) {
    renderTrace(TRACES[which], 0);
  }
}

function init() {
  for (const b of document.querySelectorAll("#tabs button")) {
    b.addEventListener("click", () => play(b.dataset.trace));
  }
  const file = document.getElementById("file");
  if (file) {
    file.addEventListener("change", (ev) => {
      const f = ev.target.files[0];
      if (!f) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const traj = JSON.parse(reader.result);
          clearTrace();
          for (const b of document.querySelectorAll("#tabs button")) b.classList.remove("active");
          renderTrace(traj, 0);
        } catch (e) {
          clearTrace();
          traceEl().textContent = "could not parse that trace.json: " + e.message;
        }
      };
      reader.readAsText(f);
    });
  }
  play("self_debug"); // autoplay the money beat on load
}

document.addEventListener("DOMContentLoaded", init);

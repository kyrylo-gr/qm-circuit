// Chip viewer: one chip row picks the program (when there are several), one picks Collapsed / Expanded
// (plus Code when the source is hidden behind the diagram, as in the gallery).
// Hidden parts carry `qc-off`; re-showing one replays its CSS fade-in.
function setupViewer(viewer) {
  if (viewer.dataset.ready) return;
  viewer.dataset.ready = "true";
  const programs = [...viewer.querySelectorAll(".qc-program")];
  let program = programs[0];
  let view = "collapsed";

  const rows = [];
  const row = (labels, onClick) => {
    const div = document.createElement("div");
    div.className = "qc-chips";
    const chips = labels.map((label, i) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "qc-chip";
      chip.textContent = label;
      chip.addEventListener("click", () => onClick(i));
      div.append(chip);
      return chip;
    });
    rows.push(div);
    return chips;
  };

  const views = ["collapsed", "expanded"];
  if (viewer.querySelector(".qc-code")) views.push("code");
  const viewLabels = { collapsed: "Collapsed", expanded: "Expanded", code: "Code" };
  const viewChips = row(views.map((v) => viewLabels[v]), (i) => show(program, views[i]));
  const programChips =
    programs.length > 1 ? row(programs.map((p) => p.dataset.title), (i) => show(programs[i], view)) : [];

  if (rows.length > 1) {
    const wrapper = document.createElement("div");
    wrapper.className = "qc-chip-rows";
    rows.reverse().forEach((r) => wrapper.append(r));
    viewer.prepend(wrapper);
  } else {
    viewer.prepend(rows[0]);
  }

  function show(nextProgram, wantedView) {
    const downgraded = wantedView === "expanded" && !nextProgram.dataset.expandable;
    const nextView = downgraded ? "collapsed" : wantedView;
    programs.forEach((p, i) => {
      p.classList.toggle("qc-off", p !== nextProgram);
      if (programChips[i]) programChips[i].setAttribute("aria-pressed", p === nextProgram);
    });
    const code = nextProgram.querySelector(".qc-code");
    if (code) {
      code.classList.toggle("qc-off", nextView !== "code");
      nextProgram.querySelector(".qc-diagram").classList.toggle("qc-off", nextView === "code");
    }
    if (nextView !== "code") {
      nextProgram.querySelectorAll("[data-view]").forEach((link) => {
        link.classList.toggle("qc-off", link.dataset.view !== nextView);
      });
    }
    viewChips.forEach((chip, i) => chip.setAttribute("aria-pressed", views[i] === nextView));
    // With several programs the chip stays in place, disabled, so the row does not jump; alone it just hides.
    if (programs.length > 1) {
      viewChips[1].disabled = !nextProgram.dataset.expandable;
      viewChips[1].title = nextProgram.dataset.expandable ? "" : "This program calls no helper function";
    } else {
      viewChips[1].classList.toggle("qc-off", !nextProgram.dataset.expandable);
    }
    program = nextProgram;
    if (!downgraded) view = nextView;
  }

  show(program, view);
}

document$.subscribe(() => document.querySelectorAll(".qc-viewer").forEach(setupViewer));

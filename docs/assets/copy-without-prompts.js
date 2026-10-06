// The copy button on an interactive session (a pycon block) copies only the
// code: the ">>> " and "... " prompts are removed and output lines are left
// out, so the result can be pasted into a file or a terminal.
document.addEventListener(
  "click",
  (event) => {
    const button = event.target.closest("[data-clipboard-target]");
    if (!button) return;
    const target = document.querySelector(button.dataset.clipboardTarget);
    if (!target || !target.closest(".language-pycon")) return;
    const code = target.textContent
      .split("\n")
      .filter((line) => /^(>>>|\.\.\.)( |$)/.test(line))
      .map((line) => line.slice(4))
      .join("\n");
    button.setAttribute("data-clipboard-text", code + "\n");
  },
  true,
);

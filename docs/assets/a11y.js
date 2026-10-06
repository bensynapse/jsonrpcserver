// Small accessibility fixes for Material for MkDocs defaults. They run after
// Material has rendered each page, including after instant navigation.
document$.subscribe(() => {
  // The search overlay is a dialog, so it needs a name.
  const search = document.querySelector(".md-search");
  if (search && !search.hasAttribute("aria-label")) {
    search.setAttribute("aria-label", "Search");
  }
  document.querySelectorAll(".md-code__nav").forEach((nav, i) => {
    // Each code block's toolbar is a nav landmark; give each a distinct name.
    nav.setAttribute("aria-label", `Code block ${i + 1} actions`);
  });
  document.querySelectorAll(".highlight pre > code").forEach((code) => {
    // A code block that scrolls sideways must be reachable with the keyboard.
    if (code.scrollWidth > code.clientWidth) {
      code.setAttribute("tabindex", "0");
    }
  });
  document.querySelectorAll(".md-typeset__scrollwrap").forEach((wrap, i) => {
    // So must a table that's wider than the screen.
    if (wrap.scrollWidth > wrap.clientWidth) {
      wrap.setAttribute("tabindex", "0");
      wrap.setAttribute("role", "region");
      wrap.setAttribute("aria-label", `Table ${i + 1}, scrolls sideways`);
    }
  });
});

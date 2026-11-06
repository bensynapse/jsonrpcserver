// The version menu, and a notice on versions that aren't the stable one.
//
// .github/scripts/build_versions.py adds this file to every copy of the docs
// it builds: the stable docs at the site root, and each version in a folder
// like /5.x/. It reads versions.json at the site root.
//
// Material has a version menu of its own (extra.version.provider: mike), but
// it looks for versions.json one level above the docs. At the site root that
// is outside the site. Its button also fails axe's label-in-name check. So
// this draws the same markup, with Material's styles, in every copy.
(function () {
  "use strict";
  var data = document.getElementById("__config");
  if (!data) return;
  var config = JSON.parse(data.textContent);
  var base = new URL(config.base, location.href);
  var folder = base.pathname.split("/").filter(Boolean).pop();
  // Version folders are named like 5.x or 6.0. See LINES in build_versions.py.
  var inFolder = /^\d+\.(\d+|x)$/.test(folder);
  var root = inFolder ? new URL("../", base) : base;
  // This page's address inside its copy of the docs, like "migration/".
  var path = location.pathname.slice(base.pathname.length).replace(/index\.html$/, "");

  function element(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  // Open the same page in another version if it has one, else its home page.
  function open(home) {
    fetch(new URL("sitemap.xml", home))
      .then(function (response) {
        if (!response.ok) throw new Error(response.statusText);
        return response.text();
      })
      .then(function (text) {
        var xml = new DOMParser().parseFromString(text, "application/xml");
        var urls = Array.prototype.map.call(xml.querySelectorAll("loc"), function (loc) {
          return loc.textContent.trim();
        });
        // Every copy lists the root's addresses. The shortest is the home page.
        var first = urls.reduce(function (a, b) { return b.length < a.length ? b : a; }, urls[0]);
        var found = urls.indexOf(first + path) !== -1;
        location.href = found ? new URL(path, home).href + location.hash : home.href;
      })
      .catch(function () {
        location.href = home.href;
      });
  }

  function addMenu(versions, current, stable) {
    var topic = document.querySelector(".md-header__topic");
    if (!topic) return;
    var menu = element("div", "md-version");
    // The visible text is the button's name, which is what axe asks for.
    var button = element("button", "md-version__current", current.title);
    button.setAttribute("title", config.translations["select.version"]);
    var list = element("ul", "md-version__list");
    versions.forEach(function (version) {
      if (version.properties && version.properties.hidden) return;
      var home = version === stable ? root : new URL(version.version + "/", root);
      var link = element("a", "md-version__link", version.title);
      link.href = home.href;
      link.addEventListener("click", function (event) {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey) return;
        event.preventDefault();
        open(home);
      });
      var item = element("li", "md-version__item");
      item.appendChild(link);
      list.appendChild(item);
    });
    menu.appendChild(button);
    menu.appendChild(list);
    topic.appendChild(menu);
  }

  function addNotice(current, stable) {
    var header = document.querySelector(".md-header");
    if (!header) return;
    // The canonical link is the same page at the root, when the root has it.
    var canonical = document.querySelector('link[rel="canonical"]');
    // A dark bar like the "not on PyPI yet" one, so extra.css styles its link.
    var notice = element("aside", "md-banner");
    notice.setAttribute("data-version-notice", "");
    notice.setAttribute("aria-label", "Version notice");
    var inner = element("div", "md-banner__inner md-grid md-typeset");
    inner.appendChild(document.createTextNode(
      "These docs are for jsonrpcserver " + current.title + ". The stable release is " +
      stable.title + ". "
    ));
    var link = element("a", "", canonical ? "Read this page in the stable docs" : "Go to the stable docs");
    link.href = canonical ? canonical.href : root.href;
    inner.appendChild(link);
    inner.appendChild(document.createTextNode("."));
    notice.appendChild(inner);
    header.parentNode.insertBefore(notice, header);
  }

  fetch(new URL("versions.json", root))
    .then(function (response) {
      if (!response.ok) throw new Error(response.statusText);
      return response.json();
    })
    .then(function (versions) {
      var stable = versions.filter(function (v) { return v.aliases.indexOf("stable") !== -1; })[0];
      if (!stable) return;
      var current = inFolder
        ? versions.filter(function (v) { return v.version === folder; })[0]
        : stable;
      if (!current) return;
      addMenu(versions, current, stable);
      if (current !== stable) addNotice(current, stable);
    })
    .catch(function () {
      // No versions.json: a plain mkdocs build, not the versioned site.
    });
})();

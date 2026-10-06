"""Check the built docs site in a real browser.

Usage: python .github/scripts/check_site.py SITE_DIR AXE_JS

Serves SITE_DIR at http://localhost:8765/jsonrpcserver/, the same path as on
GitHub Pages, and opens every page in the sitemap, plus the 404 page, in light
and dark mode at desktop and phone widths. It fails if:

- axe-core finds a serious or critical accessibility problem,
- a page scrolls sideways, has a JavaScript error, or has no visible h1,
  description or canonical link,
- a link to another page of the site, or to an anchor on it, is broken.

Needs playwright (pip install playwright, then playwright install chromium).
"""

import functools
import re
import sys
import threading
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
from urllib.parse import urldefrag

from playwright.sync_api import Page, sync_playwright

PORT = 8765
BASE = f"http://localhost:{PORT}/jsonrpcserver/"
LIVE = "https://bensynapse.github.io/jsonrpcserver/"
VIEWPORTS = {"desktop": (1280, 900), "phone": (375, 812)}


class Handler(SimpleHTTPRequestHandler):
    """Serve the site under /jsonrpcserver/, with 404.html for missing pages."""

    def translate_path(self, path: str) -> str:
        path = path.split("?", 1)[0].split("#", 1)[0]
        if not path.startswith("/jsonrpcserver/"):
            return ""
        return super().translate_path(path[len("/jsonrpcserver") :])

    def send_error(self, code: int, message: Any = None, explain: Any = None) -> None:
        if code != 404:
            super().send_error(code, message, explain)
            return
        body = (Path(self.directory) / "404.html").read_bytes()
        self.send_response(404)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        pass


class Server(ThreadingHTTPServer):
    def handle_error(self, request: Any, client_address: Any) -> None:
        # The browser often drops a connection it no longer needs.
        if not isinstance(sys.exc_info()[1], ConnectionError):
            super().handle_error(request, client_address)


def record(errors: List[str], exc: Exception) -> None:
    errors.append(str(exc))


def page_info(page: Page) -> Dict[str, Any]:
    return page.evaluate(
        """() => {
        const q = (s) => document.querySelector(s);
        const h1 = [...document.querySelectorAll(".md-content h1")]
          .filter((h) => h.offsetParent !== null);
        const doc = document.documentElement;
        return {
          h1: h1.length,
          description: (q('meta[name="description"]') || {}).content || "",
          canonical: (q('link[rel="canonical"]') || {}).href || "",
          overflow: doc.scrollWidth > doc.clientWidth,
          links: [...document.querySelectorAll("a[href]")].map((a) => a.href),
          ids: [...document.querySelectorAll("[id]")].map((e) => e.id),
        };
      }"""
    )


def axe_problems(page: Page, axe: str) -> List[str]:
    page.add_script_tag(content=axe)
    violations: List[Dict[str, Any]] = page.evaluate(
        """async () => {
        const result = await axe.run(document, {
          runOnly: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"],
        });
        return result.violations.map((v) => ({
          id: v.id, impact: v.impact, nodes: v.nodes.map((n) => n.target.join(" ")),
        }));
      }"""
    )
    return [
        f"{v['id']} ({v['impact']}): {', '.join(v['nodes'][:3])}"
        for v in violations
        if v["impact"] in ("serious", "critical")
    ]


def main(site: Path, axe: str) -> int:
    handler = functools.partial(Handler, directory=str(site))
    server = Server(("localhost", PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    sitemap = (site / "sitemap.xml").read_text()
    urls = re.findall(r"<loc>(.*?)</loc>", sitemap)
    pages = [url.replace(LIVE, BASE) for url in urls]
    problems: List[str] = []
    links: Set[str] = set()
    ids: Dict[str, Set[str]] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for scheme in ("light", "dark"):
            for name, (width, height) in VIEWPORTS.items():
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    color_scheme=scheme,
                    is_mobile=name == "phone",
                )
                page = context.new_page()
                errors: List[str] = []
                page.on("pageerror", functools.partial(record, errors))
                for url in [*pages, BASE + "no-such-page/"]:
                    errors.clear()
                    response = page.goto(url, wait_until="networkidle")
                    where = f"{url} ({scheme}, {name})"
                    expected = 404 if url.endswith("no-such-page/") else 200
                    status = response.status if response else None
                    if status != expected:
                        problems.append(f"{where}: status {status}")
                    info = page_info(page)
                    if info["h1"] != 1:
                        problems.append(f"{where}: {info['h1']} visible h1")
                    if not info["description"]:
                        problems.append(f"{where}: no description")
                    if expected == 200 and not info["canonical"]:
                        problems.append(f"{where}: no canonical link")
                    if info["overflow"]:
                        problems.append(f"{where}: the page scrolls sideways")
                    problems.extend(f"{where}: JavaScript error {e}" for e in errors)
                    problems.extend(f"{where}: {p}" for p in axe_problems(page, axe))
                    links.update(info["links"])
                    ids[url] = set(info["ids"])
                context.close()
        browser.close()
    problems.extend(check_links(links, ids))
    server.shutdown()
    for problem in problems:
        print(problem)
    print(f"{len(pages) + 1} pages, 4 views each, {len(problems)} problems")
    return 1 if problems else 0


def check_links(links: Set[str], ids: Dict[str, Set[str]]) -> List[str]:
    problems: List[str] = []
    status: Dict[str, int] = {}
    for link in sorted(links):
        # The banner and the 404 page link to the live site's address.
        url, fragment = urldefrag(link.replace(LIVE, BASE))
        if not url.startswith(BASE):
            continue
        if url not in status:
            status[url] = fetch_status(url)
        if status[url] != 200:
            problems.append(f"broken link: {link} ({status[url]})")
        elif fragment and url in ids and fragment not in ids[url]:
            problems.append(f"broken anchor: {link}")
    return problems


def fetch_status(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return exc.code


def parse_args(argv: List[str]) -> Tuple[Path, str]:
    if len(argv) != 2:
        raise SystemExit(__doc__)
    return Path(argv[0]), Path(argv[1]).read_text()


if __name__ == "__main__":
    sys.exit(main(*parse_args(sys.argv[1:])))

"""The rebuild crew.

A pool of worker threads - the "agents" - share a queue of jobs. Some jobs are pages to
read, some are assets to download. Reading a page adds more jobs (its stylesheets, scripts,
images, and same-site links), so the crew spreads out across the whole front end and keeps
going until there is nothing left or a limit is hit.

Only the front end, and only the site you pointed it at (same origin). It never follows a
link off your domain, and it never tries to reach a back end. Everything runs on CPU with
the standard library, so there is no GPU and no API key anywhere in here.
"""
from __future__ import annotations

import os
import posixpath
import queue
import re
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser

from .live import Dashboard
from .safety import USER_AGENT, redact_text, validate_target

# Attributes that hold a URL, by the tag they appear on.
ASSET_ATTRS = {
    ("link", "href"), ("script", "src"), ("img", "src"), ("img", "data-src"),
    ("source", "src"), ("video", "poster"), ("audio", "src"), ("embed", "src"),
    ("object", "data"), ("track", "src"), ("use", "href"),
}
PAGE_ATTRS = {("a", "href"), ("area", "href")}
SRCSET_TAGS = {"img", "source"}
TEXT_EXT = {".css", ".js", ".mjs", ".json", ".svg", ".xml", ".txt", ".map", ".webmanifest", ".html", ".htm"}
CSS_URL = re.compile(r"""url\(\s*['"]?([^'")]+?)['"]?\s*\)""", re.I)
CSS_IMPORT = re.compile(r"""@import\s+(?:url\(\s*)?['"]([^'")]+)['"]""", re.I)


@dataclass
class Job:
    kind: str  # "page" or "asset"
    url: str
    depth: int = 0


@dataclass
class Config:
    out_dir: str = "rebuild"
    agents: int = 24
    max_pages: int = 40
    max_assets: int = 600
    max_depth: int = 3
    max_bytes: int = 8_000_000
    timeout: float = 15.0
    allow_loopback: bool = False
    dashboard_mode: str = "auto"


@dataclass
class Result:
    seed: str
    out_dir: str
    pages: int = 0
    assets: int = 0
    bytes: int = 0
    skipped: int = 0
    errors: list = field(default_factory=list)
    seconds: float = 0.0

    def summary(self) -> str:
        return (f"{self.pages} pages, {self.assets} assets, {self.bytes/1_000_000:.1f} MB "
                f"in {self.seconds:.1f}s with {len(self.errors)} error(s)")


class _Collector(HTMLParser):
    """Pulls every URL-bearing attribute and inline style out of one HTML page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.assets: list[str] = []
        self.pages: list[str] = []
        self.css_blocks: list[str] = []
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "style":
            self._in_style = True
        if tag == "link":
            rel = (d.get("rel") or "").lower()
            if d.get("href") and rel and {"stylesheet", "icon", "apple-touch-icon", "manifest", "preload", "mask-icon"} & set(rel.split()):
                self.assets.append(d["href"])
        for (t, a) in ASSET_ATTRS:
            if t == tag and d.get(a):
                self.assets.append(d[a])
        for (t, a) in PAGE_ATTRS:
            if t == tag and d.get(a):
                self.pages.append(d[a])
        if tag in SRCSET_TAGS and d.get("srcset"):
            for part in d["srcset"].split(","):
                token = part.strip().split(" ")[0]
                if token:
                    self.assets.append(token)
        if d.get("style"):
            self.css_blocks.append(d["style"])

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_style and data.strip():
            self.css_blocks.append(data)


class Rebuilder:
    def __init__(self, seed: str, config: Config):
        self.cfg = config
        parsed = validate_target(seed, allow_loopback=config.allow_loopback)
        self.seed = seed
        self.origin = (parsed.scheme, parsed.hostname, parsed.port or _default_port(parsed.scheme))
        self.q: "queue.Queue[Job|None]" = queue.Queue()
        self.seen: set[str] = set()
        self.lock = threading.Lock()
        self.result = Result(seed=seed, out_dir=config.out_dir)
        self.board = Dashboard(config.agents, mode=config.dashboard_mode)
        self._active = 0
        self._active_lock = threading.Lock()

    # -- origin / path helpers ------------------------------------------------
    def _same_origin(self, url: str) -> bool:
        p = urllib.parse.urlparse(url)
        if p.scheme not in ("http", "https"):
            return False
        return (p.scheme, p.hostname, p.port or _default_port(p.scheme)) == self.origin or \
            (p.hostname, p.port or _default_port(p.scheme)) == (self.origin[1], self.origin[2])

    def local_path(self, url: str) -> str:
        """Deterministic output path for a URL, so we can rewrite links before a file exists."""
        p = urllib.parse.urlparse(url)
        path = p.path or "/"
        if path.endswith("/"):
            path += "index.html"
        elif not posixpath.splitext(path)[1]:
            path += "/index.html"
        path = path.lstrip("/")
        if p.query:
            root, ext = posixpath.splitext(path)
            tag = "%08x" % (abs(hash(p.query)) & 0xFFFFFFFF)
            path = f"{root}__{tag}{ext or '.html'}"
        safe = [seg for seg in path.split("/") if seg not in ("", ".", "..")]
        return "/".join(safe) or "index.html"

    def _relative(self, from_url: str, to_url: str) -> str:
        a = self.local_path(from_url)
        b = self.local_path(to_url)
        rel = posixpath.relpath(b, posixpath.dirname(a) or ".")
        return rel

    # -- queue plumbing -------------------------------------------------------
    def _add(self, job: Job) -> None:
        norm = _strip_fragment(job.url)
        with self.lock:
            if norm in self.seen:
                return
            if job.kind == "page" and self.result_pages_scheduled >= self.cfg.max_pages:
                return
            if job.kind == "asset" and self.result_assets_scheduled >= self.cfg.max_assets:
                return
            self.seen.add(norm)
            if job.kind == "page":
                self.result_pages_scheduled += 1
            else:
                self.result_assets_scheduled += 1
        self.q.put(job)

    result_pages_scheduled = 0
    result_assets_scheduled = 0

    # -- the run --------------------------------------------------------------
    def run(self) -> Result:
        start = time.time()
        self._add(Job("page", self.seed, 0))
        self.board.start()
        workers = [threading.Thread(target=self._worker, args=(i,), daemon=True)
                   for i in range(self.cfg.agents)]
        for w in workers:
            w.start()
        self.q.join()
        for _ in workers:
            self.q.put(None)
        for w in workers:
            w.join(timeout=2)
        self.board.tick(self.result.pages + self.result.assets,
                        self.result_pages_scheduled + self.result_assets_scheduled)
        self.board.stop()
        self.result.seconds = round(time.time() - start, 2)
        _write_manifest(self.cfg.out_dir, self.result, self.seed)
        return self.result

    def _worker(self, agent_id: int) -> None:
        while True:
            job = self.q.get()
            if job is None:
                self.board.set(agent_id, "done")
                self.q.task_done()
                return
            try:
                self._do(agent_id, job)
            except Exception as e:  # one bad page must never take the crew down
                self.result.errors.append(f"{job.url}: {e}")
                self.board.set(agent_id, "error", _short_url(job.url))
            finally:
                self.board.tick(self.result.pages + self.result.assets,
                                self.result_pages_scheduled + self.result_assets_scheduled)
                self.q.task_done()

    def _do(self, agent_id: int, job: Job) -> None:
        verb = "reading" if job.kind == "page" else "fetching"
        self.board.set(agent_id, verb, _short_url(job.url))
        data, ctype = self._fetch(job.url)
        if data is None:
            with self.lock:
                self.result.skipped += 1
            return
        if job.kind == "page":
            self._handle_page(job, data, ctype)
        else:
            self._handle_asset(job, data, ctype)

    # -- fetching -------------------------------------------------------------
    def _fetch(self, url: str):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=self.cfg.timeout) as resp:
            ctype = resp.headers.get("Content-Type", "")
            length = resp.headers.get("Content-Length")
            if length and int(length) > self.cfg.max_bytes:
                return None, ctype
            data = resp.read(self.cfg.max_bytes + 1)
        if len(data) > self.cfg.max_bytes:
            return None, ctype
        return data, ctype

    # -- page handling --------------------------------------------------------
    def _handle_page(self, job: Job, data: bytes, ctype: str):
        html = data.decode("utf-8", errors="replace")
        col = _Collector()
        try:
            col.feed(html)
        except Exception:
            pass
        rewrites: dict[str, str] = {}
        for raw in col.assets:
            self._consider_asset(job.url, raw, rewrites)
        for block in col.css_blocks:
            for m in list(CSS_URL.finditer(block)) + list(CSS_IMPORT.finditer(block)):
                self._consider_asset(job.url, m.group(1), rewrites)
        if job.depth < self.cfg.max_depth:
            for raw in col.pages:
                abs_url = _absolute(job.url, raw)
                if abs_url and self._same_origin(abs_url) and _looks_like_page(abs_url):
                    self._add(Job("page", abs_url, job.depth + 1))
                    rewrites.setdefault(raw, self._relative(job.url, abs_url))
        out = _apply_rewrites(redact_text(html), rewrites)
        self._save(self.local_path(job.url), out.encode("utf-8"))
        with self.lock:
            self.result.pages += 1
            self.result.bytes += len(out)

    def _consider_asset(self, page_url: str, raw: str, rewrites: dict):
        if not raw or raw.startswith(("data:", "javascript:", "mailto:", "tel:", "#")):
            return
        abs_url = _absolute(page_url, raw)
        if not abs_url or not self._same_origin(abs_url):
            return
        self._add(Job("asset", abs_url, 0))
        rewrites.setdefault(raw, self._relative(page_url, abs_url))

    # -- asset handling -------------------------------------------------------
    def _handle_asset(self, job: Job, data: bytes, ctype: str):
        path = self.local_path(job.url)
        ext = posixpath.splitext(path)[1].lower()
        if ext in TEXT_EXT or ctype.startswith(("text/", "application/javascript", "application/json")):
            text = data.decode("utf-8", errors="replace")
            if ext == ".css" or "css" in ctype:
                text = self._rewrite_css(job.url, text)
            data = redact_text(text).encode("utf-8")
        self._save(path, data)
        with self.lock:
            self.result.assets += 1
            self.result.bytes += len(data)

    def _rewrite_css(self, css_url: str, text: str) -> str:
        rewrites: dict[str, str] = {}
        for m in list(CSS_URL.finditer(text)) + list(CSS_IMPORT.finditer(text)):
            raw = m.group(1)
            if raw.startswith(("data:", "#")):
                continue
            abs_url = _absolute(css_url, raw)
            if abs_url and self._same_origin(abs_url):
                self._add(Job("asset", abs_url, 0))
                rewrites.setdefault(raw, self._relative(css_url, abs_url))
        return _apply_rewrites(text, rewrites)

    # -- disk -----------------------------------------------------------------
    def _save(self, rel_path: str, data: bytes):
        full = os.path.join(self.cfg.out_dir, rel_path)
        os.makedirs(os.path.dirname(full) or self.cfg.out_dir, exist_ok=True)
        with open(full, "wb") as fh:
            fh.write(data)


# -- module helpers -----------------------------------------------------------
def _default_port(scheme: str) -> int:
    return 443 if scheme == "https" else 80


def _strip_fragment(url: str) -> str:
    """Drop the #fragment and make sure the path is at least '/', so '' and '/' are one URL."""
    p = urllib.parse.urlparse(urllib.parse.urldefrag(url)[0])
    return urllib.parse.urlunparse((p.scheme, p.netloc, p.path or "/", p.params, p.query, ""))


def _absolute(base: str, raw: str):
    try:
        return _strip_fragment(urllib.parse.urljoin(base, raw.strip()))
    except ValueError:
        return None


def _looks_like_page(url: str) -> bool:
    ext = posixpath.splitext(urllib.parse.urlparse(url).path)[1].lower()
    return ext in ("", ".html", ".htm", ".php", ".asp", ".aspx")


def _short_url(url: str) -> str:
    p = urllib.parse.urlparse(url)
    return (p.path or "/") + ("?" + p.query if p.query else "")


def _apply_rewrites(text: str, rewrites: dict) -> str:
    for raw in sorted(rewrites, key=len, reverse=True):
        local = rewrites[raw]
        for quote in ('"', "'", "(", " "):
            text = text.replace(f"{quote}{raw}", f"{quote}{local}")
    return text


def _write_manifest(out_dir: str, result: Result, seed: str):
    os.makedirs(out_dir, exist_ok=True)
    lines = [
        "# Rebuilt front end",
        "",
        f"Source (a site the operator confirmed they own): {seed}",
        f"Result: {result.summary()}",
        "",
        "This is a static copy of the public front end only. There is no back-end code here -",
        "a site's server logic is never sent to the browser, so it cannot be and was not copied.",
        "Open index.html to preview, then rebuild it into clean code with the site-re-agent skill.",
    ]
    if result.errors:
        lines += ["", "## Skipped / errors", *[f"- {e}" for e in result.errors[:40]]]
    with open(os.path.join(out_dir, "REBUILD.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def rebuild(seed: str, config: Config) -> Result:
    return Rebuilder(seed, config).run()

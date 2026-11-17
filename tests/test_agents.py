"""The rebuild crew, exercised against a small site served on localhost.

No network: a throwaway http.server hands out a few linked pages and assets, and we check
that the agents crawl them, download same-origin assets only, rewrite links to local paths,
and never wander off the origin.
"""
from __future__ import annotations

import http.server
import os
import threading

import pytest

from sitere.agents import Config, Rebuilder, rebuild

PAGES = {
    "/": b"""<!doctype html><html><head>
        <link rel="stylesheet" href="/css/app.css">
        <link rel="icon" href="/favicon.ico">
        <script src="/js/app.js"></script>
        <style>body{background:url('/img/bg.png')}</style>
    </head><body>
        <img src="/img/logo.png" srcset="/img/logo.png 1x, /img/logo2x.png 2x">
        <a href="/about">About</a>
        <a href="/about#team">Team anchor</a>
        <a href="https://evil.example.com/steal">offsite</a>
        <a href="mailto:x@y.com">mail</a>
    </body></html>""",
    "/about": b"""<!doctype html><html><head><link rel="stylesheet" href="/css/app.css"></head>
        <body><h1>About</h1><a href="/">home</a></body></html>""",
    "/css/app.css": b"@import 'base.css';\nbody{background:url(/img/bg.png)}\n.x{background:url('https://cdn.example.com/x.png')}",
    "/css/base.css": b".base{color:#fff}",
    "/js/app.js": b"console.log('SECRET sk_live_abcdefghijklmnop1234 here');",
    "/img/logo.png": b"\x89PNG\r\n\x1a\nlogo",
    "/img/logo2x.png": b"\x89PNG\r\n\x1a\nlogo2x",
    "/img/bg.png": b"\x89PNG\r\n\x1a\nbg",
    "/favicon.ico": b"ico",
}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = PAGES.get(self.path.split("?")[0])
        if body is None:
            self.send_error(404)
            return
        ctype = "text/html"
        if self.path.endswith(".css"):
            ctype = "text/css"
        elif self.path.endswith(".js"):
            ctype = "application/javascript"
        elif self.path.endswith((".png", ".ico")):
            ctype = "image/png"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture()
def site():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()
    srv.server_close()


def cfg(tmp_path, **kw):
    kw.setdefault("agents", 8)
    kw.setdefault("allow_loopback", True)
    kw.setdefault("dashboard_mode", "quiet")
    return Config(out_dir=str(tmp_path / "out"), **kw)


def read(tmp_path, rel):
    with open(tmp_path / "out" / rel, "rb") as fh:
        return fh.read()


def test_crawls_pages_and_downloads_same_origin_assets(site, tmp_path):
    res = rebuild(site, cfg(tmp_path))
    out = tmp_path / "out"
    assert (out / "index.html").exists()
    assert (out / "about" / "index.html").exists()
    assert (out / "css" / "app.css").exists()
    assert (out / "css" / "base.css").exists()  # reached via @import
    assert (out / "js" / "app.js").exists()
    assert (out / "img" / "logo.png").exists()
    assert (out / "img" / "logo2x.png").exists()  # from srcset
    assert (out / "img" / "bg.png").exists()       # from inline <style> and css
    assert (out / "favicon.ico").exists()
    assert res.pages == 2
    assert res.errors == []


def test_never_leaves_the_origin(site, tmp_path):
    rebuild(site, cfg(tmp_path))
    # offsite link and third-party cdn asset must not be saved anywhere
    saved = []
    for root, _dirs, files in os.walk(tmp_path / "out"):
        saved += files
    assert not any("steal" in f for f in saved)
    assert not any(f == "x.png" for f in saved)


def test_links_are_rewritten_to_local_relative_paths(site, tmp_path):
    rebuild(site, cfg(tmp_path))
    index = read(tmp_path, "index.html").decode()
    assert 'href="css/app.css"' in index
    assert 'src="js/app.js"' in index
    assert 'href="about/index.html"' in index
    # offsite links are left untouched so the page still points at the real thing
    assert "https://evil.example.com/steal" in index
    # a page one level deep points back up correctly
    about = read(tmp_path, "about/index.html").decode()
    assert "../css/app.css" in about
    assert 'href="../index.html"' in about


def test_css_imports_and_urls_are_rewritten(site, tmp_path):
    rebuild(site, cfg(tmp_path))
    css = read(tmp_path, "css/app.css").decode()
    assert "base.css" in css and "@import" in css
    assert "../img/bg.png" in css
    assert "https://cdn.example.com/x.png" in css  # third-party left alone


def test_secrets_are_redacted_before_saving(site, tmp_path):
    rebuild(site, cfg(tmp_path))
    js = read(tmp_path, "js/app.js").decode()
    assert "sk_live_abcdefghijklmnop1234" not in js
    assert "[REDACTED]" in js


def test_anchor_fragments_do_not_make_a_duplicate_page(site, tmp_path):
    res = rebuild(site, cfg(tmp_path))
    assert res.pages == 2  # "/about" and "/about#team" collapse to one


def test_max_pages_limit_is_respected(site, tmp_path):
    res = rebuild(site, cfg(tmp_path, max_pages=1))
    assert res.pages == 1
    assert not (tmp_path / "out" / "about" / "index.html").exists()


def test_offsite_seed_is_refused(tmp_path):
    from sitere.safety import Refused
    with pytest.raises(Refused):
        Rebuilder("http://127.0.0.1:1/", cfg(tmp_path, allow_loopback=False))


def test_manifest_is_written(site, tmp_path):
    rebuild(site, cfg(tmp_path, operator="Madara"))
    manifest = read(tmp_path, "REBUILD.md").decode()
    assert "front end" in manifest
    assert "never sent to the" in manifest  # back end cannot be copied
    assert "Run by: Madara" in manifest      # the operator is stamped on the run


def test_cli_rebuild_runs_end_to_end(site, tmp_path):
    from sitere.__main__ import main
    out = str(tmp_path / "cli-out")
    code = main(["rebuild", site, "--i-own-this", "--allow-local", "--plain", "--save",
                 "--by", "Madara", "--out", out, "--agents", "6"])
    assert code == 0
    assert os.path.exists(os.path.join(out, "index.html"))
    assert not os.path.exists(out + ".preview-tmp")  # staging cleaned up
    with open(os.path.join(out, "REBUILD.md"), encoding="utf-8") as fh:
        manifest = fh.read()
    assert "Madara" in manifest  # the run is stamped with the operator's name
    assert "entertainment" in manifest.lower()


def test_cli_rebuild_without_save_keeps_nothing(site, tmp_path):
    from sitere.__main__ import main
    out = str(tmp_path / "nosave-out")
    # non-interactive and no --save: must not write the output folder
    code = main(["rebuild", site, "--i-own-this", "--allow-local", "--plain", "--out", out, "--agents", "6"])
    assert code == 0
    assert not os.path.exists(os.path.join(out, "index.html"))
    assert not os.path.exists(out + ".preview-tmp")

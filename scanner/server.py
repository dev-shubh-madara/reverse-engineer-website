"""Local scanner server: collects a site's public front-end files into a ZIP for Claude.

Stdlib only. Never logs in, never probes hidden paths, only fetches what the page itself links to.
"""
import html.parser
import ipaddress
import json
import os
import re
import socket
import urllib.parse
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT.parent / "out"
UA = "site-re-agent/0.1 (owner-authorised scan)"
MAX_FILES, MAX_BYTES = 40, 2_000_000
OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("RE_MODEL", "qwen2.5-coder:7b")


def _public_host(host: str) -> bool:
    if os.getenv("RE_ALLOW_LOCAL") == "1":
        return True
    try:
        for info in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
    except socket.gaierror:
        return False
    return True


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read(MAX_BYTES)


class _Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and a.get("src"):
            self.assets.append(a["src"])
        if tag == "link" and a.get("rel") in ("stylesheet", "icon") and a.get("href"):
            self.assets.append(a["href"])


ENDPOINT_RX = re.compile(r"""(?:fetch|axios\.\w+|\.open)\(\s*(?:['"]\w+['"]\s*,\s*)?['"`]([^'"`]{2,200})['"`]""")
LIB_HINTS = {"react": "React", "vue": "Vue", "angular": "Angular", "jquery": "jQuery",
             "three": "three.js", "gsap": "GSAP", "tailwind": "Tailwind", "bootstrap": "Bootstrap"}


def scan(url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Enter a full http(s) URL")
    if not _public_host(parsed.hostname):
        raise ValueError("Private/local addresses are blocked")
    site = OUT / re.sub(r"[^\w.-]", "_", parsed.netloc)
    site.mkdir(parents=True, exist_ok=True)

    page = _get(url)
    (site / "index.html").write_bytes(page)
    parser = _Links()
    parser.feed(page.decode("utf-8", "replace"))

    files, endpoints, libs = ["index.html"], set(), set()
    for ref in parser.assets[:MAX_FILES]:
        full = urllib.parse.urljoin(url, ref)
        if urllib.parse.urlparse(full).netloc != parsed.netloc:
            libs.add(urllib.parse.urlparse(full).netloc + " (external)")
            continue
        try:
            body = _get(full)
        except Exception:
            continue
        name = re.sub(r"[^\w.-]", "_", urllib.parse.urlparse(full).path.strip("/")) or "asset"
        (site / name).write_bytes(body)
        files.append(name)
        text = body.decode("utf-8", "replace")
        endpoints.update(ENDPOINT_RX.findall(text))
        libs.update(v for k, v in LIB_HINTS.items() if k in text.lower())
    endpoints.update(ENDPOINT_RX.findall(page.decode("utf-8", "replace")))

    report = {"url": url, "files": files, "endpoints": sorted(endpoints)[:60], "libraries": sorted(libs)}
    report["summary"] = _summarise(report, page.decode("utf-8", "replace")[:6000])
    (site / "analysis.json").write_text(json.dumps(report, indent=2))
    zpath = OUT / f"{site.name}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in site.iterdir():
            z.write(f, f.name)
    report["zip"] = str(zpath)
    return report


def _summarise(report: dict, head: str) -> str:
    prompt = ("You are helping reverse engineer a website the user owns. From this scan data, list the page "
              "sections, likely stack, and anything that looks missing or unfinished. Be brief.\n"
              f"{json.dumps({k: report[k] for k in ('files', 'endpoints', 'libraries')})}\n\nHTML start:\n{head}")
    try:
        req = urllib.request.Request(f"{OLLAMA}/api/generate", method="POST",
                                     data=json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())["response"]
    except Exception as e:
        return f"(Ollama summary unavailable: {e}. The ZIP is still complete, Claude can analyse it.)"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            self._send(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/scan":
            return self._send(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if not body.get("confirmed"):
                return self._send(400, {"error": "You must confirm you own this site or have permission."})
            self._send(200, scan(body.get("url", "").strip()))
        except Exception as e:
            self._send(400, {"error": str(e)})

    def log_message(self, *a):
        pass


def main(port: int = 8765):
    OUT.mkdir(exist_ok=True)
    print(f"Open http://localhost:{port} in your browser (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()

"""The verify loop: prove a rebuild matches the original it was based on.

Screenshots the original and the rebuild at desktop and mobile widths, scores how close they look,
and writes a diff image plus a report Claude (or you) can act on. This is the feature that makes a
rebuild trustworthy instead of "looks about right".

Nothing here extracts a site's source, API or private data. It only compares how two pages *appear*,
which is exactly what any visitor's browser already sees.
"""
from __future__ import annotations

import contextlib
import functools
import http.server
import json
import threading
import urllib.parse
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from .safety import USER_AGENT, validate_target

VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}


@contextlib.contextmanager
def _served(path: Path):
    """Serve a built directory on a random loopback port for the duration of the block."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(path))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}/"
    finally:
        httpd.shutdown()


def _screenshot(page, url: str, out: Path) -> None:
    page.goto(url, wait_until="networkidle", timeout=45_000)
    page.wait_for_timeout(600)  # let fonts / entrance animations settle
    page.screenshot(path=str(out), full_page=True)


def similarity(a_path: Path, b_path: Path, diff_path: Path) -> float:
    """Return a 0..1 visual similarity score and write a difference image."""
    a = Image.open(a_path).convert("RGB")
    b = Image.open(b_path).convert("RGB")
    w, h = min(a.width, b.width), min(a.height, b.height)
    a, b = a.resize((w, h)), b.resize((w, h))
    diff = ImageChops.difference(a, b)
    diff.save(diff_path)
    mean_channels = ImageStat.Stat(diff).mean  # 0..255 per RGB channel
    return round(1 - (sum(mean_channels) / len(mean_channels)) / 255, 4)


def _capture_all(original_url: str, rebuild_url: str, out: Path) -> dict:
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for name, (width, height) in VIEWPORTS.items():
                ctx = browser.new_context(viewport={"width": width, "height": height}, user_agent=USER_AGENT)
                page = ctx.new_page()
                orig_png = out / f"original-{name}.png"
                rebuild_png = out / f"rebuild-{name}.png"
                _screenshot(page, original_url, orig_png)
                _screenshot(page, rebuild_url, rebuild_png)
                ctx.close()
                score = similarity(orig_png, rebuild_png, out / f"diff-{name}.png")
                results[name] = {
                    "score": score,
                    "original": orig_png.name,
                    "rebuild": rebuild_png.name,
                    "diff": f"diff-{name}.png",
                }
        finally:
            browser.close()
    return results


def verify(original_url: str, rebuild: str, out_dir: str = "verify-out") -> dict:
    """Compare a rebuild against its original.

    original_url: the public site you own that you are rebuilding.
    rebuild: a path to your built site (a folder) OR a http://localhost URL you are already serving.
    """
    validate_target(original_url)
    out = Path(out_dir)

    rebuild_path = Path(rebuild)
    report_meta = {"original": original_url, "viewports": {}}

    if rebuild_path.is_dir():
        with _served(rebuild_path) as rebuild_url:
            report_meta["rebuild"] = f"(served) {rebuild_path}"
            report_meta["viewports"] = _capture_all(original_url, rebuild_url, out)
    else:
        validate_target(rebuild, allow_loopback=True)
        report_meta["rebuild"] = rebuild
        report_meta["viewports"] = _capture_all(original_url, rebuild, out)

    scores = [v["score"] for v in report_meta["viewports"].values()]
    report_meta["overall"] = round(sum(scores) / len(scores), 4) if scores else 0.0
    report_meta["verdict"] = _verdict(report_meta["overall"])
    (out / "verify-report.json").write_text(json.dumps(report_meta, indent=2))
    _write_markdown(out, report_meta)
    return report_meta


def _verdict(score: float) -> str:
    if score >= 0.97:
        return "excellent — pixel-close match"
    if score >= 0.90:
        return "good — minor visual differences remain"
    if score >= 0.75:
        return "partial — sections still differ, keep iterating"
    return "far — the rebuild does not match yet"


def _write_markdown(out: Path, meta: dict) -> None:
    lines = [
        "# Verify report",
        "",
        f"- Original: {meta['original']}",
        f"- Rebuild: {meta['rebuild']}",
        f"- **Overall match: {meta['overall'] * 100:.1f}% — {meta['verdict']}**",
        "",
        "| Viewport | Match | Diff image |",
        "| --- | --- | --- |",
    ]
    for name, v in meta["viewports"].items():
        lines.append(f"| {name} | {v['score'] * 100:.1f}% | `{v['diff']}` |")
    lines += ["", "Open the `diff-*.png` images: bright areas are where the rebuild differs from the original."]
    (out / "VERIFY.md").write_text("\n".join(lines))

"""Preview a finished rebuild in the browser, then ask before anything is kept.

The agents build into a temporary folder. We serve that folder on localhost, open it in
the browser so the person can look at it, and only move it to the real output folder if they
say to keep it. Say no and the temporary folder is deleted - nothing is written.
"""
from __future__ import annotations

import functools
import http.server
import shutil
import sys
import threading
import webbrowser

KEEP_WORD = "SAVE"


def _serve(folder: str):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=folder)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def preview_and_ask(folder: str, *, auto_save: bool = False, stream=None) -> bool:
    """Show the rebuild and return True only if it should be saved."""
    out = stream or sys.stdout
    interactive = sys.stdin.isatty()

    # Scripted run: no browser, decision comes from the flag.
    if not interactive:
        if auto_save:
            return True
        print("Not interactive - rebuild not saved. Re-run with --save to keep it.", file=out)
        return False

    srv = _serve(folder)
    url = f"http://127.0.0.1:{srv.server_port}/"
    print(f"\nPreview is open in your browser: {url}", file=out)
    print("(this is only a local preview - nothing has been saved yet)", file=out)
    try:
        webbrowser.open(url)
    except Exception:
        print("Could not open the browser automatically - open the link above.", file=out)
    try:
        if auto_save:
            return True
        answer = input(f"\nKeep this rebuild? type {KEEP_WORD} to save it, anything else throws it away: ")
        return answer.strip().upper() == KEEP_WORD
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=out)
        return False
    finally:
        srv.shutdown()
        srv.server_close()


def commit_or_discard(staging: str, out_dir: str, keep: bool, *, stream=None) -> bool:
    """Move the staging folder to out_dir when keep is True, otherwise delete it."""
    sout = stream or sys.stdout
    if keep:
        shutil.copytree(staging, out_dir, dirs_exist_ok=True)
        shutil.rmtree(staging, ignore_errors=True)
        print(f"Saved to {out_dir}", file=sout)
        return True
    shutil.rmtree(staging, ignore_errors=True)
    print("Discarded - nothing was written to disk.", file=sout)
    return False

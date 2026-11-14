"""Command line entry: `python -m sitere <scan|verify>`."""
from __future__ import annotations

import argparse
import json
import os
import sys


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="sitere",
        description="Rebuild and modernize a website you own, then prove the rebuild matches.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="start the local collector UI (your own site's front end)")
    p_scan.add_argument("--port", type=int, default=8765)

    p_verify = sub.add_parser("verify", help="screenshot-compare your rebuild against the original")
    p_verify.add_argument("--original", required=True, help="the public site you own")
    p_verify.add_argument("--rebuild", required=True, help="folder of your built site, or a http://localhost URL")
    p_verify.add_argument("--out", default="verify-out")

    p_rebuild = sub.add_parser("rebuild", help="run the agent crew to pull down the front end of a site you own")
    p_rebuild.add_argument("url", help="the site you own (full http(s):// URL)")
    p_rebuild.add_argument("--out", default="rebuild", help="output folder (default: rebuild)")
    p_rebuild.add_argument("--agents", type=int, default=24, help="how many agents run at once (1-30, default 24)")
    p_rebuild.add_argument("--max-pages", type=int, default=40, help="most pages to crawl (default 40)")
    p_rebuild.add_argument("--max-assets", type=int, default=600, help="most assets to download (default 600)")
    p_rebuild.add_argument("--depth", type=int, default=3, help="how many links deep to crawl (default 3)")
    p_rebuild.add_argument("--i-own-this", action="store_true", help="confirm ownership without the prompt (for scripts)")
    p_rebuild.add_argument("--allow-local", action="store_true", help="allow a localhost target (your own dev server)")
    p_rebuild.add_argument("--plain", action="store_true", help="plain log instead of the live board")

    args = parser.parse_args(argv)

    if args.cmd == "scan":
        from scanner.server import main as serve
        serve(args.port)
        return 0

    if args.cmd == "rebuild":
        from .agents import Config, rebuild
        from .consent import confirm_ownership
        from .safety import Refused, validate_target
        if not confirm_ownership(args.url, preapproved=args.i_own_this):
            return 1
        try:
            validate_target(args.url, allow_loopback=args.allow_local)
        except Refused as e:
            print(f"Refused: {e}", file=sys.stderr)
            return 1
        n_agents = max(1, min(args.agents, 30))
        cfg = Config(
            out_dir=args.out, agents=n_agents, max_pages=args.max_pages,
            max_assets=args.max_assets, max_depth=args.depth,
            allow_loopback=args.allow_local,
            dashboard_mode="plain" if args.plain else "auto",
        )
        print(f"Sending {n_agents} agents to rebuild {args.url} ...")
        result = rebuild(args.url, cfg)
        where = os.path.join(args.out, "")
        print(f"\nDone: {result.summary()}")
        print(f"Front end saved to {where}  (open {os.path.join(args.out, 'index.html')})")
        print(f"Next: python -m sitere verify --original {args.url} --rebuild {args.out}")
        return 0 if result.pages else 1

    if args.cmd == "verify":
        from .verify import verify
        try:
            report = verify(args.original, args.rebuild, args.out)
        except Exception as e:  # noqa: BLE001 - surface a clean message to the user
            print(f"verify failed: {e}", file=sys.stderr)
            return 1
        print(json.dumps(report, indent=2))
        print(f"\nOverall match: {report['overall'] * 100:.1f}% — {report['verdict']}")
        print(f"See {args.out}/VERIFY.md and the diff-*.png images.")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

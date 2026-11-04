"""Command line entry: `python -m sitere <scan|verify>`."""
from __future__ import annotations

import argparse
import json
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

    args = parser.parse_args(argv)

    if args.cmd == "scan":
        from scanner.server import main as serve
        serve(args.port)
        return 0

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

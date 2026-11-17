"""The ownership gate and the use notice.

Before the rebuild engine touches a site, the person has to (1) see what this tool is for,
(2) put their own name to the run, and (3) confirm, in their own words, that the site is
theirs. None of this stops a determined misuse on its own - the same-origin and front-end
limits in the engine do the real work - but it makes the one rule impossible to miss and
ties every run to the person who started it.
"""
from __future__ import annotations

import sys

PHRASE = "I OWN THIS"

NOTICE = """\
------------------------------------------------------------
 site-re-agent  -  use notice
------------------------------------------------------------
 This tool is for rebuilding a website you OWN, or have
 written permission to rebuild. It is provided for testing
 and entertainment use only, as-is and with no warranty.

 It reads only the public front end of the one site you
 point it at. It does not reach any back end, and it will
 not crawl off that site.

 You are responsible for how you use it and for following
 the law and the terms of any website. If it is misused,
 that is on the person who ran it, not on the author.
------------------------------------------------------------"""

PROMPT = "If this site is yours, type  {phrase}  to continue (anything else cancels): "


def show_notice(stream=None) -> None:
    print(NOTICE, file=stream or sys.stdout)


def operator_name(provided: str = "", *, stream=None) -> str:
    """The name of the person running this. Stamped onto the run so it is theirs."""
    out = stream or sys.stdout
    if provided and provided.strip():
        return provided.strip()[:80]
    if not sys.stdin.isatty():
        return "unnamed operator"
    try:
        name = input("Your name (the developer running this rebuild): ").strip()
    except (EOFError, KeyboardInterrupt):
        return "unnamed operator"
    return name[:80] if name else "unnamed operator"


def confirm_ownership(url: str, *, preapproved: bool = False, stream=None) -> bool:
    """Return True only when the person has confirmed they own the target.

    preapproved covers the non-interactive flag (--i-own-this) for scripted runs.
    """
    out = stream or sys.stdout
    if preapproved:
        print(f"Ownership confirmed for {url} (--i-own-this).", file=out)
        return True
    if not sys.stdin.isatty():
        print(
            "Refusing to run without a confirmation. Re-run with --i-own-this "
            "if this is your own site.",
            file=out,
        )
        return False
    print(f"\nTarget: {url}", file=out)
    try:
        answer = input(PROMPT.format(phrase=PHRASE))
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=out)
        return False
    if answer.strip().upper() == PHRASE:
        return True
    print("Cancelled - that did not match, so nothing was downloaded.", file=out)
    return False

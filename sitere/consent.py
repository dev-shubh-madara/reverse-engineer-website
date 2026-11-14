"""The ownership gate.

Before the rebuild engine touches a site, the person has to say, in their own words,
that it's their site. This is the same idea as a pre-flight checklist: it won't stop a
determined misuse, but it makes the one rule of this tool impossible to miss.
"""
from __future__ import annotations

import sys

PHRASE = "I OWN THIS"

PROMPT = """\
site-re-agent only rebuilds a site you own or are allowed to rebuild.
It reads the public front end of:

    {url}

and writes a fresh copy of that front end to disk. It does not touch anyone
else's site, and it never copies a back end.

If this site is yours, type  {phrase}  to continue (anything else cancels): """


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
    try:
        answer = input(PROMPT.format(url=url, phrase=PHRASE))
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=out)
        return False
    if answer.strip().upper() == PHRASE:
        return True
    print("Cancelled - that did not match, so nothing was downloaded.", file=out)
    return False

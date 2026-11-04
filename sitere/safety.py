"""Guard rails shared by every mode: URL validation, private-network blocking, light redaction.

site-re-agent only ever works on a site the user owns or is authorised to rebuild. These helpers keep
the tooling from being pointed at private infrastructure and keep obvious secrets out of saved files.
"""
from __future__ import annotations

import ipaddress
import os
import re
import socket
import urllib.parse

USER_AGENT = (
    "site-re-agent/1.0 (+https://github.com/dev-shubh-madara/reverse-engineer-website; owner-authorised rebuild)"
)


class Refused(ValueError):
    """Raised when a target must not be processed."""


def allow_local() -> bool:
    return os.getenv("SITERE_ALLOW_LOCAL") == "1"


def is_public_host(host: str) -> bool:
    """True only if every resolved address is a public, routable IP."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def validate_target(url: str, *, allow_loopback: bool = False) -> urllib.parse.ParseResult:
    """Validate a URL the user wants to work on. allow_loopback is for a local rebuild preview only."""
    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise Refused("Enter a full http(s):// URL")
    if parsed.username or parsed.password:
        raise Refused("URLs with embedded credentials are not allowed")
    if allow_loopback and parsed.hostname in ("localhost", "127.0.0.1", "::1"):
        return parsed
    if not allow_local() and not is_public_host(parsed.hostname):
        raise Refused(
            "Private, local and unresolvable addresses are blocked "
            "(set SITERE_ALLOW_LOCAL=1 only for your own local dev server)"
        )
    return parsed


_SECRET_VALUES = [
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"),  # JWT
    re.compile(r"\b(sk|pk|rk)_(live|test)_[A-Za-z0-9]{10,}\b"),                     # Stripe-style
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),                                 # GitHub token
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                                           # AWS key id
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),                                     # Google key
]


def redact_text(text: str) -> str:
    """Blank out things that look like credentials before writing anything to disk."""
    for rx in _SECRET_VALUES:
        text = rx.sub("[REDACTED]", text)
    return text

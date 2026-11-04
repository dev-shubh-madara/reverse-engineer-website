# Security policy

## Scope & intended use

site-re-agent is designed to rebuild websites the operator **owns or is explicitly authorised to work on**.
It must not be used to clone third-party sites, impersonate brands, bypass authentication or paywalls, or
collect private data. Several guard rails enforce this:

- Private, loopback, link-local and unresolvable hosts are blocked by default.
- URLs with embedded credentials are rejected.
- Obvious secret patterns (tokens, keys, JWTs) are redacted before anything is written to disk.
- GitHub credentials are never requested or accepted in chat; authentication uses `gh auth login` or the
  app's connector.

## Reporting a vulnerability

If you find a way the guard rails can be bypassed, or any other security issue, please **open a private
security advisory** on the repository rather than a public issue, or contact the maintainer. Include steps
to reproduce. We aim to respond within a few days.

Please do not use a discovered weakness against anyone else's site.

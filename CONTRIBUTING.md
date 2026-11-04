# Contributing

Thanks for wanting to help — contributions make this better for everyone.

## Ground rules

site-re-agent is for rebuilding sites the user **owns or is authorised to work on**. Any change that makes
it easier to clone someone else's site, impersonate a brand, bypass auth/paywalls, or harvest private data
will be declined. Keep the guard rails in `sitere/safety.py` intact (or stronger).

## Getting set up

```bash
git clone https://github.com/dev-shubh-madara/reverse-engineer-website
cd reverse-engineer-website
pip install -r requirements-dev.txt
python -m playwright install chromium   # only needed to run the verify loop
pytest -q
```

## Good first contributions

- New stack templates for the rebuild step (Next.js, Flask, FastAPI)
- A structural diff (DOM + visible text) to sit next to the visual score
- A one-command deploy step (GitHub Pages / Vercel)
- Docs, examples, and a demo GIF

## Pull requests

1. Branch off `main`.
2. Add or update tests — they must pass offline (no network, no browser) in CI.
3. Keep changes focused and describe *why* in the PR.
4. Run `pytest -q` before you push.

By contributing you agree your work is released under the repo's MIT license.

<div align="center">

# 🛠️ site-re-agent

### Rebuild and modernize a website you own — as clean original code — and *prove* the rebuild matches.

[![CI](https://github.com/dev-shubh-madara/reverse-engineer-website/actions/workflows/ci.yml/badge.svg)](https://github.com/dev-shubh-madara/reverse-engineer-website/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
![No API key](https://img.shields.io/badge/API%20key-not%20required-success)

</div>

---

Most "AI rebuild a website" tools stop at *"looks about right"* and quietly cross the line into cloning
other people's sites. **site-re-agent** does the opposite of both: it rebuilds **a site you own** into
clean, original, modern code, and then it **measures** how close the rebuild is with a screenshot diff —
so you ship with proof, not vibes.

Claude is the engine. There's no API key, no paid service, and no closed black box.

## ✨ Why it's different

| | Typical "AI clone" tool | **site-re-agent** |
|---|---|---|
| Target | Anyone's site | **Only sites you own / are authorised for** |
| Output | Pasted minified source | **Clean original code** |
| Trust | "Looks right" | **Visual verify score + diff images** |
| Cost | API key / credits | **None — runs in your Claude chat** |
| Honesty | Vague | **Explicit "what it will not do"** |

## 🚀 Quickstart

```bash
git clone https://github.com/dev-shubh-madara/reverse-engineer-website
cd reverse-engineer-website
python start.py          # checks Ollama, installs the browser, launches the collector UI
```

Then, in your Claude chat, install the skill (see below) and say:

> **Use site-re-agent to rebuild https://my-own-site.com**

Claude runs the authorisation check, builds a blueprint, rebuilds the site, and helps you verify it.

## 🔁 The verify loop (the good part)

After Claude rebuilds your site, serve the build and run:

```bash
python -m sitere verify --original https://my-own-site.com --rebuild ./my-build
```

You get a match score and diff images at desktop **and** mobile:

```
Overall match: 96.4% — good — minor visual differences remain
See verify-out/VERIFY.md and the diff-*.png images.
```

Claude reads the report, fixes what still differs, and you run it again until it's pixel-close.

## 🧩 Three modes

1. **Rebuild my own site** — modernize your own site into fresh code.
2. **Learn from a reference** — study a public site's techniques and build *your own* original site, your content.
3. **Verify** — score any rebuild against its original.

## 📦 Install the skill

Pick whichever your Claude app supports:

- **Plugin:** add this repo as a plugin source, then install `site-re-agent`.
- **Skill upload:** zip the `skills/site-re-agent` folder and upload it in Settings → Skills.
- **Claude Code:** copy `skills/site-re-agent` into `~/.claude/skills/`.

## 🛑 What this will **not** do

- Clone a real brand's or organisation's site, or make look-alike login / payment / support pages
- Bypass logins or paywalls, scrape private or user data, or probe for vulnerabilities
- Copy anyone's logos, text, images or source
- Ask for your passwords or tokens — connect GitHub via the app connector or `gh auth login`
- Touch private or local addresses (blocked by default)

If you point it at something it shouldn't rebuild, it stops and tells you why.

## 🤝 Collaborate

This is an open project and contributors are very welcome — new stack templates, better diffing, deploy steps.

- ⭐ **Star** the repo if it's useful — it genuinely helps.
- 🧑‍💻 Open an issue or a PR (see [CONTRIBUTING](CONTRIBUTING.md)).
- ✉️ Want to build together? Open a [discussion / issue](https://github.com/dev-shubh-madara/reverse-engineer-website/issues) titled **"Collab"**, or email **shubhkumarmishra5@gmail.com**.

## 🗺️ Roadmap

- [ ] Stack templates (static, Next.js, Flask, FastAPI)
- [ ] Structural diff (DOM + content) alongside the visual score
- [ ] Optional one-command deploy (Pages / Vercel)
- [ ] Binary & APK mode (bridges to the sister `re-agent` project)

## 📄 License

[MIT](LICENSE) © dev-shubh-madara

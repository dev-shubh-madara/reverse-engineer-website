# reverse-engineer-website

I built this because I kept wanting to rebuild my own old sites with cleaner code, and every "AI website cloner" I found did two things I didn't like: it happily copied other people's sites, and it never told me whether the rebuild actually matched the original. This does neither. It rebuilds a site you own into fresh code, and then it measures how close the rebuild is with a real screenshot comparison, so you know before you ship.

No API key. It runs inside your Claude chat as a skill, plus a small local tool for the screenshot checking.

## What it does

1. You point it at a site you own.
2. It reads the public front end and writes a plan: the sections, the colours and fonts, the layout, the libraries in use, and the shape of any API the page calls.
3. It rebuilds the site as clean, original code.
4. It screenshots your rebuild and the original at desktop and mobile, scores how close they are, and saves diff images so you can see exactly what still looks off.
5. When you're happy, it pushes to your GitHub.

## Setup

```bash
git clone https://github.com/dev-shubh-madara/reverse-engineer-website
cd reverse-engineer-website
python start.py
```

`start.py` installs the dependencies, sets up the headless browser used for the screenshot check, and offers to install Ollama if you want the optional local summary. Then it opens the collector at `http://localhost:8765`.

Install the skill in Claude (pick what your app supports):

- Plugin: add this repo as a plugin source and install `site-re-agent`.
- Skill upload: zip the `skills/site-re-agent` folder and upload it in Settings, Skills.
- Claude Code: copy `skills/site-re-agent` into `~/.claude/skills/`.

Then just tell Claude: `rebuild https://my-own-site.com`.

## The verify step

This is the part I actually care about. After the rebuild, serve it locally and run:

```bash
python -m sitere verify --original https://my-own-site.com --rebuild ./my-build
```

You get something like:

```
Overall match: 96.4% - good, minor visual differences remain
See verify-out/VERIFY.md and the diff-*.png images.
```

The diff images show the exact spots that differ, so you can fix those and run it again until it's close.

## Modes

- Rebuild your own site into fresh code.
- Learn from a public site's techniques and build your own version with your own content.
- Verify any rebuild against its original.

## What it won't do

I put limits in on purpose, because a tool that rebuilds "anything" is really a cloning tool:

- No copying real brands: no look-alike login, payment or support pages.
- No bypassing logins or paywalls, no scraping private data, no poking at vulnerabilities.
- No copying anyone's logos, text, images or source.
- It never asks for your passwords or tokens. GitHub is connected through the app or `gh auth login`.
- Private and local addresses are blocked by default.

If you point it at something it shouldn't touch, it stops and says why.

## Contributing

Happy to have help. Good places to start are new stack templates, a structural diff to sit next to the visual one, and a one-command deploy. See CONTRIBUTING.md. If you want to build on this together, open an issue titled "Collab" or email me at shubhkumarmishra5@gmail.com.

## Roadmap

- Stack templates: static, Next.js, Flask, FastAPI
- Structural diff of the DOM and text alongside the visual score
- One-command deploy to Pages or Vercel
- Binary and APK mode

## License

MIT

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

## Fast mode: the agent crew

The skill reads a page carefully and rebuilds it with clean code. But when I just want the
whole front end of my own site pulled down fast - every page, every stylesheet, script, image
and font - I use the crew:

```bash
python -m sitere rebuild https://my-own-site.com --out mysite
```

It asks one thing first:

```
If this site is yours, type  I OWN THIS  to continue:
```

Type it and a pool of agents goes to work. By default 24 run at once (you can set `--agents`
up to 30). They share one job list: reading a page adds its stylesheets, scripts, images and
same-site links back into the list, so the crew fans out across the whole site until there's
nothing left. Each agent shows its own line while it works, so you can watch all of them at
once instead of one scrolling log:

```
  ⠹ agent 00  reading /pricing
  ⠹ agent 01  fetching /css/app.css
  ⠸ agent 02  fetching /img/hero.png
  ...
  rebuilt 18/40
```

When it's done you get a working offline copy in `mysite/` - open `index.html` and it looks
like the real thing, with every link pointing at the local files. Then run the verify step,
or hand the folder to the skill to turn into fresh, clean code.

A few things it does on purpose:

- **Front end only.** It downloads what the browser already receives. A site's back end lives
  on its server and never reaches the browser, so it can't be and isn't copied. There's a note
  saying exactly that in every rebuild.
- **Your site only.** It stays on the one domain you pointed it at. An off-site link or a
  third-party CDN file is left as-is, not downloaded, so you don't end up with someone else's
  assets.
- **No GPU, no key.** The agents are plain Python workers doing network and file work in
  parallel. Nothing loads a model, so it runs the same on any laptop.
- **Safe by default.** It redacts anything that looks like a key before writing a file, blocks
  private and local addresses (pass `--allow-local` for your own dev server), caps how many
  pages and how much it downloads, and skips oversized files.

Flags I use most: `--agents 30`, `--max-pages 60`, `--depth 4`, `--plain` (for a plain log
instead of the live board), `--i-own-this` (skip the prompt in a script).

## Modes

- Pull down the whole front end of your own site with the agent crew, then rebuild it.
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

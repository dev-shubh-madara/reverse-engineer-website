# site-re-agent

Turn your own Claude chat into a **website reverse engineering agent**. Give it a site you own (or are
authorised to work on), and it analyses how it is built, rebuilds it as clean original code, and pushes the
result to **your** GitHub after you connect it. No API key, no extra server: Claude is the agent.

## How it works

1. **Authorisation check first.** You confirm you own the site or have permission (or that it is only a design
   reference for your own original build).
2. **Analyse.** Claude reads the public HTML/CSS/JS and the API calls the front end makes.
3. **Rebuild.** Claude writes new, working code, with your own content for anything that is not yours.
4. **Push.** With your approval, Claude commits under your name and pushes to the repo you choose.

## Install

Pick whichever your Claude app supports:

- **Plugin:** add this repo as a plugin source, then install `site-re-agent`.
- **Skill upload:** download this repo as a ZIP, zip the `skills/site-re-agent` folder and upload it in
  Settings, Skills.
- **Claude Code:** copy `skills/site-re-agent` into `~/.claude/skills/`.

Then in a chat, say: *"Use site-re-agent to rebuild https://my-own-site.com"*

## What it will not do

- Clone a real brand's or organisation's site, or make look-alike login, payment or support pages
- Bypass logins or paywalls, scrape private data, or exploit vulnerabilities
- Copy someone else's logos, text, images or proprietary code
- Ask for your passwords or tokens: connect GitHub through the app's connector or your own `gh` login

## Roadmap

- [ ] Templates for common stacks (static, Next.js, Flask, FastAPI)
- [ ] Network-trace report generator
- [ ] Optional Pages/Vercel deploy step

## Licence

MIT

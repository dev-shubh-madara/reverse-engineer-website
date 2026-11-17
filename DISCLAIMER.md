# Disclaimer and intended use

Please read this before using `reverse-engineer-website`.

## What this tool is for

This project is for rebuilding a website **you own**, or that you have **written
permission** to rebuild, into clean code of your own. It is shared for **testing and
entertainment use**. It is a learning and convenience tool, not a service for copying
other people's work.

## What it does and does not do

- It reads only the **public front end** of the single site you point it at - the HTML,
  CSS, JavaScript, images and fonts that a normal browser already downloads when it opens
  the page.
- It **cannot and does not** copy a back end. A website's server code, database and secret
  keys never leave the server, so no tool running in a browser or on your own machine can
  reach them.
- It **stays on the one site** you give it. It does not follow links to other domains, and
  it does not download assets from third-party domains.
- It asks you to confirm you own the site (`I OWN THIS`) and to put your name to the run
  before it does anything.

## Your responsibility

You are responsible for how you use this tool. By using it you agree that:

- You will only run it on a site you own or are allowed to rebuild.
- You will follow the law and the terms of service of any website.
- You will not use it to copy, impersonate or pass off someone else's website as your own.

If someone uses this tool to do something they are not allowed to do, that is **their**
responsibility, not the author's. The author built it in good faith for legitimate use and
does not intend it to harm any website or company.

## No warranty

The software is provided "as is", without warranty of any kind, and without any guarantee
that a rebuild is accurate or complete. See the [LICENSE](LICENSE) for the full terms.

## A note on what this disclaimer is and is not

This document explains the intended use and limits of the tool. It is a good-faith notice,
not a legal guarantee: no disclaimer makes any use of any tool automatically lawful. The
real safeguards here are built into the tool itself - it works only on the site you own,
only on the front end, and only after you confirm ownership. Please keep it that way.

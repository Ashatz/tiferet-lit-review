# tiferet-lit-review
A literature review knowledge base app built with Tiferet.

## Quick Start

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -e .

python lit_review_cli.py system ping
```

The `ping` command is an end-to-end smoke test: it proves the application
skeleton loads, resolves its dependency injection container, and executes a
feature step. It prints `pong` and exits with code `0`.

## Agent-assisted capture

Once the CLI is installed, hand a PDF, book, or excerpt to an agent in this
repo and ask it to capture the reading. Project skills live in
`.agents/skills/` and cover the capture and thematic-organization loop:

- `tiferet-lit-review-ingest` — `source add`, optional `source attach` for a
  supplied local file, and `citation add` from researcher-approved passages
- `tiferet-lit-review-theme` — `theme add` / `theme link` / `theme update` /
  `theme synthesize` / `theme show` after you confirm

Abstract composition (`abstract`), Outline assembly (`outline`), and Paper
drafting (`paper`) are also implemented, but as separate, researcher-initiated
workflows — the capture and theme skills above do not assemble an Outline,
open a Paper, or create/rewrite a KB Abstract on their own.

See [AGENTS.md](AGENTS.md) for the project's layer overview and runtime flow.

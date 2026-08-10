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

See [AGENTS.md](AGENTS.md) for the project's layer overview and runtime flow.

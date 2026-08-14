---
name: tiferet-lit-review-theme
description: Create themes, link existing citations to them, and show the current synthesized description in the tiferet-lit-review knowledge base. Use this whenever the user wants to group citations by idea, start a theme, attach evidence to a theme, inspect what a theme currently says, or organize captured reading around an argument — even if they do not say "theme." Do not use this to capture a new source; that is tiferet-lit-review-ingest.
---

# Themes in tiferet-lit-review

The theme, not the source, is the unit of intellectual work. This skill
covers the implemented theme surface on `v1.x-proto` as of `v1.0.0a3`.
It does not render citations in APA or assemble an outline.

## When to use

- The user wants to group already-captured citations around an idea.
- The user asks what a theme currently says, or to attach a citation to one.
- Ingest just captured citations and the researcher is ready to confirm links.

Do not use this skill to invent bibliographic records, extract PDF text,
or decide theme membership without the researcher.

## Current CLI surface

Run from the repository root with the project venv active when `.venv` exists:

```bash
python lit_review_cli.py theme <command> [flags]
```

| Command | Flags | What it does |
|---|---|---|
| `theme add` | `-n` / `--name` (required) | Create a theme. `id` is a slug of the name, or a UUID if that slug already exists. Synthesis starts empty. |
| `theme list` | none | List themes (name, id, linkage_count, current description). |
| `theme link` | `-c` / `--citation-id`, `-t` / `--theme-id` | Attach a citation. New links re-synthesize from the **full** linkage set. Re-linking the same pair is idempotent (no second row, no re-synth). |
| `theme show` | `-i` / `--id` | Print the synthesized description plus each linked citation's raw excerpt (not APA). |

Errors you may see:

- `THEME_NOT_FOUND` — bad theme id
- `CITATION_NOT_FOUND` — bad citation id

There is no `theme unlink` or `theme update` at v1. Do not invent them.

## How synthesis works today

`LinkCitationToTheme` reloads every citation already linked to the theme,
then calls the injected `ThemeSynthesisService`. The shipped implementation
(`NaiveThemeSynthesizer`) concatenates up to 10 lines of
`Author (Year): excerpt`, most-recently-linked first.

Treat that string as a working collage, not finished scholarly prose. The
seam is what matters: a later synthesizer can replace it via `di.yml`
without changing these commands.

## Procedure

### 1. Know what you are linking

You need a real `citation_id` (UUID from `citation add` / `citation list`).
If the citation does not exist yet, stop and use `tiferet-lit-review-ingest`.

```bash
python lit_review_cli.py citation list -s SOURCE_ID
```

### 2. Find or create the theme

```bash
python lit_review_cli.py theme list
```

Prefer an existing theme whose name already matches the idea. Only create
a new theme when the researcher agrees the idea is not already represented:

```bash
python lit_review_cli.py theme add -n "Situated expertise"
```

Save the returned `id` (often a slug such as `situated-expertise`).

A citation may belong to more than one theme. That is expected — one passage
can support more than one strand of the argument. Confirm each link separately.

### 3. Confirm, then link

Propose the mapping in plain language first:

> Link citation `<short excerpt…>` to theme `<name>` (`<id>`)?

Only after yes:

```bash
python lit_review_cli.py theme link \
  -c CITATION_ID \
  -t THEME_ID
```

Then show the result:

```bash
python lit_review_cli.py theme show -i THEME_ID
```

If the researcher declines, do not link. Suggest a different existing theme
or a new name rather than forcing a fit.

### 4. Inspect, do not silently rewrite

`theme show` is the way to review. Do not try to edit
`synthesized_description` by hand — at v1 it only changes when a **new**
linkage is formed. Adding another confirmed citation is how the collage
grows.

## Not available yet

- `citation render` / style-correct in-text and reference forms (RFP-4)
- `outline assemble` / arranging themes into a paper skeleton (RFP-5)
- Unlinking or re-scoping a linkage

## Worked example

Two citations from different sources should land on the same theme (the
point of this domain):

```bash
python lit_review_cli.py theme add -n "Expertise is enacted"

# id -> expertise-is-enacted

python lit_review_cli.py theme link \
  -c 9aa10000-aaaa-bbbb-cccc-ddddeeeeffff \
  -t expertise-is-enacted

python lit_review_cli.py theme link \
  -c 8bb20000-aaaa-bbbb-cccc-ddddeeeeffff \
  -t expertise-is-enacted

python lit_review_cli.py theme show -i expertise-is-enacted
```

The show output should include both excerpts. Re-running the first `theme link`
must not increase `linkage_count`.

## Quality checklist

- `theme list` was consulted before creating a near-duplicate theme.
- Every `theme link` waited on researcher confirmation.
- Citation ids came from the store, not invented.
- One citation may be offered to multiple themes; each offer was confirmed.
- `theme show` was used after linking so the researcher sees the collage.
- No unlink, render, or outline command was invented.

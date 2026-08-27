---
name: tiferet-lit-review-theme
description: Create themes, link existing citations to them, write or re-synthesize a theme description, and show what a theme currently says in the tiferet-lit-review knowledge base. Use this whenever the user wants to group citations by idea, start a theme, attach evidence to a theme, curate the theme narrative, inspect what a theme currently says, or organize captured reading around an argument — even if they do not say "theme." Do not use this to capture a new source; that is tiferet-lit-review-ingest.
---

# Themes in tiferet-lit-review

The theme, not the source, is the unit of intellectual work. This skill
covers the implemented theme surface on `v1.x-proto` as of `v1.0.0a13`.
Outline assembly and Paper composition are implemented elsewhere in the app
(see § Boundary with later workflows); this skill organizes already-captured
evidence into themes and does not assemble an Outline or open/draft a Paper
itself.

## When to use

- The user wants to group already-captured citations around an idea.
- The user asks what a theme currently says, or to attach a citation to one.
- The user wants to write or replace a theme's narrative by hand.
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
| `theme list` | none | List themes (name, id, linkage_count, retired_linkage_count, current description). |
| `theme link` | `-c` / `--citation-id`, `-t` / `--theme-id`, optional `-s` / `--include-synthesis` | Attach a citation. Default is structural only: new linkage + `linkage_count`, description unchanged. `-s` also re-synthesizes from the **active** linkage set. Re-linking the same pair is idempotent (no second row, no count change), but `-s` on an existing pair still re-synthesizes from the current active set. |
| `theme update` | positional `id`, optional `-n` / `--name`, `-d` / `--description` | Editorial write. `-d` sets `synthesized_description` to the exact text, including with zero citations. |
| `theme synthesize` | positional `id` | Reload the theme's active linkages and run the injected synthesizer. |
| `theme retire` | `-c` / `--citation-id`, `-t` / `--theme-id`, optional `-r` / `--reason` | Retire a linkage: excluded from synthesis and the default show view, but never deleted. Idempotent (re-retiring does not restamp). |
| `theme reinstate` | `-c` / `--citation-id`, `-t` / `--theme-id` | Return a retired linkage to active. Idempotent on an already-active linkage. |
| `theme show` | positional `id`, optional `--include-retired` | Print the description plus each **active** linked citation's raw excerpt (not APA). `--include-retired` additionally lists retired linkages with their retirement timestamp and reason. |

Errors you may see:

- `THEME_NOT_FOUND` — bad theme id
- `CITATION_NOT_FOUND` — bad citation id
- `LINKAGE_NOT_FOUND` — no linkage exists between the named citation and theme (`theme retire` / `theme reinstate`)

There is no hard-delete `theme unlink` at v1 — `theme retire` is the
unlinking mechanism, and it is reversible via `theme reinstate`. Retirement
is always a researcher-confirmed act; never infer it from context.

## How synthesis works today

Linking is a cheap structural fact. It does **not** rewrite
`synthesized_description` unless the researcher opts in with
`--include-synthesis`.

`theme synthesize` (and opt-in link) reloads every **active** citation
linked to the theme, then calls the injected `ThemeSynthesisService`. A
retired linkage's excerpt never reaches the synthesizer. The shipped
implementation (`NaiveThemeSynthesizer`) concatenates up to 10 lines of
`Author (Year): excerpt`, most-recently-linked first.

Treat that string as a working collage, not finished scholarly prose. Prefer
`theme update -d` for a curated narrative. The seam is what matters: a later
synthesizer can replace the naive impl via `di.yml` without changing these
commands.

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

Default link leaves any curated description intact. Add `-s` /
`--include-synthesis` only when the researcher wants the naive collage
rewritten as part of the link.

Then show the result:

```bash
python lit_review_cli.py theme show THEME_ID
```

If the researcher declines, do not link. Suggest a different existing theme
or a new name rather than forcing a fit.

### 4. Write or re-synthesize the description

To set exact editorial text (zero citations required):

```bash
python lit_review_cli.py theme update THEME_ID \
  -d "The curated narrative the researcher approved."
```

To rebuild the naive collage from the current linkage set:

```bash
python lit_review_cli.py theme synthesize THEME_ID
```

Do not run `theme synthesize` or `--include-synthesis` after a curated
`theme update` unless the researcher asks to replace that text.

## Boundary with later workflows

`outline` and `paper` are implemented CLI groups, but out of this skill's
scope:

- This skill organizes citations into themes. It does not assemble an
  Outline slot, open a Paper, or draft prose.
- If the researcher wants to arrange themes into a paper skeleton, point
  them at the `outline` CLI group directly; that is a separate,
  researcher-initiated decision.

Still not available at v1:

- Hard deletion of a linkage (retirement is reversible state, not erasure)
- Typed supersession (recording that citation X displaced citation Y)
- Retirement of an `AbstractTheme` join (a known, deliberately deferred gap)

`citation render` is implemented. Use it when the user asks for APA; it is
not required to create or link a theme.

## Worked example

Two citations from different sources should land on the same theme (the
point of this domain). Write the narrative first so batch linking cannot
clobber it:

```bash
python lit_review_cli.py theme add -n "Expertise is enacted"

# id -> expertise-is-enacted

python lit_review_cli.py theme update expertise-is-enacted \
  -d "Expertise is enacted in review, not stored in the reviewer."

python lit_review_cli.py theme link \
  -c 9aa10000-aaaa-bbbb-cccc-ddddeeeeffff \
  -t expertise-is-enacted

python lit_review_cli.py theme link \
  -c 8bb20000-aaaa-bbbb-cccc-ddddeeeeffff \
  -t expertise-is-enacted

python lit_review_cli.py theme show expertise-is-enacted
```

The show output should include both excerpts and the curated description.
Re-running the first `theme link` must not increase `linkage_count`.

## Quality checklist

- `theme list` was consulted before creating a near-duplicate theme.
- Every `theme link` waited on researcher confirmation.
- Citation ids came from the store, not invented.
- One citation may be offered to multiple themes; each offer was confirmed.
- Default `theme link` was used unless the researcher asked to synthesize.
- Curated text went through `theme update -d`, not a silent synthesizer run.
- `theme show` was used after linking so the researcher sees the result.
- A linkage was retired only on explicit researcher confirmation, never
  inferred from context (e.g. "this source seems outdated").
- `theme retire` was used instead of inventing a hard-delete unlink, and no
  Outline/Paper composition was performed from this skill.

---
name: tiferet-lit-review-theme
description: Create themes, link existing citations to them, write or re-synthesize a theme description, record a researcher-confirmed relevancy weight on one mapping, and show what a theme currently says in the tiferet-lit-review knowledge base. Use this whenever the user wants to group citations by idea, start a theme, attach evidence to a theme, curate the theme narrative, judge thematic novelty of a linkage, inspect what a theme currently says, or organize captured reading around an argument — even if they do not say "theme." Do not use this to capture a new source; that is tiferet-lit-review-ingest. Do not write a weight until the researcher agrees, and do not synthesize, retire, hide, or filter because a weight was set.
---

# Themes in tiferet-lit-review

The theme, not the source, is the unit of intellectual work. This skill
covers the implemented theme surface on `v1.x-proto`, including an optional
relevancy weight on each citation–theme linkage.
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

Run from the repository root with the project venv active when `.venv` exists.
Every store command takes a leading positional `project_id`:

```bash
python lit_review_cli.py theme <command> PROJECT_ID [flags]
```

Resolve the store first if you do not already hold `PROJECT_ID`:

```bash
python lit_review_cli.py project list
python lit_review_cli.py project show PROJECT_ID
```

Do not run `project add` unless the researcher explicitly asks to create a
project. There is no `project update`, no theme copy/move, and no theme
delete. `theme retire` remains the unlinking mechanism.

| Command | Flags | What it does |
|---|---|---|
| `theme add` | positional `project_id`, `-n` / `--name` (required) | Create a theme. `id` is a slug of the name, or a UUID if that slug already exists. Synthesis starts empty. |
| `theme list` | positional `project_id` | List themes (name, id, linkage_count, retired_linkage_count, current description). |
| `theme link` | positional `project_id`, `-c` / `--citation-id`, `-t` / `--theme-id`, optional `-s` / `--include-synthesis` | Attach a citation. Default is structural only: new linkage + `linkage_count`, description unchanged. `-s` also re-synthesizes from the **active** linkage set. Re-linking the same pair is idempotent (no second row, no count change), but `-s` on an existing pair still re-synthesizes from the current active set. |
| `theme update` | positional `project_id`, positional `id`, optional `-n` / `--name`, `-d` / `--description` | Editorial write. `-d` sets `synthesized_description` to the exact text, including with zero citations. |
| `theme synthesize` | positional `project_id`, positional `id` | Reload the theme's active linkages and run the injected synthesizer. |
| `theme retire` | positional `project_id`, `-c` / `--citation-id`, `-t` / `--theme-id`, optional `-r` / `--reason` | Retire a linkage: excluded from synthesis and the default show view, but never deleted. Idempotent (re-retiring does not restamp). |
| `theme reinstate` | positional `project_id`, `-c` / `--citation-id`, `-t` / `--theme-id` | Return a retired linkage to active. Idempotent on an already-active linkage. |
| `theme show` | positional `project_id`, positional `id`, optional `--include-retired` | Print the description plus each **active** linked citation's raw excerpt (not APA) and that mapping's relevancy weight. Absent prints as null, never `0`. Order stays linkage order. `--include-retired` additionally lists retired linkages with their retirement timestamp, reason, and weight. |
| `theme weight` | positional `project_id`, `-c` / `--citation-id`, `-t` / `--theme-id`, `-w` / `--weight` | Set a researcher-confirmed relevancy weight, integer 1–100, on an existing linkage. Does not create a linkage, retire it, or synthesize. |
| `theme clear-weight` | positional `project_id`, `-c` / `--citation-id`, `-t` / `--theme-id` | Clear the weight, returning the mapping to unjudged. Does not create a linkage. |

Errors you may see:

- `THEME_NOT_FOUND` — bad theme id
- `CITATION_NOT_FOUND` — bad citation id
- `LINKAGE_NOT_FOUND` — no linkage exists between the named citation and theme (`theme retire`, `theme reinstate`, `theme weight`, `theme clear-weight`)
- `RELEVANCY_WEIGHT_OUT_OF_RANGE` — weight is not an integer from 1 to 100
- `CITATION_LINK_ORIGIN_NOT_FOUND` — a linked `type=link` citation's origin project or default citation is missing at resolve time

There is no hard-delete `theme unlink` at v1 — `theme retire` is the
unlinking mechanism, and it is reversible via `theme reinstate`. Retirement
is always a researcher-confirmed act; never infer it from context.

Cross-project `source copy|move` and `citation copy|move` are shipped on the
ingest surface. They do **not** transfer themes or linkages. A copied or moved
citation arrives unlinked. Citation move deletes the origin row and does not
retire linkages — linkage rows stay behind, and `theme show` currently drops a
missing citation. Do not recommend moving a citation that still has linkages;
prefer retire-in-place, or copy when the origin linkages should remain coherent.
There is no theme copy or move and no bulk transfer.

## How synthesis works today

Linking is a cheap structural fact. It does **not** rewrite
`synthesized_description` unless the researcher opts in with
`--include-synthesis`.

`theme synthesize` (and opt-in link) reloads every **active** citation
linked to the theme, then calls the injected `ThemeSynthesisService`. A
retired linkage's excerpt never reaches the synthesizer. The shipped
implementation (`NaiveThemeSynthesizer`) concatenates up to 10 lines of
`Author (Year): excerpt`, most-recently-linked first.

A `type=link` citation is a live pointer, not a second excerpt and not a
citation–theme Linkage. Synthesis and `theme show` use the origin excerpt and
the **local** context_note; origin context_note is not substituted. Missing
origin fails visibly (`CITATION_LINK_ORIGIN_NOT_FOUND`) and must not quote the
pointer string as a quotation.

Treat that string as a working collage, not finished scholarly prose. Prefer
`theme update -d` for a curated narrative. The seam is what matters: a later
synthesizer can replace the naive impl via `di.yml` without changing these
commands.

## Procedure

### 0. Resolve the project store

Hold a real `PROJECT_ID` before any theme or citation command:

```bash
python lit_review_cli.py project list
python lit_review_cli.py project show PROJECT_ID
```

If the researcher already named the project, use that id. Do not create a
project unless they ask.

### 1. Know what you are linking

You need a real `citation_id` (UUID from `citation add` / `citation list`).
If the citation does not exist yet, stop and use `tiferet-lit-review-ingest`.

```bash
python lit_review_cli.py citation list PROJECT_ID -s SOURCE_ID
```

### 2. Assess the citation, then find or create the theme

Whenever a citation is newly captured or brought up for review, assess it
against the themes already in the store before proposing a link.

```bash
python lit_review_cli.py theme list PROJECT_ID
```

Read the excerpt and context note, not the title alone. Compare them with
existing theme descriptions.

- Recommend an existing theme when the passage would add to that theme's
  claim. With the recommendation, give a 1–100 thematic-novelty weight for
  that proposed mapping and one or two sentences of method. 100 means the
  theme would be thinner without the passage. 50 means it mostly restates a
  claim the theme already holds. 1–20 means it does not belong there.
- The same citation may fit more than one theme, at different weights.
  Confirm each mapping separately.
- If the best existing theme is still a weak fit, do not force the link.
  Name a possible new theme that would hold the passage more closely.
  Create it only after the researcher agrees the idea is not already represented.

Prefer an existing theme whose claim the passage actually develops. Only create
a new theme when the researcher agrees the idea is not already represented:

```bash
python lit_review_cli.py theme add PROJECT_ID -n "Situated expertise"
```

Save the returned `id` (often a slug such as `situated-expertise`).

A citation may belong to more than one theme. That is expected — one passage
can support more than one strand of the argument. Confirm each link separately.

### 3. Confirm, then link

Propose the mapping in plain language first:

> Link citation `<short excerpt…>` to theme `<name>` (`<id>`)?

Only after yes:

```bash
python lit_review_cli.py theme link PROJECT_ID \
  -c CITATION_ID \
  -t THEME_ID
```

Default link leaves any curated description intact. Add `-s` /
`--include-synthesis` only when the researcher wants the naive collage
rewritten as part of the link.

Then show the result:

```bash
python lit_review_cli.py theme show PROJECT_ID THEME_ID
```

If the researcher declines, do not link. Suggest a different existing theme
or a new name rather than forcing a fit.

### 4. Write or re-synthesize the description

To set exact editorial text (zero citations required):

```bash
python lit_review_cli.py theme update PROJECT_ID THEME_ID \
  -d "The curated narrative the researcher approved."
```

To rebuild the naive collage from the current linkage set:

```bash
python lit_review_cli.py theme synthesize PROJECT_ID THEME_ID
```

Do not run `theme synthesize` or `--include-synthesis` after a curated
`theme update` unless the researcher asks to replace that text.

### 5. Retire a linkage (when asked)

Unlinking is retirement, not hard delete. Only on explicit confirmation:

```bash
python lit_review_cli.py theme retire PROJECT_ID \
  -c CITATION_ID \
  -t THEME_ID \
  -r "Optional researcher reason"
```

Reinstate the same way if they change their mind:

```bash
python lit_review_cli.py theme reinstate PROJECT_ID \
  -c CITATION_ID \
  -t THEME_ID
```

### 6. Recommend a relevancy weight only after agreement

The weight is a researcher-confirmed judgment of thematic novelty on one
mapping, integer 1–100, not an automatic score. It lives on that linkage, not
on the citation and not on the theme. Absent is valid and is not a low score.

The operating agent may recommend a weight and must explain the method. It
must not write the weight until the researcher agrees. Do not synthesize
because a weight was set. Do not retire, hide, or filter a linkage because its
weight is low. There is no base-score filter yet.

Only after yes:

```bash
python lit_review_cli.py theme weight PROJECT_ID \
  -c CITATION_ID \
  -t THEME_ID \
  -w 70
```

To return the mapping to unjudged, again only after agreement:

```bash
python lit_review_cli.py theme clear-weight PROJECT_ID \
  -c CITATION_ID \
  -t THEME_ID
```

`theme link` has no weight flag. A new linkage is born unweighted. A missing
pair is `LINKAGE_NOT_FOUND`; do not create one to hold a weight.

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
- Theme copy, theme move, or theme delete
- Typed supersession (recording that citation X displaced citation Y)
- Retirement of an `AbstractTheme` join (a known, deliberately deferred gap)
- A base-score filter, hide-below flag, or automatic retirement because a
  weight is low. The weight is stored so that filter can be added later.

`citation render PROJECT_ID <id> -s apa` is implemented. Use it when the user
asks for APA; it is not required to create or link a theme.

## Worked example

Two citations from different sources should land on the same theme (the
point of this domain). Write the narrative first so batch linking cannot
clobber it. Project id is `design-review`:

```bash
python lit_review_cli.py project list
python lit_review_cli.py theme add design-review -n "Expertise is enacted"

# id -> expertise-is-enacted

python lit_review_cli.py theme update design-review expertise-is-enacted \
  -d "Expertise is enacted in review, not stored in the reviewer."

python lit_review_cli.py theme link design-review \
  -c 9aa10000-aaaa-bbbb-cccc-ddddeeeeffff \
  -t expertise-is-enacted

python lit_review_cli.py theme link design-review \
  -c 8bb20000-aaaa-bbbb-cccc-ddddeeeeffff \
  -t expertise-is-enacted

python lit_review_cli.py theme show design-review expertise-is-enacted
```

The show output should include both excerpts and the curated description.
Re-running the first `theme link` must not increase `linkage_count`.

## Quality checklist

- `PROJECT_ID` was resolved before any store command.
- A citation brought up for review was compared with existing theme
  descriptions before a link or a new theme was proposed.
- A weak fit was not forced onto an existing theme. A possible new theme was
  named and left uncreated until the researcher agreed.
- `theme list` was consulted before creating a near-duplicate theme.
- Every `theme link` waited on researcher confirmation.
- A recommended weight named the mapping, the integer, and why. It was not
  written before the linkage existed.
- Citation ids came from the store, not invented.
- One citation may be offered to multiple themes; each offer was confirmed.
- Default `theme link` was used unless the researcher asked to synthesize.
- Curated text went through `theme update -d`, not a silent synthesizer run.
- `theme show` was used after linking so the researcher sees the result.
- A linkage was retired only on explicit researcher confirmation, never
  inferred from context (e.g. "this source seems outdated").
- `theme retire` was used instead of inventing a hard-delete unlink, and no
  Outline/Paper composition was performed from this skill.
- No theme copy/move/delete was invented; a linked citation was not moved
  across projects while origin linkages remained.
- A relevancy weight, if written, was a researcher-confirmed 1–100 judgment
  of thematic novelty on one mapping, with the method explained first. Absent
  was left absent. No synthesis, retirement, hiding, or filtering followed
  from the weight.

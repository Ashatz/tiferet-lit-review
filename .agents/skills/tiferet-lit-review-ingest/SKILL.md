---
name: tiferet-lit-review-ingest
description: Capture a source and its citations into the tiferet-lit-review knowledge base from a PDF, book, excerpt, or bibliographic detail the user hands over. Use this whenever the user wants material added, captured, logged, ingested, or filed into the lit-review system — even if they do not say "skill" or "ingest." Also use it when they attach a PDF or quote a passage and ask you to put it in the knowledge base.
---

# Ingest into tiferet-lit-review

Teach an agent how to turn supplied reading material into live CLI calls.
This skill covers only what is implemented on `v1.x-proto` as of `v1.0.0a3`:
`source`, `citation`, and `theme`. It does not extract text itself, write
the paper, render APA, or assemble an outline.

## When to use

- The user attaches or points at a PDF, book, excerpt, or bibliographic record
  and asks for it to be added, captured, logged, or ingested.
- The user pastes a passage and wants it stored as evidence, not just discussed.
- The user is starting a preliminary literature-review collection and wants
  sources and citations in the knowledge base.

Do not use this skill to implement framework code, draft a paper, invent
bibliographic fields, or call commands that do not exist yet
(`citation render`, `outline assemble`).

## Current CLI surface (do not invent flags)

Run every command from the repository root, with the project venv active
(`source .venv/bin/activate` when `.venv` exists). Entrypoint:

```bash
python lit_review_cli.py <group> <command> [flags]
```

Implemented groups:

- `source add|list|update`
- `citation add|list|update`
- `theme add|list|link|show`

### `source add`

| Flag | Required | Notes |
|---|---|---|
| `-m` / `--medium` | yes | `pdf` or `book` only |
| `-a` / `--authors` | yes | Space-separated list; at least one. Quote any name that contains spaces. |
| `-y` / `--year` | yes | Integer publication year |
| `-t` / `--title` | yes | Work title |
| `--container-title` | no | Journal or collection title |
| `--publisher` | no | Publisher |

`locator_convention` is derived from medium (`page_range` for both `pdf` and
`book`). Do not pass it.

### `citation add`

| Flag | Required | Notes |
|---|---|---|
| `-s` / `--source-id` | yes | UUID returned by `source add` |
| `-l` / `--locator` | yes | Must match `^\d+-\d+$` (e.g. `12-14` or `12-12` for a single page) |
| `-e` / `--excerpt` | yes | Quoted or paraphrased passage |
| `--context-note` | no | Enough surrounding context to stand alone later |

A locator like `12`, `p. 12`, or `12–14` (en-dash) is invalid.

### Related read/update commands

- `source list` — confirm the source landed; capture its `id` if you lost it.
- `source update -i/--id` plus any of `-a`, `-y`, `-t`, `--container-title`,
  `--publisher`. Medium cannot be changed this way.
- `citation list -s/--source-id` — required filter; returns that source only.
- `citation update -i/--id` plus any of `-l`, `-e`, `--context-note`.

Theme commands live in `tiferet-lit-review-theme`. After capture, offer
linking; do not apply a theme without confirmation.

## Procedure

### 1. Read the material

Use your own file-reading tools (PDF-capable read, pasted text, user notes).
This codebase does not extract or OCR anything. If you cannot read the file,
say so and ask for the bibliographic fields and the passages the researcher
cares about.

### 2. Identify the source record

From title page, front matter, running headers, or an explicit citation, collect:

- `medium`: `pdf` if the artifact is a PDF/digital article file; `book` if it
  is a monograph/book. If neither fits, stop — do not invent a third medium.
- `authors`, `year`, `title`
- `container_title` and `publisher` when they are actually present

If a required field is missing or ambiguous, ask. Do not guess a year, invent
an author, or "fix" a title.

Before adding, run `source list` and reuse an existing source when the same
work is already captured (same authors + year + title). Do not create a
duplicate.

### 3. Capture the source

```bash
python lit_review_cli.py source add \
  -m pdf \
  -a "Last, F." \
  -y 2020 \
  -t "Exact title from the material" \
  --container-title "Journal Name" \
  --publisher "Publisher"
```

Save the returned `id`. Later citations need it. If the command prints a
structured object, take `id` from that object — do not invent a slug.

### 4. Identify candidate citations

Capture only passages the researcher pointed at, highlighted, or approved.
Do not bulk-ingest an entire PDF uninvited. If they said "add this paper"
without naming passages, propose a short list of candidate excerpts and wait.

For each approved passage, record:

- locator as `start-end` digits (`142-144`, or `88-88` for one page)
- excerpt text (quote when they quoted; paraphrase only if they asked)
- optional `context_note` when the excerpt is unclear out of context

### 5. Capture citations

```bash
python lit_review_cli.py citation add \
  -s SOURCE_ID \
  -l 142-144 \
  -e "The excerpt exactly as approved." \
  --context-note "Why this passage matters, if needed."
```

Save each returned citation `id`. Verify with:

```bash
python lit_review_cli.py citation list -s SOURCE_ID
```

If `SOURCE_NOT_FOUND` or `INVALID_LOCATOR` is raised, fix the input and retry.
Do not invent a different locator shape to "make it work."

### 6. Offer thematic linking

Thematic linking is available (`theme add`, `theme link`, `theme show`).
Follow `tiferet-lit-review-theme`:

1. `theme list` first.
2. Suggest existing theme names, or a new theme name, from the excerpts.
3. Run `theme link` only after the researcher confirms citation → theme.
4. `theme show -i THEME_ID` after a successful link so they can see the
   current (naive, concatenated) synthesis.

Never assign themes silently. Synthesis at v1 concatenates
`Author (Year): excerpt` lines; it is a placeholder, not finished prose.

## Not available yet

Do not call or invent:

- `citation render` / APA formatting (RFP-4)
- `outline assemble` / `outline show` (RFP-5)

Ingestion populates the knowledge base. Assembling a paper outline is a
separate, researcher-initiated decision.

## Worked example

Supplied: a journal-article PDF whose title page shows
*Smith, J. (2020). Situated expertise in design review. Design Studies.*
The researcher points at page 12: "Expertise is enacted in the review, not
stored in the reviewer."

```bash
python lit_review_cli.py source add \
  -m pdf \
  -a "Smith, J." \
  -y 2020 \
  -t "Situated expertise in design review" \
  --container-title "Design Studies"

# Suppose the command returns id=2f1c0a8e-1111-2222-3333-444444444444

python lit_review_cli.py citation add \
  -s 2f1c0a8e-1111-2222-3333-444444444444 \
  -l 12-12 \
  -e "Expertise is enacted in the review, not stored in the reviewer."

# Suppose the citation id is 9aa10000-aaaa-bbbb-cccc-ddddeeeeffff

python lit_review_cli.py theme list
# Researcher confirms an existing theme id "situated-expertise" (or asks to create it)

python lit_review_cli.py theme link \
  -c 9aa10000-aaaa-bbbb-cccc-ddddeeeeffff \
  -t situated-expertise

python lit_review_cli.py theme show -i situated-expertise
```

If the year had been missing from the title page, stop after reading and ask
before any `source add`.

## Quality checklist

- Bibliographic fields came from the material or the researcher, never invented.
- Medium is `pdf` or `book`.
- Locator is `digits-digits` and matches the page(s) of the excerpt.
- Every citation has an approved passage (not an unsolicited full-document dump).
- Existing sources were reused when the same work was already in the store.
- No theme link ran without confirmation.
- No `citation render` or `outline` command was attempted.
- Returned `id`s were captured from CLI output, not guessed.

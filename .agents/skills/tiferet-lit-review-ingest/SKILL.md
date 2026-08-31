---
name: tiferet-lit-review-ingest
description: Capture a source and its citations into the tiferet-lit-review knowledge base from a PDF, book, web text, excerpt, or bibliographic detail the user hands over. Use this whenever the user wants material added, captured, logged, ingested, or filed into the lit-review system — even if they do not say "skill" or "ingest." Also use it when they attach a PDF or quote a passage and ask you to put it in the knowledge base.
---

# Ingest into tiferet-lit-review

Teach an agent how to turn supplied reading material into live CLI calls.
This skill covers source, citation, and theme capture — including source
document attachment/download — as implemented on `v1.x-proto` through
RFP-13 (Activity Log). It does not extract text itself. Abstract composition,
Outline assembly, and Paper drafting are implemented elsewhere in the app,
but are separate, researcher-initiated workflows outside this skill's scope
(see § Boundary with later workflows).

## When to use

- The user attaches or points at a PDF, book, web text, excerpt, or bibliographic record
  and asks for it to be added, captured, logged, or ingested.
- The user pastes a passage and wants it stored as evidence, not just discussed.
- The user is starting a preliminary literature-review collection and wants
  sources and citations in the knowledge base.

Do not use this skill to implement framework code, draft a paper, invent
bibliographic fields, or call Abstract/Outline/Paper commands (`abstract add`,
`outline assemble`, `paper open`) — those exist, but belong to separate
composition workflows, not capture.

## Current CLI surface (do not invent flags)

Run every command from the repository root, with the project venv active
(`source .venv/bin/activate` when `.venv` exists). Entrypoint:

```bash
python lit_review_cli.py <group> <command> [flags]
```

Implemented groups this skill uses:

- `source add|list|update|attach|download`
- `citation add|list|update|render`
- `theme add|list|link|update|synthesize|show`

Also implemented on `v1.x-proto`, but out of this skill's scope (see
§ Boundary with later workflows): `abstract`, `outline`, `paper`.
`activity list` also exists as a read-only history view; every successful
`source`, `citation`, and `theme` write this skill makes below records its
own activity entry automatically and best-effort — this skill never calls
`activity list`, and there is no `activity add` command to invent.

### `source add`

| Flag | Required | Notes |
|---|---|---|
| `-m` / `--medium` | yes | `pdf`, `book`, `web`, or `presentation` |
| `-a` / `--authors` | yes | Space-separated list; at least one. Quote any name that contains spaces. |
| `-y` / `--year` | yes | Integer publication year |
| `-t` / `--title` | yes | Work title |
| `--container-title` | no | Journal or collection title |
| `--publisher` | no | Publisher |
| `--url` | no | Optional HTTP(S) URL for the source or online edition |
| `--overview-note` | no | Optional researcher note about the work as a whole; only set it if the researcher supplies or approves one |

`locator_convention` is derived from medium (`page_range` for `pdf` and
`book`; a non-blank textual locator for `web`; `slide_range` for
`presentation`). Do not pass it. A URL is provenance/access metadata only: do
not fetch, verify, scrape, or attach content from it. An overview note is a
document-level judgment about the whole work — never a substitute for a
citation's own `--context-note`.

### `source attach`

Use after a successful `source add`, only when the researcher supplied a
readable local file (the same file you read in step 1).

| Flag | Required | Notes |
|---|---|---|
| `id` (positional) | yes | The source identifier returned by `source add` |
| `-f` / `--file` | yes | Path to the readable local file supplied by the researcher |
| `-n` / `--name` | no | Optional API/download name override; omit unless the researcher requests one |

### `source download`

Retrieval, not a new capture step. Use only if the researcher asks to pull
the attached file back out.

| Flag | Required | Notes |
|---|---|---|
| `id` (positional) | yes | The source identifier whose document to download |
| `-o` / `--out` | no | Destination directory; defaults to the current working directory |

### `citation add`

| Flag | Required | Notes |
|---|---|---|
| `-s` / `--source-id` | yes | UUID returned by `source add` |
| `-l` / `--locator` | yes | Must match `^\d+-\d+$` (e.g. `12-14` or `12-12` for a single page) |
| `-e` / `--excerpt` | yes | Quoted or paraphrased passage |
| `--context-note` | no | Enough surrounding context to stand alone later |
| `-n` / `--title` | no | A short, researcher-authored label for *this citation* — not the source's title. Only set it if the researcher supplies or approves one; do not invent one from the excerpt. |

A locator like `12`, `p. 12`, or `12–14` (en-dash) is invalid.

### Related read/update commands

- `source list` — confirm the source landed; capture its `id` if you lost it.
- `source update <id>` plus any of `-a`, `-y`, `-t`, `--container-title`,
  `--publisher`, `--url`, or `--overview-note`; use `--clear-url` or
  `--clear-overview-note` to remove either. Medium cannot be changed this way.
- `source attach <id> -f PATH [-n NAME]` — attach a supplied local file to
  its source (see step 4). `source download <id> [-o DIR]` retrieves it later.
- `citation list -s/--source-id` — required filter; returns that source only.
- `citation update <id>` plus any of `-l`, `-e`, `--context-note`, `-n`/`--title`,
  or `--clear-title` (clears an existing title without touching other fields).

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
  is a monograph/book; `web` for a web-native page, online text, or browser-
  accessible textbook; `presentation` for a slide deck. Do not use `web`
  solely because a book also has an online edition; retain `book` and record
  its optional URL instead.
- `authors`, `year`, `title`
- `container_title` and `publisher` when they are actually present
- `url` when the researcher supplies or approves a specific HTTP(S) access
  location. Record it exactly; do not resolve, verify, scrape, or infer it.
- `overview_note` only if the researcher gives a note about the work as a
  whole — never infer one from the material yourself.

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
  --publisher "Publisher" \
  --url "https://publisher.example/article"
```

Save the returned `id`. Later citations need it. If the command prints a
structured object, take `id` from that object — do not invent a slug.

### 4. Attach the supplied document (when applicable)

If the researcher handed you a readable local file (the same PDF/book file
you read in step 1), attach it to the source you just captured:

```bash
python lit_review_cli.py source attach SOURCE_ID -f "/path/to/file.pdf"
```

Only pass `-n`/`--name` if the researcher asks for a specific download name;
otherwise let it default. Do not attach a file you were not given, and do
not skip this step silently when a file was supplied — either attach it or
tell the researcher why you could not (e.g. the path is unreadable).

`source download SOURCE_ID [-o /destination/dir]` retrieves the attached
file later; it is retrieval, not a new capture step, and this skill does not
need to call it during ingestion.

### 5. Identify candidate citations

Capture only passages the researcher pointed at, highlighted, or approved.
Do not bulk-ingest an entire PDF uninvited. If they said "add this paper"
without naming passages, propose a short list of candidate excerpts and wait.

For each approved passage, record:

- locator as `start-end` digits (`142-144`, or `88-88` for one page) for
  `pdf` and `book`; the same `start-end` digit shape for `presentation`, read
  as a slide range (`9-9` for one slide, `9-11` for a span) rather than pages;
  or a non-blank textual reference such as `5:1`, `Chapter 2`, or `#methods`
  for `web`
- excerpt text (quote when they quoted; paraphrase only if they asked)
- optional `context_note` when the excerpt is unclear out of context
- optional `title` only if the researcher gives this specific excerpt a
  short label of its own — never derive one from the excerpt or the
  source's title yourself

### 6. Capture citations

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

### 7. Offer thematic linking

Thematic linking is available (`theme add`, `theme link`, `theme update`,
`theme synthesize`, `theme show`). Follow `tiferet-lit-review-theme`:

1. `theme list` first.
2. Suggest existing theme names, or a new theme name, from the excerpts.
3. Run default `theme link` only after the researcher confirms citation → theme.
   Default link is structural and does not rewrite the description.
4. Offer `theme update -d` for a curated narrative. Do not pass
   `--include-synthesis` or run `theme synthesize` unless they ask to replace
   that text with the naive collage.
5. `theme show THEME_ID` after a successful link so they can see the result.

Never assign themes silently.

## Boundary with later workflows

`abstract`, `outline`, and `paper` are implemented on `v1.x-proto` (KB
Abstracts, named-slot Outlines, and Papers forked from Outlines). They are
separate, researcher-initiated composition workflows, not part of ingestion:

- After capture, this skill may offer confirmed, structural theme linking
  (step 7). It must not assemble an Outline, open a Paper, draft prose, or
  infer any composition decision from the ingested material.
- A KB Abstract is never silently created or rewritten during capture.
- A Paper is never opened during capture.

Do not call or invent `abstract add`, `outline assemble`, or `paper open`
from this skill. If the researcher wants to move captured material into an
Abstract, Outline, or Paper, point them at the relevant CLI group directly —
that decision is outside this skill's scope.

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

python lit_review_cli.py theme show situated-expertise
```

If the year had been missing from the title page, stop after reading and ask
before any `source add`.

## Quality checklist

- Bibliographic fields came from the material or the researcher, never invented.
- Medium is `pdf`, `book`, `web`, or `presentation`.
- Locator is `digits-digits` for `pdf`/`book`/`presentation` (a page range for
  the first two, a slide range for the last), or a non-blank textual
  reference for `web`.
- An overview note, if set, was supplied or approved by the researcher and
  describes the work as a whole, not one passage.
- A URL, if recorded, was supplied or approved by the researcher and was not
  fetched, authenticated, scraped, or treated as a document attachment.
- Every citation has an approved passage (not an unsolicited full-document dump).
- A citation title, if set, was supplied or approved by the researcher — never
  invented, and never a copy of the source's title.
- Existing sources were reused when the same work was already in the store.
- No theme link ran without confirmation.
- Default `theme link` was used unless the researcher asked to synthesize.
- A supplied local file was attached with `source attach`, or the researcher
  was told why it wasn't.
- No `abstract`, `outline`, `paper`, or `activity` command was invented or
  invoked from this skill.
- Returned `id`s were captured from CLI output, not guessed.

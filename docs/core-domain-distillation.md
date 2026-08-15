# Core Domain Distillation — Tiferet Literature Review Knowledge Base

**Status:** Draft · **Domain:** `lit-review` · **Code:** *(not yet implemented)* · **Branch:** `docs-vision-statement-and-core-domain-docs`
**Companion:** `docs/domain-vision.md`

## 1. Purpose of this document

The vision statement says *what* this knowledge base is for. This document says
*how the domain is meant to work*: the vocabulary, the behaviors, the rules
those behaviors enforce, and the way the pieces relate. It is the reference a
contributor should read before writing the first domain object, and the
reference a reviewer should read before judging whether a change belongs.

**This is a forward-looking distillation.** No code exists in this repository
yet — `docs/`, `LICENSE`, `README.md`, and `.gitignore` are the entire contents
of `master` at the time of writing. Every behavior described below is a
candidate, not an implemented fact. Where a claim needs grounding, it is
grounded in the conventions of the Tiferet framework this application is
declared to be "built with" (per `README.md`) — specifically the base classes
documented for `DomainObject` (`tiferet/domain/settings.py`), `DomainEvent`
(`tiferet/events/settings.py`), `Aggregate`/`TransferObject`
(`tiferet/mappers/settings.py`), and `Service`
(`tiferet/interfaces/settings.py`) in the framework's own orientation
documentation — not in anything invented for this repository. Section 10 turns
this distillation into the concrete first slice of implementation work.

It is written to be legible to a technical-adjacent reader who has not yet read
the framework's own conventions in depth. Where a term is unavoidable, it is
defined once, in Section 3, and then used consistently.

## 2. The core domain, restated precisely

The core domain is **capturing sourced evidence and synthesizing it into
themes that can be assembled, correctly cited, into a paper's outline**.

A piece of reading does not become useful by being stored — a saved PDF is
inert. It becomes useful once a specific passage is pulled out as evidence and
connected to an idea that recurs elsewhere in the literature. That connection
is where meaning is made: not at the moment a source is added, and not at the
moment a passage is copied out, but at the moment a passage is told to belong
to an idea that other passages, from other works, also belong to.

The domain has exactly one shape:

> **Capture** a source → **cite** a passage from it → **link** the citation to
> a theme → **synthesize** the theme's description (curated or on demand) →
> **render** the citation in the paper's required style → **assemble** themes
> into the sections and paragraphs of an outline.

and exactly two axes of variation:

1. **Source medium** — the kind of work being read (PDF, book, journal
   article, and whatever is added later), which determines what bibliographic
   fields are expected and what a "locator" (the passage's precise position)
   means for that medium.
2. **Citation style** — the named formatting convention (APA, MLA, Chicago, or
   another) a given paper requires, which determines how a bibliographic
   record and a locator render into an in-text citation and a reference-list
   entry.

Everything else — recording a citation's excerpt and locator, linking a
citation to a theme, re-synthesizing a theme's description as its linkages
grow, and assembling themes into an outline — is identical regardless of what
kind of source is being read or what style the paper eventually needs. That
asymmetry is the single most important fact about this domain, and Section 8
treats it directly.

## 3. Ubiquitous language

**Source** — a work being read: a PDF, a book, or another medium added later.
Carries a bibliographic record and, where relevant, a pointer to the underlying
file.

**Bibliographic record** — the structured metadata about a source (authors,
year, title, container title, publisher, and the other fields a citation style
needs) required to reference it correctly. Captured once, per source, and
reused by every citation and every rendering drawn from that source.

**Locator** — the precise position of a passage within a source: a page range
for a PDF or book today, and whatever position concept a future medium
requires (see Section 4).

**Citation** — an excerpt or paraphrase pulled from a source, together with its
locator and enough surrounding context to be understood on its own. The atomic
unit of evidence in this domain.

**Theme** — a strand of meaning that gathers citations from one or more
sources. A theme carries a **synthesized description**: a standing, current
statement of what its linked citations collectively say, distinct from any one
citation's wording.

**Linkage** — the structural relationship connecting a citation to a theme.
Forming a linkage is the atomic act of attaching evidence to an idea,
incrementing the theme's linkage count without destructively overwriting any
existing narrative description. A citation may hold linkages to more than one
theme.

**Synthesis** — the evaluative act of generating or revising a theme's
synthesized description against its full linkage set. Can be performed
manually by the researcher (curated editorial synthesis), invoked on demand
via an automated synthesis service (`theme synthesize`), or requested at link
time via an opt-in flag (`--include-synthesis`).

**Citation style** — a named formatting convention (e.g. APA, MLA, Chicago)
that determines how a bibliographic record and a locator are rendered.

**Formatted reference** — a bibliographic record rendered, in a given citation
style, into the reference-list entry form for a source.

**In-text citation** — a citation's locator rendered, in a given citation
style, into the short parenthetical or footnote form used inline in prose.

**Assembly** — the arrangement of one or more themes, with their supporting
citations rendered as formatted references and in-text citations, into the
sections and paragraphs of a paper's outline. Assembly does not draft prose; it
arranges already-synthesized, already-cited material.

**Outline** — the target structure (sections, and paragraph-level slots within
them) that an assembly populates.

**Provenance** — the unbroken path from any piece of content appearing in an
assembly back through its citation to its source, preserved regardless of how
many themes that citation has been linked to or how many outlines it has been
assembled into.

## 4. What the domain reads / operates on

The domain operates on bibliographic and textual data supplied about a source
— it does not read the source file itself. That is a deliberate boundary
(Section 9): PDF text extraction, OCR, and the mechanics of getting words out
of a book are infrastructure the domain depends on, not part of it.

What is captured, per source medium:

- **PDF or book (today):** authors, year, title, and publisher-family fields,
  plus a page-range locator for each citation drawn from it.
- **Any future medium** (journal article, web page, dataset, and so on) is
  expected to supply the same two things — a bibliographic record and a
  locator convention appropriate to that medium — without changing anything
  about how citations, linkages, or themes work. This is the leverage point of
  the source-medium axis: new mediums are new *field sets and locator shapes*,
  not new domain behavior.

At render time, the domain also takes a **citation style selection** as input,
and at assembly time it takes the **target outline shape** — the sections and
paragraph slots a specific paper defines. Neither input changes what a
citation or a theme *is*; both change how existing citations and themes are
*rendered and arranged*.

## 5. The behaviors

Each behavior below is a bounded step, described as a candidate domain event in
the Tiferet sense — a unit with a clear input and output, dependencies
supplied by injection, and an `execute(**kwargs)` entry point
(`tiferet/events/settings.py`). None of these events exist yet; naming them
here is what makes Section 10 concrete.

### 5.1 Capturing a source

*Register a work being read, with its bibliographic record.*

Would be modeled as a domain event (candidate name: `AddSource`) constructing a
`Source` domain object and its mutable `Aggregate` counterpart, following
Tiferet's split between read-only domain objects and the aggregates that
mutate them (`tiferet/domain/settings.py`, `tiferet/mappers/settings.py`).

**Variable** with respect to the source-medium axis: the expected bibliographic
fields and the locator convention differ by medium. **Agnostic** otherwise: a
source is a source regardless of what will later be cited from it.

### 5.2 Citing a passage

*Pull an excerpt from a source, at a precise locator, with enough context to
stand alone.*

Candidate event: `AddCitation`. A citation always refers to exactly one source
and carries one locator plus the excerpt text.

**Agnostic**: the shape of a citation — source reference, locator, excerpt —
is uniform no matter the source medium. **Variable** only in that the locator's
internal shape (a page range, eventually something else) traces back to the
source-medium axis established when the source was captured.

### 5.3 Linking a citation to a theme

*Attach a citation to one or more themes, establishing a durable evidence relationship.*

Candidate event: `LinkCitationToTheme`. Linking is a pure structural operation:
it verifies the citation and theme exist, creates a unique `Linkage` row, and
increments the theme aggregate's `linkage_count`. By default, linking is
non-destructive and zero-cost with respect to text generation: it does not
overwrite an existing human-crafted thesis summary. When immediate synthesis
is desired, an opt-in flag (`--include-synthesis`) can trigger the synthesis
pipeline as part of the link event.

**Fully agnostic** with respect to both axes: linking is identical no matter
what medium the citation's source came from or what style the eventual paper
will use.

### 5.4 Synthesizing and updating a theme

*Generate, revise, or manually curate a theme's synthesized description.*

Candidate events: `SynthesizeTheme` (or `ResynthesizeTheme`) and `UpdateTheme`.
- `SynthesizeTheme` loads all citations currently linked to the theme, invokes the
  injected `ThemeSynthesisService.synthesize(theme, citations)`, and updates
  the theme aggregate's `synthesized_description`.
- `UpdateTheme` provides direct editorial control, updating the theme's name or
  manually written narrative synthesis via `set_attribute()`.

Decoupling synthesis from linking ensures batch ingestion is efficient, human
prose is first-class, and automated synthesis can be re-run on demand whenever
a new synthesis model or algorithm lands.

**Fully agnostic**: synthesis reads already-captured citations and produces
text independent of source medium or output citation style.

### 5.5 Rendering a citation in a style

*Format a source's bibliographic record and a citation's locator into a
specific citation style's in-text and reference-list form.*

Candidate event: `RenderCitation`, taking a citation and a style selection and
producing a formatted reference and an in-text citation.

**This is the step whose behavior is entirely defined by one axis.** The
rendering mechanism — take a bibliographic record and a locator, produce two
strings — is the same for every style. What differs, per style, is the
rulebook: field order, punctuation, abbreviation conventions, and how the
in-text form is shaped. This is the same "one mechanism, many rulebooks"
pattern the Tiferet Dialect Compiler uses for component types
(`docs/compiler/core-domain-distillation.md` in `tiferet-takwin`, Section 5.4)
— here the rulebook varies by citation style instead of by component type.

### 5.6 Assembling themes into an outline

*Arrange one or more themes, with their linked citations rendered in the
paper's style, into the sections and paragraphs of an outline.*

Candidate event: `AssembleOutline`. Assembly reads a theme's synthesized
description and its linked citations, resolves each citation's rendering for
the paper's chosen style (Section 5.5), and places the result into the target
outline's sections and paragraph slots.

**Agnostic** in mechanism: arranging themes into slots does not depend on
source medium or citation style once rendering has already happened. It does,
however, need visibility into both the theme layer and the source/citation
layer at once (Section 7) — it is the one behavior that spans the whole
domain rather than one link in the chain.

## 6. How the behaviors compose

No pipeline configuration exists yet (there is no `feature.yml` in this
repository). The intended composition, following Tiferet's convention of
declaring feature workflows as ordered steps rather than hard-coding call
order (`tiferet/contexts/feature.py`), is:

- **capture-source** — register a source and its bibliographic record.
- **cite-passage** — pull a citation from an already-captured source.
- **link-citation** — connect a citation to one or more themes (pure structural linkage).
- **synthesize-theme** — synthesize or curate a theme's description across its full linkage set (on demand or manual).
- **render-citation** — format a citation in a requested style, for reuse
  wherever that citation appears.
- **assemble-outline** — arrange themes into an outline, rendering their
  citations along the way.

The first three form the "capture and linking loop," run rapidly per passage
as research progresses. The fourth forms the "synthesis loop," run when ideas
are evaluated or refined. The last two form the "drafting loop," run whenever
assembly of a specific paper is underway.

```mermaid
flowchart LR
  SRC([Add source]) --> CITE["Cite a passage<br/>excerpt + locator"]
  CITE --> LINK["Link to theme(s)<br/>structural association"]
  LINK --> THEME[(\"Theme<br/>linkage set\")]
  THEME --> SYNTH[\"Synthesize theme<br/>curated or on-demand\"]
  SYNTH --> THEME
  THEME --> ASM[\"Assemble outline<br/>sections + paragraphs\"]
  CITE --> REND[\"Render citation<br/>in paper's style\"]
  REND --> ASM
  ASM --> OUT([Outline with citations])
```

## 7. Relationships / cross-boundary rules

A source has many citations; a citation belongs to exactly one source but may
hold linkages to many themes; a theme is defined by the full set of citations
currently linked to it. None of these relationships are optional metadata —
each is load-bearing for a specific later behavior:

- **Citation → Source** is what makes rendering (5.4) possible at all: a
  citation carries only a locator, not a bibliographic record, so rendering
  always resolves through the source it names.
- **Citation → Theme** (via linkage) is what makes synthesis (5.3) possible:
  a theme's description is a function of *all* its linkages, not the newest
  one, so revising a theme requires reading its full linkage set, not just the
  citation that triggered the revision.
- **Theme → Outline** (via assembly) is what makes provenance survive
  drafting: assembly must be able to walk backward from a placed theme, through
  its citations, to their sources, so that a formatted reference appearing in
  an outline can always be traced and re-verified.

This is why assembly (5.5) cannot be a thin read of a theme's synthesized
description alone. It needs the theme's current meaning **and** its full
citation trail at the same time, because a paper's outline is expected to
carry working citations, not just distilled prose. This is the same shape of
requirement the Tiferet Dialect Compiler names for relationship checking:
judging a connection correctly requires an input beyond the immediate object
being judged (`docs/compiler/core-domain-distillation.md` in `tiferet-takwin`,
Section 7) — there, the component type; here, the citation style and the
source's bibliographic record.

## 8. The agnostic core and the variable edge

Stated plainly, so that implementation work can be scoped against it:

**Agnostic — build once, never per axis:**
- Recording a citation's excerpt and locator reference.
- Forming a linkage between a citation and a theme.
- The mechanism of theme synthesis: reconsidering a description given a
  linkage set (the algorithm, not the wording it produces).
- Assembling themes and their rendered citations into an outline's sections
  and paragraph slots.
- Provenance tracking from outline back to source.

**Variable — one definition per axis:**
- **Per source medium:** the expected bibliographic fields and the shape of a
  locator.
- **Per citation style:** the rulebook a bibliographic record and locator are
  rendered through to produce an in-text citation and a reference-list entry.

**Anticipated entanglement — risks to design against, not yet incurred:**
Because no code exists, there is no line-referenced inventory to give here.
The honest equivalent, for a forward-looking distillation, is to name where
entanglement is *likely* to appear if the two axes are not deliberately
separated from day one:

- Treating "PDF" as the only source medium in the citation's locator shape,
  rather than letting locator shape vary by source medium from the start,
  would silently couple citation recording to one medium.
- Hard-coding one citation style's punctuation or field order into the
  bibliographic record itself, rather than keeping the record style-neutral
  and rendering per style on demand, would make adding a second style a
  rewrite instead of an addition.
- Letting assembly read a theme's synthesized description without also
  resolving live citation renderings would let an outline drift out of sync
  with its own citation style if that selection changes after themes are
  already assembled.

Naming these now is what the first implementation slice (Section 10) should
be built to avoid.

## 9. Boundaries

**Inside the domain:** capturing sources and their bibliographic records,
recording citations with their locators, forming and refining linkages between
citations and themes, rendering citations in a requested style, and assembling
themes into an outline with working provenance back to source.

**Outside the domain:**
- Extracting text from a PDF, transcribing a book, or running OCR — supplied
  by infrastructure utilities the domain depends on (in Tiferet terms, a
  `FileService`-style component, `tiferet/interfaces/settings.py`), not
  authored by it.
- Drafting the paper's actual prose — the author's job, whether done by hand
  or with an agentic writing tool that reads sourced, cited themes out of this
  knowledge base.
- Deciding *which* citation style a given paper requires — that is supplied to
  the domain as a selection, the same way a target outline shape is supplied,
  not decided by it.
- General file or document storage — the underlying persistence mechanism
  (however it ends up being built) is an infrastructure concern the domain's
  repositories depend on, not the domain's own behavior.

## 10. Where this leads

The distillation above points at a first, well-bounded implementation slice:

1. **Domain objects for the four core nouns.** `Source`, `Citation`, `Theme`,
   and `Linkage`, following the `DomainObject`/`Aggregate` split
   (`tiferet/domain/settings.py`, `tiferet/mappers/settings.py`), with the
   source-medium axis expressed as field variation on `Source` and locator
   shape, not as separate domain object types.
2. **The reading-loop events first.** `AddSource`, `AddCitation`, and
   `LinkCitationToTheme` — these three make the theme-synthesis bet
   (Section 2) real, and can be built and tested before any rendering or
   assembly work starts.
3. **Citation style as a declared rulebook, not a branch.** Following the
   compiler's "one mechanism, many rulebooks" precedent
   (`docs/compiler/core-domain-distillation.md` in `tiferet-takwin`,
   Section 5.4), a style's rendering rules should be data the render event
   reads, not `if`/`elif` branches inside it.
4. **One citation style implemented as proof.** Building a single style (a
   natural first choice: APA) end-to-end through rendering is the test that
   the style axis is genuinely separable from citation recording, before a
   second style is attempted.
5. **Assembly last.** `AssembleOutline` depends on both the reading loop and
   rendering already existing, and is the natural point to validate that
   provenance survives all the way from a captured source to a placed,
   correctly cited paragraph.

Each is a candidate for its own TRD. Together they are the difference between
a set of ideas about how a literature review knowledge base should work and
the knowledge base the vision statement describes.

# Domain Vision Statement — Tiferet Literature Review Knowledge Base

**Status:** Draft · **Domain:** `lit-review` · **Code:** `app/` · **Branch:** `v1.x-proto`

## The bet: organize around your argument, not around your sources

Every reference manager on the market is organized the same way: it starts from
the source. You import a PDF or a book, you tag it, maybe you highlight a
passage, and the tool files that passage under the source it came from. When it
comes time to write, you are left re-reading your own tags and highlights,
trying to remember why you saved them and how they fit together.

That works for storage. It does not work for thinking. A dissertation or a
paper is not an inventory of sources — it is an argument, built out of ideas
that show up, in different words, across many different works. The thing worth
organizing is not "everything Smith (2019) said," it is "what does the
literature say about X," where X is assembled from Smith, Jones, and a dozen
others.

**This knowledge base bets on organizing by idea instead of by source.** Sources
and the citations pulled from them still matter — they are the evidence — but
the unit you build your paper from is a **theme**: a strand of meaning that
gathers citations from wherever they come from, and gets sharper and more
precise with each one it gathers.

## What this domain makes real

The lit-review knowledge base is a place to hold a growing body of research
reading — sources, the files that belong to them when the researcher has them,
the citations pulled from those works, the themes those citations belong to,
the abstracts that compose a selection of those themes into an argument-level
brief, the outline that arranges those themes into slots, the paper that
turns those slots into drafted sections, and the bibliographic record needed
to cite them correctly — in a form that stays organized as it grows, and that
can be handed to a human or an AI writing assistant, fully sourced and
properly citable, when it is time to draft.

## What we get for it

### Themes that get smarter, not just longer
A tag list only ever grows in volume. A theme in this system grows in
**meaning**: as citations are linked to it, the theme maintains a living
synthesis of what the literature says, without holding the researcher's
curated prose hostage. Linking evidence is a pure, zero-cost structural fact;
synthesizing is an evaluative, on-demand or collaborative act. A theme can be
synthesized automatically across its full evidence set, updated manually with
the researcher's own prose, or refreshed whenever a new synthesis model lands.
After a year of reading, a theme is not a bucket of forty highlights — it is a
distilled, current statement of what the literature says, with forty citations
standing behind it as evidence.

### One citation, many arguments
A single passage in a single source often speaks to more than one idea. This
system lets one citation belong to several themes at once, so a striking
sentence from one book can support your methodology section and your
literature-gap section without being copied, retyped, or filed twice.

### A source you can reopen, not only remember
A bibliographic stub is enough to cite a work. It is not enough to check a
page, compare two PDFs, or hand an agent the text a locator is supposed to
point at. When a source has an associated file, this knowledge base keeps that
body with the source and gives it a stable download name — so the file comes
back as *this* work, not as whatever the upload was called on disk.

### An argument you can state before you outline
A theme says what the literature says about one idea. An **abstract** says
what *this* paper (or this cut of the reading) is claiming, by composing a
chosen set of themes into one standing brief. Linking a theme into an
abstract is structural and cheap; writing or synthesizing the brief is
explicit. The same theme can support more than one abstract; the theme does
not own those briefs.

### A running head start on the writing
Because themes accumulate their own synthesized meaning and their supporting
citations as you read, and because an abstract can already state the argument
those themes jointly make, the **outline** of a paper is largely built *before*
drafting starts. Arranging themes into slots turns "start from a blank page"
into "arrange what I already know." Turning that outline into a **paper**
creates sections the researcher (or an agent) can draft one at a time — each
section keeping the themes that justify it and a context note for why it was
written that way.

An outline is not a paper. Opening a paper **forks** the arrangement into the
manuscript; the outline stays as a record of origin and is not kept in sync.
A paper is not a source. Storage that happens to look like a generic
knowledge-base document is infrastructure, not a domain noun.

### Citations that are never orphaned, and never misformatted
Every citation always traces back to the exact source and location it came
from, and every source carries the bibliographic detail (the names as they
appear on that work, year, title, publisher, and the rest) needed to reference
it correctly. Those names are a copy of what the source printed — enough to
format a citation — not a roster of people this knowledge base manages. As
themes are assembled into paper sections, both the passage and its properly
formatted citation travel together, so a citation dropped into a draft — by
hand or with the help of an AI writing tool — is correct in the style the
paper requires, not just present.

### Reading time that compounds
The value of a passage read once is not spent once. Because passages are kept
as durable, thematically-linked citations rather than personal marginalia, a
source you read for one project keeps paying off in the next.

## The core of the work

Everything in this domain follows one path:

> **Capture** a source → **attach** its document when you have the file →
> **cite** a passage from it → **link** the citation to one or more themes →
> **synthesize** the theme's meaning (curated or on demand) → **compose** an
> abstract from a selection of themes → **render** citations in the paper's
> required style → **assemble** an outline from themes → **open a paper** from
> that outline → **draft** each paper section (content + context).

Sources and citations are the structural half: a source is added with its
bibliographic detail, an optional named document can be attached so the work
itself can be reopened or compared, a citation is pulled from it with a
precise locator, and linkages attach evidence to themes. The intellectual half
is the theme, the abstract, and their synthesis. A theme is not declared
complete and then filled in — it is a living synthesis that **accretes meaning
across its linked citations**. An abstract is not a theme of themes — it is a
standing brief of one argument, composed from a chosen set of themes. A paper
is the manuscript aggregate: it owns its abstract, its sections, and the
citations used in that manuscript. Linking (citation to theme, theme to
abstract, theme to paper section) is decoupled from writing the thesis.
Researchers can link in bulk, craft narrative summaries manually, or trigger
automated re-synthesis on demand.

The central design commitment, then, is: **the theme, not the source, is the
unit of intellectual work**, and an abstract is how a *selection* of those
themes becomes one argument. Evidence is gathered continuously; theme and
abstract synthesis are refined iteratively without accidental overwrites.
Bibliographic accuracy is carried alongside that work rather than bolted on
afterward, because a citation is only useful for drafting if it can be traced
and correctly referenced at the same time.

## What it deliberately does not do

It does not invent the paper's voice. It holds an outline, then a paper whose
sections can be drafted by the researcher or an agent — content plus a context
note for why the section was written that way. Narrative flow and argument
phrasing remain the author's job. A later publication event (venue, DOI) is
not this step; when a paper is published, that appearance can become a Source.

It does not tag sources or themes for search. Themes *are* the lookup
vocabulary; a second tag layer would be a weaker classification next to the
one the researcher already thinks in.

It does not extract text from PDFs, transcribe books, or run OCR — that is
infrastructure the domain depends on, not part of the domain itself. It *does*
hold a source's associated file, name it for download, and let later work
retrieve or compare that body. Holding the work is not the same as parsing it.

It does not manage authors as people. A source keeps a copy of the name printed
on that work so the work can be cited; it does not identify, merge, or track
the person behind the name. That copy is created by the source, not as a
standalone author record.

---

*Companion document:* `docs/core-domain-distillation.md` — the detailed
walkthrough of the domain's vocabulary, behaviors, and the relationships
between its parts.

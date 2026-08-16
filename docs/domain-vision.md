# Domain Vision Statement — Tiferet Literature Review Knowledge Base

**Status:** Draft · **Domain:** `lit-review` · **Code:** `app/` · **Branch:** `rfp-4-citation-style-rendering`

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
reading — sources, the citations pulled from them, the themes those citations
belong to, and the bibliographic record needed to cite them correctly — in a
form that stays organized as it grows, and that can be handed to a human or an
AI writing assistant, fully sourced and properly citable, when it is time to
draft.

## What we get for it

### Themes that get smarter, not just longer
A tag list only ever grows in volume. A theme in this system grows in
**meaning**: every time a new citation is linked to it, the theme's own
description is revisited and refined in light of that addition. After a year of
reading, a theme is not a bucket of forty highlights — it is a distilled,
current statement of what the literature says, with forty citations standing
behind it as evidence.

### One citation, many arguments
A single passage in a single source often speaks to more than one idea. This
system lets one citation belong to several themes at once, so a striking
sentence from one book can support your methodology section and your
literature-gap section without being copied, retyped, or filed twice.

### A running head start on the writing
Because themes accumulate their own synthesized meaning and their supporting
citations as you read, the outline of a paper's argument is largely built
*before* drafting starts. Assembling themes into sections and paragraphs of an
outline turns "start from a blank page" into "arrange what I already know."

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

> **Capture** a source → **cite** a passage from it → **link** the citation to
> one or more themes → **assemble** themes into the sections and paragraphs of
> a paper's outline, complete with properly formatted citations.

Sources and citations are the easy, mechanical half: a source is added with its
bibliographic detail, and a citation is pulled from it with enough context to
place it precisely. The interesting half is the theme. A theme is not declared
complete and then filled in — it is a living synthesis that **accretes meaning
with every citation linked to it**. Linking a citation to a theme is not
filing; it is telling the knowledge base something new about what that theme
means, and the theme's standing description should reflect the fullest, most
current understanding each time.

The central design commitment, then, is: **the theme, not the source, is the
unit of intellectual work**, and every relationship between a citation and a
theme is an event that can refine the theme, not just a label attached to it.
Bibliographic accuracy is carried alongside that work rather than bolted on
afterward, because a citation is only useful for drafting if it can be traced
and correctly referenced at the same time.

## What it deliberately does not do

It does not write the paper. It holds distilled, cited, thematically organized
material *for* drafting — the actual prose, argument phrasing, and narrative
flow of a paper are the author's job, done with or without the help of an
agentic writing tool that reads from this knowledge base.

It does not extract text from PDFs, transcribe books, or run OCR — that is
infrastructure the domain depends on, not part of the domain itself.

It does not manage authors as people. A source keeps a copy of the name printed
on that work so the work can be cited; it does not identify, merge, or track
the person behind the name. That copy is created by the source, not as a
standalone author record.

---

*Companion document:* `docs/core-domain-distillation.md` — the detailed
walkthrough of the domain's vocabulary, behaviors, and the relationships
between its parts.

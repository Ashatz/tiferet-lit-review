"""Lit Review Synthesis Utilities

V1 placeholder synthesis strategies. Theme synthesis and abstract synthesis
are the same *kind* of act and different services. Swap either naive
implementation for a future LLM via di.yml only. Agent-written prose lands
through editorial update events, not by importing a model here.
"""

# *** imports

# ** core
from typing import List

# ** app
from ..domain.abstract import Abstract
from ..domain.citation import Citation
from ..domain.theme import Theme
from ..interfaces.source import SourceService
from ..interfaces.synthesis import AbstractSynthesisService, ThemeSynthesisService

# *** constants

# ** constant: max_synthesis_excerpts
MAX_SYNTHESIS_EXCERPTS = 10

# *** utils

# ** util: naive_theme_synthesizer
class NaiveThemeSynthesizer(ThemeSynthesisService):
    '''
    Placeholder ThemeSynthesisService: concatenates each citation's excerpt
    with its source's short reference (Author (Year)), most-recently-linked
    first (caller supplies that order), capped at MAX_SYNTHESIS_EXCERPTS.
    '''

    # * attribute: source_service
    source_service: SourceService

    # * init
    def __init__(self, source_service: SourceService) -> None:
        '''
        Initialize the naive theme synthesizer.

        :param source_service: Used to resolve Author (Year) from each
            citation's parent source.
        :type source_service: SourceService
        '''

        # Set the source service dependency.
        self.source_service = source_service

    # * method: synthesize
    def synthesize(self, theme: Theme, citations: List[Citation]) -> str:
        '''
        Build a concatenated synthesis from the full citation set.

        :param theme: The theme being synthesized (unused by the naive
            strategy beyond establishing the seam signature).
        :type theme: Theme
        :param citations: All citations currently linked to the theme, in
            preferred display order (most-recently-linked first).
        :type citations: List[Citation]
        :return: The concatenated synthesis text.
        :rtype: str
        '''

        # Cap the citation set for readability.
        selected = citations[:MAX_SYNTHESIS_EXCERPTS]

        # Build one "Author (Year): excerpt" line per citation.
        lines: List[str] = []
        for citation in selected:
            reference = self._short_reference(citation)
            lines.append(f'{reference}: {citation.excerpt}')

        # Join lines; empty citation sets yield an empty description.
        return '\n'.join(lines)

    # * method: _short_reference
    def _short_reference(self, citation: Citation) -> str:
        '''
        Format a citation's source as Author (Year), with et al. when needed.

        :param citation: The citation whose source to format.
        :type citation: Citation
        :return: A short bibliographic reference, or the citation id if the
            source cannot be resolved.
        :rtype: str
        '''

        # Resolve the parent source; fall back to the citation id if missing.
        source = self.source_service.get(citation.source_id)
        if source is None:
            return citation.id

        # Format first author, optionally with et al., plus year.
        if not source.authors:
            author = 'Unknown'
        elif len(source.authors) == 1:
            author = source.authors[0].display_name
        else:
            author = f'{source.authors[0].display_name} et al.'

        # Return the short reference.
        return f'{author} ({source.year})'


# ** util: naive_abstract_synthesizer
class NaiveAbstractSynthesizer(AbstractSynthesisService):
    '''
    Placeholder AbstractSynthesisService: concatenates each joined theme's
    name and synthesized description in insertion order. Not an LLM; swap
    via di.yml when a later model lands.
    '''

    # * method: synthesize
    def synthesize(self, abstract: Abstract, themes: List[Theme]) -> str:
        '''
        Build a concatenated brief from the full joined theme set.

        :param abstract: The abstract being synthesized (unused by the naive
            strategy beyond establishing the seam signature).
        :type abstract: Abstract
        :param themes: All themes currently joined to the abstract, in
            insertion order.
        :type themes: List[Theme]
        :return: The concatenated abstract body.
        :rtype: str
        '''

        # Build one "name: description" line per theme.
        lines: List[str] = []
        for theme in themes:
            lines.append(f'{theme.name}: {theme.synthesized_description}')

        # Join lines; empty theme sets yield an empty body.
        return '\n'.join(lines)

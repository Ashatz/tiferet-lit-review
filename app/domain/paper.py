"""Lit Review Paper Domain Model"""

# *** imports

# ** core
from time import time
from typing import List, Optional
from uuid import uuid4

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: paper_section_theme
class PaperSectionTheme(DomainObject):
    '''
    A theme included in a PaperSection. This is not a Theme entity: it
    carries no lifecycle of its own and exists only as a join owned by
    the section.
    '''

    # * attribute: theme_id
    theme_id: str = Field(
        ...,
        description='The identifier of the included theme.',
    )

    # * attribute: position
    position: int = Field(
        ...,
        description='The zero-based order of this theme on the section.',
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )


# ** model: paper_section
class PaperSection(DomainObject):
    '''
    A part of a Paper: title, drafted content, a context note, and the
    themes that justify it. It has no lifecycle off the paper that owns
    it.
    '''

    # * attribute: id
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='The unique section identifier, generated if absent.',
    )

    # * attribute: title
    title: str = Field(
        ...,
        description='The human heading for this section.',
    )

    # * attribute: content
    content: str = Field(
        default='',
        description='The drafted section prose; empty until an editorial write.',
    )

    # * attribute: context
    context: str = Field(
        default='',
        description='Why this section exists / why it was drafted this way.',
    )

    # * attribute: themes
    themes: List[PaperSectionTheme] = Field(
        default_factory=list,
        description='Owned theme joins, in insertion order.',
    )

    # * attribute: theme_count
    theme_count: int = Field(
        default=0,
        description='Denormalized count of themes joined to this section.',
    )

    # * attribute: position
    position: int = Field(
        ...,
        description='The zero-based order of this section in the paper.',
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )

    # * method: has_theme
    def has_theme(self, theme_id: str) -> bool:
        '''
        Report whether this section already includes the given theme.

        :param theme_id: The theme identifier to look up.
        :type theme_id: str
        :return: True when the theme is joined to this section.
        :rtype: bool
        '''

        # Match against the owned join identifiers.
        return any(theme.theme_id == theme_id for theme in self.themes)


# ** model: paper_abstract
class PaperAbstract(DomainObject):
    '''
    The brief owned by a Paper. It may copy a KB Abstract and then be
    edited. It is not the KB Abstract noun.
    '''

    # * attribute: body
    body: str = Field(
        default='',
        description='The current paper brief; empty until an editorial write or copy.',
    )

    # * attribute: source_abstract_id
    source_abstract_id: Optional[str] = Field(
        default=None,
        description='Optional origin KB Abstract identifier when the body was copied.',
    )


# ** model: paper_citation
class PaperCitation(DomainObject):
    '''
    A KB citation used in this manuscript. This is not a second evidence
    store: it resolves to an existing Citation.
    '''

    # * attribute: citation_id
    citation_id: str = Field(
        ...,
        description='The identifier of the KB citation used in this paper.',
    )

    # * attribute: section_id
    section_id: Optional[str] = Field(
        default=None,
        description='Optional paper section this citation is used in.',
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )


# ** model: paper
class Paper(DomainObject):
    '''
    The manuscript aggregate. It owns a Paper Abstract, ordered Paper
    Sections, and the Paper Citations used in that manuscript.
    '''

    # * attribute: id
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='The unique paper identifier, generated if absent.',
    )

    # * attribute: title
    title: str = Field(
        ...,
        description='The short label for this manuscript.',
    )

    # * attribute: outline_id
    outline_id: Optional[str] = Field(
        default=None,
        description='Optional origin outline identifier; not a live foreign key.',
    )

    # * attribute: abstract
    abstract: Optional[PaperAbstract] = Field(
        default=None,
        description='Owned paper brief, when one has been set.',
    )

    # * attribute: sections
    sections: List[PaperSection] = Field(
        default_factory=list,
        description='Owned sections, in open or insertion order.',
    )

    # * attribute: section_count
    section_count: int = Field(
        default=0,
        description='Denormalized count of sections on this paper.',
    )

    # * attribute: citations
    citations: List[PaperCitation] = Field(
        default_factory=list,
        description='Owned manuscript citation joins, in insertion order.',
    )

    # * attribute: citation_count
    citation_count: int = Field(
        default=0,
        description='Denormalized count of citations used in this paper.',
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )

    # * method: get_section
    def get_section(self, section_id: str) -> Optional[PaperSection]:
        '''
        Retrieve an owned section by its identifier.

        :param section_id: The section identifier to look up.
        :type section_id: str
        :return: The matching section, or None if this paper does not own it.
        :rtype: Optional[PaperSection]
        '''

        # Return the first owned section with this id.
        return next(
            (section for section in self.sections if section.id == section_id),
            None,
        )

    # * method: has_section
    def has_section(self, section_id: str) -> bool:
        '''
        Report whether this paper owns the given section.

        :param section_id: The section identifier to look up.
        :type section_id: str
        :return: True when the section belongs to this paper.
        :rtype: bool
        '''

        # Delegate to the owned-section lookup.
        return self.get_section(section_id) is not None

    # * method: has_citation
    def has_citation(self, citation_id: str, section_id: Optional[str] = None) -> bool:
        '''
        Report whether this paper already uses the given citation.

        When section_id is supplied, the match is scoped to that section.

        :param citation_id: The KB citation identifier to look up.
        :type citation_id: str
        :param section_id: Optional section scope for the lookup.
        :type section_id: Optional[str]
        :return: True when the citation is already used in this paper.
        :rtype: bool
        '''

        # Match against owned manuscript joins, optionally scoped to a section.
        return any(
            item.citation_id == citation_id
            and (section_id is None or item.section_id == section_id)
            for item in self.citations
        )

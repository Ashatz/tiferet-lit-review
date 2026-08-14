"""Lit Review Theme Events"""

# *** imports

# ** core
from typing import List, Union
from uuid import uuid4

# ** app
from tiferet import DomainEvent

from ..domain.theme import slugify_theme_name
from ..interfaces.citation import CitationService
from ..interfaces.source import SourceService
from ..interfaces.linkage import LinkageService
from ..interfaces.synthesis import ThemeSynthesisService
from ..interfaces.theme import ThemeService
from ..mappers.linkage import LinkageAggregate
from ..mappers.theme import ThemeAggregate
from .citation import CITATION_NOT_FOUND_ID

# *** constants

# ** constant: theme_not_found_id
THEME_NOT_FOUND_ID = 'THEME_NOT_FOUND'

# *** events

# ** event: theme_event
class ThemeEvent(DomainEvent):
    '''
    Base event providing the shared ThemeService dependency.
    '''

    # * attribute: theme_service
    theme_service: ThemeService

    # * init
    def __init__(self, theme_service: ThemeService) -> None:
        '''
        Initialize the ThemeEvent.

        :param theme_service: The theme service dependency.
        :type theme_service: ThemeService
        '''

        # Set the theme service dependency.
        self.theme_service = theme_service

# ** event: add_theme
class AddTheme(ThemeEvent):
    '''
    Register a new Theme with an empty synthesis until the first linkage.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name'])
    def execute(self, name: str, **kwargs) -> ThemeAggregate:
        '''
        Add a new theme.

        :param name: The short label for the theme.
        :type name: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The created theme aggregate.
        :rtype: ThemeAggregate
        '''

        # Derive a slug id from the name; fall back to UUID on collision.
        theme_id = slugify_theme_name(name)
        if self.theme_service.exists(theme_id):
            theme_id = str(uuid4())

        # Create and save the theme aggregate with empty synthesis defaults.
        new_theme = ThemeAggregate(
            id=theme_id,
            name=name,
            synthesized_description='',
            linkage_count=0,
        )
        self.theme_service.save(new_theme)

        # Return the newly created theme.
        return new_theme

# ** event: get_theme
class GetTheme(ThemeEvent):
    '''
    Retrieve a Theme by its ID.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> ThemeAggregate:
        '''
        Retrieve a theme by ID.

        :param id: The theme identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The theme aggregate.
        :rtype: ThemeAggregate
        '''

        # Retrieve the theme from the service.
        theme = self.theme_service.get(id)

        # Verify the theme exists.
        self.verify(
            theme is not None,
            THEME_NOT_FOUND_ID,
            message=f'Theme not found: {id}.',
            id=id,
        )

        # Return the theme.
        return theme

# ** event: list_themes
class ListThemes(ThemeEvent):
    '''
    List all themes.
    '''

    # * method: execute
    def execute(self, **kwargs) -> List[ThemeAggregate]:
        '''
        List all themes.

        :param kwargs: Additional keyword arguments (unused).
        :type kwargs: dict
        :return: All theme aggregates.
        :rtype: List[ThemeAggregate]
        '''

        # Return all themes from the service.
        return self.theme_service.list()

# ** event: list_linkages_for_theme
class ListLinkagesForTheme(DomainEvent):
    '''
    List all linkages belonging to a given theme, in insertion order.
    '''

    # * attribute: linkage_service
    linkage_service: LinkageService

    # * init
    def __init__(self, linkage_service: LinkageService) -> None:
        '''
        Initialize the ListLinkagesForTheme event.

        :param linkage_service: The linkage service dependency.
        :type linkage_service: LinkageService
        '''

        # Set the linkage service dependency.
        self.linkage_service = linkage_service

    # * method: execute
    @DomainEvent.parameters_required(['theme_id'])
    def execute(self, theme_id: str, **kwargs) -> List[LinkageAggregate]:
        '''
        List all linkages for a theme.

        :param theme_id: The theme identifier to filter linkages by.
        :type theme_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The linkages belonging to the theme, in insertion order.
        :rtype: List[LinkageAggregate]
        '''

        # Return the linkages filtered by theme_id.
        return self.linkage_service.list(theme_id=theme_id)

# ** event: link_citation_to_theme
class LinkCitationToTheme(DomainEvent):
    '''
    Attach a citation to a theme and reconsider the theme's synthesis against
    the full linkage set.

    On a *new* linkage this event returns the updated ThemeAggregate. On an
    idempotent re-link of an existing (citation_id, theme_id) pair it returns
    the existing LinkageAggregate without re-synthesizing. CLI wiring should
    follow a successful link with theme show/get for a stable presentation.
    '''

    # * attribute: theme_service
    theme_service: ThemeService

    # * attribute: linkage_service
    linkage_service: LinkageService

    # * attribute: citation_service
    citation_service: CitationService

    # * attribute: theme_synthesis_service
    theme_synthesis_service: ThemeSynthesisService

    # * init
    def __init__(self,
            theme_service: ThemeService,
            linkage_service: LinkageService,
            citation_service: CitationService,
            theme_synthesis_service: ThemeSynthesisService,
        ) -> None:
        '''
        Initialize the LinkCitationToTheme event.

        :param theme_service: The theme service dependency.
        :type theme_service: ThemeService
        :param linkage_service: The linkage service dependency.
        :type linkage_service: LinkageService
        :param citation_service: The citation service dependency.
        :type citation_service: CitationService
        :param theme_synthesis_service: Injected synthesizer (DI-swappable).
        :type theme_synthesis_service: ThemeSynthesisService
        '''

        # Set all injected dependencies.
        self.theme_service = theme_service
        self.linkage_service = linkage_service
        self.citation_service = citation_service
        self.theme_synthesis_service = theme_synthesis_service

    # * method: execute
    @DomainEvent.parameters_required(['citation_id', 'theme_id'])
    def execute(self,
            citation_id: str,
            theme_id: str,
            **kwargs,
        ) -> Union[ThemeAggregate, LinkageAggregate]:
        '''
        Link a citation to a theme and refresh the theme synthesis when new.

        :param citation_id: The citation to link.
        :type citation_id: str
        :param theme_id: The theme to link the citation to.
        :type theme_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated theme on a new link, or the existing linkage on
            an idempotent re-link.
        :rtype: Union[ThemeAggregate, LinkageAggregate]
        '''

        # Verify the citation exists.
        citation = self.citation_service.get(citation_id)
        self.verify(
            citation is not None,
            CITATION_NOT_FOUND_ID,
            message=f'Citation not found: {citation_id}.',
            id=citation_id,
        )

        # Verify the theme exists.
        theme = self.theme_service.get(theme_id)
        self.verify(
            theme is not None,
            THEME_NOT_FOUND_ID,
            message=f'Theme not found: {theme_id}.',
            id=theme_id,
        )

        # Idempotent: existing (citation_id, theme_id) returns without re-synth.
        existing = self.linkage_service.list(
            theme_id=theme_id,
            citation_id=citation_id,
        )
        if existing:
            return existing[0]

        # Save the new linkage.
        new_linkage = LinkageAggregate(
            citation_id=citation_id,
            theme_id=theme_id,
        )
        self.linkage_service.save(new_linkage)

        # Load the full linkage set for this theme (not just the new one).
        linkages = self.linkage_service.list(theme_id=theme_id)

        # Resolve citations newest-linkage-first for the synthesizer.
        citations = []
        for linkage in reversed(linkages):
            linked_citation = self.citation_service.get(linkage.citation_id)
            if linked_citation is not None:
                citations.append(linked_citation)

        # Synthesize against the full set and update the theme aggregate.
        description = self.theme_synthesis_service.synthesize(theme, citations)
        theme.update_synthesis(
            synthesized_description=description,
            linkage_count=len(linkages),
        )
        self.theme_service.save(theme)

        # Return the updated theme.
        return theme

# ** event: show_theme
class ShowTheme(ThemeEvent):
    '''
    Display a theme's synthesized description plus each linked citation's
    raw excerpt and source short-reference (no citation-style rendering).
    '''

    # * attribute: linkage_service
    linkage_service: LinkageService

    # * attribute: citation_service
    citation_service: CitationService

    # * attribute: source_service
    source_service: SourceService

    # * init
    def __init__(self,
            theme_service: ThemeService,
            linkage_service: LinkageService,
            citation_service: CitationService,
            source_service: SourceService,
        ) -> None:
        '''
        Initialize the ShowTheme event.

        :param theme_service: The theme service dependency.
        :type theme_service: ThemeService
        :param linkage_service: The linkage service dependency.
        :type linkage_service: LinkageService
        :param citation_service: The citation service dependency.
        :type citation_service: CitationService
        :param source_service: Used to resolve a raw Author (Year) label.
        :type source_service: SourceService
        '''

        # Initialize the shared theme service dependency.
        super().__init__(theme_service)

        # Set the remaining display dependencies.
        self.linkage_service = linkage_service
        self.citation_service = citation_service
        self.source_service = source_service

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> dict:
        '''
        Show a theme and its linked citations.

        :param id: The theme identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: A display dict with the theme synthesis and linked citations.
        :rtype: dict
        '''

        # Retrieve the theme and verify it exists.
        theme = self.theme_service.get(id)
        self.verify(
            theme is not None,
            THEME_NOT_FOUND_ID,
            message=f'Theme not found: {id}.',
            id=id,
        )

        # Load linkages and hydrate each citation with a raw source label.
        linkages = self.linkage_service.list(theme_id=id)
        citations = []
        for linkage in linkages:
            citation = self.citation_service.get(linkage.citation_id)
            if citation is None:
                continue
            source = self.source_service.get(citation.source_id)
            if source is None or not source.authors:
                source_label = citation.source_id
            elif len(source.authors) == 1:
                source_label = f'{source.authors[0]} ({source.year})'
            else:
                source_label = f'{source.authors[0]} et al. ({source.year})'
            citations.append({
                'citation_id': citation.id,
                'source_id': citation.source_id,
                'source': source_label,
                'locator': citation.locator,
                'excerpt': citation.excerpt,
            })

        # Return the theme synthesis plus the linked citation display rows.
        return {
            'id': theme.id,
            'name': theme.name,
            'synthesized_description': theme.synthesized_description,
            'linkage_count': theme.linkage_count,
            'citations': citations,
        }

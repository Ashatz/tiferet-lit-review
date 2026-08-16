"""Lit Review Theme Events"""

# *** imports

# ** core
from typing import List, Optional
from uuid import uuid4

# ** app
from tiferet import DomainEvent

from ..domain.linkage import Linkage
from ..domain.theme import Theme, slugify_theme_name
from ..interfaces.citation import CitationService
from ..interfaces.linkage import LinkageService
from ..interfaces.synthesis import ThemeSynthesisService
from ..interfaces.theme import ThemeService
from ..mappers.linkage import LinkageAggregate
from ..mappers.theme import ThemeAggregate, ThemeResponse
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
    def execute(self, name: str, **kwargs) -> Theme:
        '''
        Add a new theme.

        :param name: The short label for the theme.
        :type name: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The created theme.
        :rtype: Theme
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
    def execute(self, id: str, **kwargs) -> Theme:
        '''
        Retrieve a theme by ID.

        :param id: The theme identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The theme.
        :rtype: Theme
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
    def execute(self, name: Optional[str] = None, **kwargs) -> List[Theme]:
        '''
        List themes, optionally filtered by name.

        :param name: Optional theme name to match exactly.
        :type name: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The matching themes.
        :rtype: List[Theme]
        '''

        # Return themes from the service, applying the optional name filter.
        return self.theme_service.list(name=name)

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
    def execute(self, theme_id: str, **kwargs) -> List[Linkage]:
        '''
        List all linkages for a theme.

        :param theme_id: The theme identifier to filter linkages by.
        :type theme_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The linkages belonging to the theme, in insertion order.
        :rtype: List[Linkage]
        '''

        # Return the linkages filtered by theme_id.
        return self.linkage_service.list(theme_id=theme_id)

# ** event: link_citation_to_theme
class LinkCitationToTheme(DomainEvent):
    '''
    Attach a citation to a theme as a structural fact.

    Default linking creates the linkage and increments linkage_count without
    rewriting synthesized_description. Synthesis runs only when
    include_synthesis is true. An existing (citation_id, theme_id) pair is
    idempotent and returns the current theme unchanged.
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
            include_synthesis: bool = False,
            **kwargs,
        ) -> Theme:
        '''
        Link a citation to a theme; synthesize only when opted in.

        :param citation_id: The citation to link.
        :type citation_id: str
        :param theme_id: The theme to link the citation to.
        :type theme_id: str
        :param include_synthesis: When True, re-synthesize from the full
            linkage set after creating the linkage. Defaults to False.
        :type include_synthesis: bool
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The theme after linking (unchanged on an idempotent re-link).
        :rtype: Theme
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

        # Idempotent: existing (citation_id, theme_id) returns unchanged.
        existing = self.linkage_service.list(
            theme_id=theme_id,
            citation_id=citation_id,
        )
        if existing:
            return theme

        # Save the new linkage as a structural fact.
        new_linkage = LinkageAggregate(
            citation_id=citation_id,
            theme_id=theme_id,
        )
        self.linkage_service.save(new_linkage)

        # Increment the denormalized linkage count without touching synthesis.
        theme.set_attribute('linkage_count', theme.linkage_count + 1)

        # Opt-in: reload the full citation set and rewrite the description.
        if include_synthesis:
            linkages = self.linkage_service.list(theme_id=theme_id)
            citations = []
            for linkage in reversed(linkages):
                linked_citation = self.citation_service.get(linkage.citation_id)
                if linked_citation is not None:
                    citations.append(linked_citation)
            description = self.theme_synthesis_service.synthesize(
                theme,
                citations,
            )
            theme.set_attribute('synthesized_description', description)

        # Persist the updated theme aggregate.
        self.theme_service.save(theme)

        # Return the updated theme.
        return theme

# ** event: show_theme
class ShowTheme(ThemeEvent):
    '''
    Display a theme's synthesized description plus each linked citation.
    '''

    # * attribute: linkage_service
    linkage_service: LinkageService

    # * attribute: citation_service
    citation_service: CitationService

    # * init
    def __init__(self,
            theme_service: ThemeService,
            linkage_service: LinkageService,
            citation_service: CitationService,
        ) -> None:
        '''
        Initialize the ShowTheme event.

        :param theme_service: The theme service dependency.
        :type theme_service: ThemeService
        :param linkage_service: The linkage service dependency.
        :type linkage_service: LinkageService
        :param citation_service: The citation service dependency.
        :type citation_service: CitationService
        '''

        # Initialize the shared theme service dependency.
        super().__init__(theme_service)

        # Set the remaining show dependencies.
        self.linkage_service = linkage_service
        self.citation_service = citation_service

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> Theme:
        '''
        Show a theme and its linked citations.

        :param id: The theme identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The theme response, including linked citations.
        :rtype: Theme
        '''

        # Retrieve the theme and verify it exists.
        theme = self.theme_service.get(id)
        self.verify(
            theme is not None,
            THEME_NOT_FOUND_ID,
            message=f'Theme not found: {id}.',
            id=id,
        )

        # Load each linked citation aggregate in linkage order.
        citations = []
        for linkage in self.linkage_service.list(theme_id=id):
            citation = self.citation_service.get(linkage.citation_id)
            if citation is not None:
                citations.append(citation)

        # Map the theme aggregate into a response that includes the citations.
        return ThemeResponse.from_aggregate(theme, citations=citations)

# ** event: update_theme
class UpdateTheme(ThemeEvent):
    '''
    Apply an editorial write to a theme's name and/or synthesized description.

    Lets a researcher curate narrative text without requiring citations or
    invoking the synthesizer.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self,
            id: str,
            name: Optional[str] = None,
            synthesized_description: Optional[str] = None,
            description: Optional[str] = None,
            **kwargs,
        ) -> Theme:
        '''
        Update a theme's name and/or synthesized description.

        :param id: The theme identifier.
        :type id: str
        :param name: The updated theme name, if provided.
        :type name: Optional[str]
        :param synthesized_description: The updated synthesis text, if provided.
        :type synthesized_description: Optional[str]
        :param description: CLI alias for synthesized_description (``-d``).
        :type description: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated theme.
        :rtype: Theme
        '''

        # Retrieve the theme and verify it exists.
        theme = self.theme_service.get(id)
        self.verify(
            theme is not None,
            THEME_NOT_FOUND_ID,
            message=f'Theme not found: {id}.',
            id=id,
        )

        # Apply an editorial name write when provided.
        if name is not None:
            theme.set_attribute('name', name)

        # Prefer the event-level name; fall back to the CLI description alias.
        next_description = (
            synthesized_description
            if synthesized_description is not None
            else description
        )

        # Apply an editorial description write when provided.
        if next_description is not None:
            theme.set_attribute('synthesized_description', next_description)

        # Persist the updated theme aggregate.
        self.theme_service.save(theme)

        # Return the updated theme.
        return theme

# ** event: resynthesize_theme
class ResynthesizeTheme(DomainEvent):
    '''
    Rebuild a theme's synthesized description from its current linkage set.

    Synthesis is an explicit editorial/computational act, not a side effect of
    forming a linkage.
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
        Initialize the ResynthesizeTheme event.

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
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> Theme:
        '''
        Re-synthesize a theme from all currently linked citations.

        :param id: The theme identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The theme after synthesis.
        :rtype: Theme
        '''

        # Retrieve the theme and verify it exists.
        theme = self.theme_service.get(id)
        self.verify(
            theme is not None,
            THEME_NOT_FOUND_ID,
            message=f'Theme not found: {id}.',
            id=id,
        )

        # Load linkages and resolve each citation, newest-linkage-first.
        linkages = self.linkage_service.list(theme_id=id)
        citations = []
        for linkage in reversed(linkages):
            citation = self.citation_service.get(linkage.citation_id)
            if citation is not None:
                citations.append(citation)

        # Run the injected synthesizer and write the description.
        description = self.theme_synthesis_service.synthesize(theme, citations)
        theme.set_attribute('synthesized_description', description)
        self.theme_service.save(theme)

        # Return the updated theme.
        return theme

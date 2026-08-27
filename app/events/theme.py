"""Lit Review Theme Events"""

# *** imports

# ** core
from typing import List, Optional
from uuid import uuid4

# ** app
from tiferet import DomainEvent

from ..domain.citation import Citation
from ..domain.linkage import Linkage
from ..domain.theme import Theme, slugify_theme_name
from ..interfaces.citation import CitationService
from ..interfaces.linkage import LinkageService
from ..interfaces.synthesis import ThemeSynthesisService
from ..interfaces.theme import ThemeService
from ..mappers.linkage import LinkageAggregate
from ..mappers.theme import RetiredCitationView, ThemeAggregate, ThemeResponse
from .citation import CITATION_NOT_FOUND_ID

# *** constants

# ** constant: theme_not_found_id
THEME_NOT_FOUND_ID = 'THEME_NOT_FOUND'

# ** constant: linkage_not_found_id
LINKAGE_NOT_FOUND_ID = 'LINKAGE_NOT_FOUND'

# *** functions

# ** function: load_active_citations
def load_active_citations(
        linkage_service: LinkageService,
        citation_service: CitationService,
        theme_id: str,
    ) -> List[Citation]:
    '''
    Load the citations for a theme's active linkages, newest-linkage-first.

    Shared by LinkCitationToTheme's opt-in synthesis path and
    ResynthesizeTheme so both feed the synthesizer the identical set; a
    retired linkage's excerpt never reaches either path (RFP-7).

    :param linkage_service: The linkage service dependency.
    :type linkage_service: LinkageService
    :param citation_service: The citation service dependency.
    :type citation_service: CitationService
    :param theme_id: The theme identifier whose active linkages to load.
    :type theme_id: str
    :return: The active linkages' citations, newest-linkage-first.
    :rtype: List[Citation]
    '''

    # Load every linkage for the theme, newest first.
    linkages = linkage_service.list(theme_id=theme_id)
    citations = []
    for linkage in reversed(linkages):

        # Skip retired linkages; only active evidence feeds synthesis.
        if not linkage.is_active():
            continue

        citation = citation_service.get(linkage.citation_id)
        if citation is not None:
            citations.append(citation)

    # Return the active-only citation set.
    return citations

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
            retired_linkage_count=0,
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
    include_synthesis is true, and reads active linkages only (RFP-7). An
    existing (citation_id, theme_id) pair does not create a second linkage or
    change the counts, but an opt-in include_synthesis request still runs
    against the current active set so this path agrees with a standalone
    synthesize.
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
        :param include_synthesis: When True, re-synthesize from the active
            linkage set after creating (or confirming) the linkage. Defaults
            to False.
        :type include_synthesis: bool
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The theme after linking (unchanged on an idempotent re-link,
            except for synthesized_description when include_synthesis=True).
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

        # Idempotent: existing (citation_id, theme_id) returns unchanged,
        # except an opt-in synthesis request still runs over the current
        # active set so the link and standalone synthesize paths agree.
        existing = self.linkage_service.list(
            theme_id=theme_id,
            citation_id=citation_id,
        )
        if existing:
            if include_synthesis:
                citations = load_active_citations(
                    self.linkage_service,
                    self.citation_service,
                    theme_id,
                )
                description = self.theme_synthesis_service.synthesize(theme, citations)
                theme.set_attribute('synthesized_description', description)
                self.theme_service.save(theme)
            return theme

        # Save the new linkage as a structural fact.
        new_linkage = LinkageAggregate(
            citation_id=citation_id,
            theme_id=theme_id,
        )
        self.linkage_service.save(new_linkage)

        # Increment the active linkage count; a new linkage is always active.
        theme.set_attribute('linkage_count', theme.linkage_count + 1)

        # Opt-in: reload the active citation set and rewrite the description.
        if include_synthesis:
            citations = load_active_citations(
                self.linkage_service,
                self.citation_service,
                theme_id,
            )
            description = self.theme_synthesis_service.synthesize(
                theme,
                citations,
            )
            theme.set_attribute('synthesized_description', description)

        # Persist the updated theme aggregate.
        self.theme_service.save(theme)

        # Return the updated theme.
        return theme

# ** event: retire_linkage
class RetireLinkage(DomainEvent):
    '''
    Retire the linkage between a citation and a theme.

    Retirement is state, not deletion: a retired linkage is excluded from
    synthesis and the default show view but keeps resolving to its citation
    and source. Idempotent: retiring an already-retired linkage neither
    restamps retired_at nor raises.
    '''

    # * attribute: theme_service
    theme_service: ThemeService

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
        Initialize the RetireLinkage event.

        :param theme_service: The theme service dependency.
        :type theme_service: ThemeService
        :param linkage_service: The linkage service dependency.
        :type linkage_service: LinkageService
        :param citation_service: The citation service dependency.
        :type citation_service: CitationService
        '''

        # Set all injected dependencies.
        self.theme_service = theme_service
        self.linkage_service = linkage_service
        self.citation_service = citation_service

    # * method: execute
    @DomainEvent.parameters_required(['citation_id', 'theme_id'])
    def execute(self,
            citation_id: str,
            theme_id: str,
            reason: Optional[str] = None,
            **kwargs,
        ) -> Linkage:
        '''
        Retire the linkage between a citation and a theme.

        :param citation_id: The linked citation identifier.
        :type citation_id: str
        :param theme_id: The linked theme identifier.
        :type theme_id: str
        :param reason: Optional free-text reason for the retirement.
        :type reason: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The linkage after retirement (unchanged if already retired).
        :rtype: Linkage
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

        # Verify a linkage exists between them.
        matches = self.linkage_service.list(theme_id=theme_id, citation_id=citation_id)
        self.verify(
            bool(matches),
            LINKAGE_NOT_FOUND_ID,
            message=f'Linkage not found between citation {citation_id} and theme {theme_id}.',
            citation_id=citation_id,
            theme_id=theme_id,
        )
        linkage = matches[0]

        # Idempotent: an already-retired linkage is returned unchanged.
        retired = linkage.retire(reason=reason)
        if not retired:
            return linkage

        # Persist the retired linkage.
        self.linkage_service.save(linkage)

        # Move the denormalized count from active to retired.
        theme.set_attribute('linkage_count', theme.linkage_count - 1)
        theme.set_attribute('retired_linkage_count', theme.retired_linkage_count + 1)
        self.theme_service.save(theme)

        # Return the retired linkage.
        return linkage

# ** event: reinstate_linkage
class ReinstateLinkage(DomainEvent):
    '''
    Reinstate a retired linkage between a citation and a theme.

    Retirement is an editorial judgment, not a correction, so it is always
    reversible. Idempotent: reinstating an already-active linkage neither
    raises nor changes the counts.
    '''

    # * attribute: theme_service
    theme_service: ThemeService

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
        Initialize the ReinstateLinkage event.

        :param theme_service: The theme service dependency.
        :type theme_service: ThemeService
        :param linkage_service: The linkage service dependency.
        :type linkage_service: LinkageService
        :param citation_service: The citation service dependency.
        :type citation_service: CitationService
        '''

        # Set all injected dependencies.
        self.theme_service = theme_service
        self.linkage_service = linkage_service
        self.citation_service = citation_service

    # * method: execute
    @DomainEvent.parameters_required(['citation_id', 'theme_id'])
    def execute(self, citation_id: str, theme_id: str, **kwargs) -> Linkage:
        '''
        Reinstate the linkage between a citation and a theme.

        :param citation_id: The linked citation identifier.
        :type citation_id: str
        :param theme_id: The linked theme identifier.
        :type theme_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The linkage after reinstatement (unchanged if already active).
        :rtype: Linkage
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

        # Verify a linkage exists between them.
        matches = self.linkage_service.list(theme_id=theme_id, citation_id=citation_id)
        self.verify(
            bool(matches),
            LINKAGE_NOT_FOUND_ID,
            message=f'Linkage not found between citation {citation_id} and theme {theme_id}.',
            citation_id=citation_id,
            theme_id=theme_id,
        )
        linkage = matches[0]

        # Idempotent: an already-active linkage is returned unchanged.
        reinstated = linkage.reinstate()
        if not reinstated:
            return linkage

        # Persist the reinstated linkage.
        self.linkage_service.save(linkage)

        # Move the denormalized count from retired back to active.
        theme.set_attribute('linkage_count', theme.linkage_count + 1)
        theme.set_attribute('retired_linkage_count', theme.retired_linkage_count - 1)
        self.theme_service.save(theme)

        # Return the reinstated linkage.
        return linkage

# ** event: show_theme
class ShowTheme(ThemeEvent):
    '''
    Display a theme's synthesized description plus its active linkages.

    Retired linkages are excluded from the default view; pass
    include_retired=True to also list them, each marked with its retirement
    timestamp and reason.
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
    def execute(self, id: str, include_retired: bool = False, **kwargs) -> Theme:
        '''
        Show a theme, its active linkages, and optionally its retired ones.

        :param id: The theme identifier.
        :type id: str
        :param include_retired: When True, also list retired linkages with
            their retirement timestamp and reason. Defaults to False.
        :type include_retired: bool
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

        # Split linked citations into active and (optionally) retired views.
        citations = []
        retired_citations = [] if include_retired else None
        for linkage in self.linkage_service.list(theme_id=id):
            if linkage.is_active():
                citation = self.citation_service.get(linkage.citation_id)
                if citation is not None:
                    citations.append(citation)
            elif include_retired:
                citation = self.citation_service.get(linkage.citation_id)
                if citation is not None:
                    retired_citations.append(
                        RetiredCitationView.from_citation_and_linkage(citation, linkage)
                    )

        # Map the theme aggregate into a response with the split citations.
        return ThemeResponse.from_aggregate(
            theme,
            citations=citations,
            retired_citations=retired_citations,
        )

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
    Rebuild a theme's synthesized description from its active linkage set.

    Synthesis is an explicit editorial/computational act, not a side effect of
    forming a linkage. A retired linkage's excerpt never reaches the
    synthesizer (RFP-7).
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
        Re-synthesize a theme from its active linkage set.

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

        # Load the active linkages' citations, newest-linkage-first.
        citations = load_active_citations(self.linkage_service, self.citation_service, id)

        # Run the injected synthesizer and write the description.
        description = self.theme_synthesis_service.synthesize(theme, citations)
        theme.set_attribute('synthesized_description', description)
        self.theme_service.save(theme)

        # Return the updated theme.
        return theme

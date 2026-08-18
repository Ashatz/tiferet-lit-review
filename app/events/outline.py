"""Lit Review Outline Events"""

# *** imports

# ** core
from typing import List, Optional

# ** app
from tiferet import DomainEvent

from ..domain.outline import Outline
from ..domain.theme import Theme
from ..interfaces.citation import CitationService
from ..interfaces.citation_style import CitationStyleRuleService
from ..interfaces.linkage import LinkageService
from ..interfaces.outline import OutlineService
from ..interfaces.source import SourceService
from ..interfaces.theme import ThemeService
from ..mappers.outline import OutlineAggregate, OutlineResponse
from .citation_style import CITATION_STYLE_NOT_FOUND_ID, RenderCitation
from .theme import THEME_NOT_FOUND_ID

# *** constants

# ** constant: outline_not_found_id
OUTLINE_NOT_FOUND_ID = 'OUTLINE_NOT_FOUND'

# *** events

# ** event: outline_event
class OutlineEvent(DomainEvent):
    '''
    Base event providing the shared OutlineService dependency.
    '''

    # * attribute: outline_service
    outline_service: OutlineService

    # * init
    def __init__(self, outline_service: OutlineService) -> None:
        '''
        Initialize the OutlineEvent.

        :param outline_service: The outline service dependency.
        :type outline_service: OutlineService
        '''

        # Set the outline service dependency.
        self.outline_service = outline_service

# ** event: assemble_outline
class AssembleOutline(DomainEvent):
    '''
    Name a new Outline and optionally place an initial ordered slot list.

    Arrangement is a researcher or agent act, not a synthesis service.
    Themes may be omitted at create and added later via AddOutlineSlot.
    Re-running assemble always produces a new Outline. Style is accepted
    for CLI compatibility and is not required to persist slots.
    '''

    # * attribute: outline_service
    outline_service: OutlineService

    # * attribute: theme_service
    theme_service: ThemeService

    # * init
    def __init__(self,
            outline_service: OutlineService,
            theme_service: ThemeService,
        ) -> None:
        '''
        Initialize the AssembleOutline event.

        :param outline_service: The outline service dependency.
        :type outline_service: OutlineService
        :param theme_service: The theme service dependency.
        :type theme_service: ThemeService
        '''

        # Set all injected dependencies.
        self.outline_service = outline_service
        self.theme_service = theme_service

    # * method: execute
    @DomainEvent.parameters_required(['title'])
    def execute(self,
            title: str,
            theme_ids: Optional[List[str]] = None,
            style_id: Optional[str] = None,
            **kwargs,
        ) -> Outline:
        '''
        Assemble a new outline, optionally from an ordered theme list.

        :param title: The short label for this arrangement.
        :type title: str
        :param theme_ids: Optional theme identifiers in slot order.
        :type theme_ids: Optional[List[str]]
        :param style_id: Optional style identifier; unused for persist.
        :type style_id: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The created outline.
        :rtype: Outline
        '''

        # Default to an empty arrangement when no initial themes are supplied.
        theme_ids = theme_ids or []

        # Verify every theme exists before writing any outline.
        for theme_id in theme_ids:
            theme = self.theme_service.get(theme_id)
            self.verify(
                theme is not None,
                THEME_NOT_FOUND_ID,
                message=f'Theme not found: {theme_id}.',
                id=theme_id,
            )

        # Create the outline and own each slot in the supplied order.
        new_outline = OutlineAggregate(title=title)
        for theme_id in theme_ids:
            new_outline.add_slot(theme_id)
        self.outline_service.save(new_outline)

        # Return the newly assembled outline.
        return new_outline

# ** event: add_outline_slot
class AddOutlineSlot(DomainEvent):
    '''
    Append a theme to an existing Outline as a structural fact.

    An already-slotted theme_id is idempotent and returns the current
    outline unchanged. This is not a synthesis step.
    '''

    # * attribute: outline_service
    outline_service: OutlineService

    # * attribute: theme_service
    theme_service: ThemeService

    # * init
    def __init__(self,
            outline_service: OutlineService,
            theme_service: ThemeService,
        ) -> None:
        '''
        Initialize the AddOutlineSlot event.

        :param outline_service: The outline service dependency.
        :type outline_service: OutlineService
        :param theme_service: The theme service dependency.
        :type theme_service: ThemeService
        '''

        # Set all injected dependencies.
        self.outline_service = outline_service
        self.theme_service = theme_service

    # * method: execute
    @DomainEvent.parameters_required(['id', 'theme_id'])
    def execute(self, id: str, theme_id: str, **kwargs) -> Outline:
        '''
        Add a theme slot to an existing outline.

        :param id: The outline identifier.
        :type id: str
        :param theme_id: The theme to place in the next slot.
        :type theme_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The outline after adding (unchanged on an idempotent re-add).
        :rtype: Outline
        '''

        # Verify the outline exists.
        outline = self.outline_service.get(id)
        self.verify(
            outline is not None,
            OUTLINE_NOT_FOUND_ID,
            message=f'Outline not found: {id}.',
            id=id,
        )

        # Verify the theme exists before forming the slot.
        theme = self.theme_service.get(theme_id)
        self.verify(
            theme is not None,
            THEME_NOT_FOUND_ID,
            message=f'Theme not found: {theme_id}.',
            id=theme_id,
        )

        # Idempotent: an already-slotted theme returns the outline unchanged.
        added = outline.add_slot(theme_id)
        if not added:
            return outline

        # Persist the updated outline aggregate.
        self.outline_service.save(outline)

        # Return the updated outline.
        return outline

# ** event: get_outline
class GetOutline(OutlineEvent):
    '''
    Retrieve an Outline by its ID.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> Outline:
        '''
        Retrieve an outline by ID.

        :param id: The outline identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The outline.
        :rtype: Outline
        '''

        # Retrieve the outline from the service.
        outline = self.outline_service.get(id)

        # Verify the outline exists.
        self.verify(
            outline is not None,
            OUTLINE_NOT_FOUND_ID,
            message=f'Outline not found: {id}.',
            id=id,
        )

        # Return the outline.
        return outline

# ** event: list_outlines
class ListOutlines(OutlineEvent):
    '''
    List all outlines.
    '''

    # * method: execute
    def execute(self,
            title: Optional[str] = None,
            theme_id: Optional[str] = None,
            **kwargs,
        ) -> List[Outline]:
        '''
        List outlines, optionally filtered by title or included theme.

        :param title: Optional outline title to match exactly.
        :type title: Optional[str]
        :param theme_id: Optional theme identifier included in a slot.
        :type theme_id: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The matching outlines.
        :rtype: List[Outline]
        '''

        # Return outlines from the service, applying the optional filters.
        return self.outline_service.list(title=title, theme_id=theme_id)

# ** event: show_outline
class ShowOutline(OutlineEvent):
    '''
    Display an outline's slots plus each arranged theme.

    Optional style_id adds a live citation preview via RenderCitation.
    Theme names and order are always required; preview is optional.
    '''

    # * attribute: theme_service
    theme_service: ThemeService

    # * attribute: linkage_service
    linkage_service: LinkageService

    # * attribute: citation_service
    citation_service: CitationService

    # * attribute: source_service
    source_service: SourceService

    # * attribute: citation_style_service
    citation_style_service: CitationStyleRuleService

    # * init
    def __init__(self,
            outline_service: OutlineService,
            theme_service: ThemeService,
            linkage_service: LinkageService,
            citation_service: CitationService,
            source_service: SourceService,
            citation_style_service: CitationStyleRuleService,
        ) -> None:
        '''
        Initialize the ShowOutline event.

        :param outline_service: The outline service dependency.
        :type outline_service: OutlineService
        :param theme_service: The theme service dependency.
        :type theme_service: ThemeService
        :param linkage_service: The linkage service dependency.
        :type linkage_service: LinkageService
        :param citation_service: The citation service dependency.
        :type citation_service: CitationService
        :param source_service: The source service dependency.
        :type source_service: SourceService
        :param citation_style_service: The citation style rule service.
        :type citation_style_service: CitationStyleRuleService
        '''

        # Initialize the shared outline service dependency.
        super().__init__(outline_service)

        # Set the remaining show dependencies.
        self.theme_service = theme_service
        self.linkage_service = linkage_service
        self.citation_service = citation_service
        self.source_service = source_service
        self.citation_style_service = citation_style_service

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self,
            id: str,
            style_id: Optional[str] = None,
            **kwargs,
        ) -> Outline:
        '''
        Show an outline and its arranged themes.

        :param id: The outline identifier.
        :type id: str
        :param style_id: Optional citation style for live preview renderings.
        :type style_id: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The outline response, including arranged themes.
        :rtype: Outline
        '''

        # Retrieve the outline and verify it exists.
        outline = self.outline_service.get(id)
        self.verify(
            outline is not None,
            OUTLINE_NOT_FOUND_ID,
            message=f'Outline not found: {id}.',
            id=id,
        )

        # Resolve each owned slot from the loaded aggregate.
        themes = self._load_slotted_themes(outline)

        # Optionally preview linked citations through the existing render event.
        citation_previews = []
        if style_id:
            citation_previews = self._preview_citations(themes, style_id)

        # Map the outline aggregate into a response that includes the themes.
        return OutlineResponse.from_aggregate(
            outline,
            themes=themes,
            citation_previews=citation_previews,
        )

    # * method: _load_slotted_themes
    def _load_slotted_themes(self, outline: OutlineAggregate) -> List[Theme]:
        '''
        Resolve every Theme currently slotted on the outline.

        :param outline: The outline whose owned slots to resolve.
        :type outline: OutlineAggregate
        :return: The slotted themes in assembly order.
        :rtype: List[Theme]
        '''

        # Resolve each owned slot, skipping any theme that can no longer be loaded.
        themes = []
        for slot in outline.slots:
            theme = self.theme_service.get(slot.theme_id)
            if theme is not None:
                themes.append(theme)

        # Return the full set in slot order.
        return themes

    # * method: _preview_citations
    def _preview_citations(self,
            themes: List[Theme],
            style_id: str,
        ) -> list:
        '''
        Render citations linked to the slotted themes in the given style.

        :param themes: The slotted themes in assembly order.
        :type themes: List[Theme]
        :param style_id: The citation style identifier.
        :type style_id: str
        :return: Rendered citation responses in slot-then-linkage order.
        :rtype: list
        '''

        # Fail once if the requested style is unknown.
        rule = self.citation_style_service.get_rule(style_id)
        self.verify(
            rule is not None,
            CITATION_STYLE_NOT_FOUND_ID,
            message=f'Citation style not found: {style_id}.',
            id=style_id,
        )

        # Render each linked citation through the existing render event.
        previews = []
        render_dependencies = {
            'citation_service': self.citation_service,
            'source_service': self.source_service,
            'citation_style_service': self.citation_style_service,
        }
        for theme in themes:
            for linkage in self.linkage_service.list(theme_id=theme.id):
                previews.append(DomainEvent.handle(
                    RenderCitation,
                    dependencies=render_dependencies,
                    citation_id=linkage.citation_id,
                    style_id=style_id,
                ))

        # Return the optional preview payload.
        return previews

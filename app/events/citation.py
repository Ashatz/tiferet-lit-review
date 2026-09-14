"""Lit Review Citation Events"""

# *** imports

# ** core
from typing import Callable, List, Optional

# ** app
from tiferet import DomainEvent
from tiferet.assets.error import COMMAND_PARAMETER_REQUIRED_ID

from ..domain.activity import CITATION_ADDED_ACTION, CITATION_SUBJECT_TYPE, CITATION_UPDATED_ACTION
from ..domain.citation import (
    ALLOWED_CITATION_TYPES,
    CITATION_TYPE_DEFAULT,
    CITATION_TYPE_LINK,
    parse_citation_link_pointer,
)
from ..domain.source import is_valid_locator
from ..interfaces.activity import ActivityService
from ..interfaces.citation import CitationService
from ..interfaces.project import ProjectService
from ..interfaces.source import SourceService
from ..mappers.activity import ActivityAggregate
from ..mappers.citation import CitationAggregate
from ..mappers.source import SourceAggregate
from .activity import record_activity
from .source import SOURCE_NOT_FOUND_ID

# *** constants

# ** constant: citation_not_found_id
CITATION_NOT_FOUND_ID = 'CITATION_NOT_FOUND'

# ** constant: invalid_locator_id
INVALID_LOCATOR_ID = 'INVALID_LOCATOR'

# ** constant: citation_link_origin_not_found_id
CITATION_LINK_ORIGIN_NOT_FOUND_ID = 'CITATION_LINK_ORIGIN_NOT_FOUND'

# ** constant: invalid_citation_type_id
INVALID_CITATION_TYPE_ID = 'INVALID_CITATION_TYPE'

# ** constant: invalid_citation_link_pointer_id
INVALID_CITATION_LINK_POINTER_ID = 'INVALID_CITATION_LINK_POINTER'

# ** constant: citation_link_immutable_id
CITATION_LINK_IMMUTABLE_ID = 'CITATION_LINK_IMMUTABLE'

# *** functions

# ** function: normalize_citation_type
def normalize_citation_type(citation_type: Optional[str] = None) -> str:
    '''
    Coerce a missing or blank citation type to default.

    :param citation_type: The requested citation type, if any.
    :type citation_type: Optional[str]
    :return: ``default`` or the stripped requested type.
    :rtype: str
    '''

    # Omit or blank type keeps today's default capture shape.
    if citation_type is None or not str(citation_type).strip():
        return CITATION_TYPE_DEFAULT

    # Return the caller-supplied type for later allow-list checking.
    return str(citation_type).strip()

# ** function: load_origin_citation
def load_origin_citation(
        event: DomainEvent,
        pointer: str,
        project_service: Optional[ProjectService],
        get_project_dependency: Optional[Callable],
    ) -> CitationAggregate:
    '''
    Load the origin default citation named by a live pointer.

    :param event: The calling event, used to raise structured errors.
    :type event: DomainEvent
    :param pointer: The stored ``project_id:citation_id`` excerpt.
    :type pointer: str
    :param project_service: The catalog project service.
    :type project_service: Optional[ProjectService]
    :param get_project_dependency: Factory for a project-scoped get_dependency.
    :type get_project_dependency: Optional[Callable]
    :return: The origin citation aggregate.
    :rtype: CitationAggregate
    '''

    # Reject a malformed pointer before opening any origin store.
    try:
        origin_project_id, origin_citation_id = parse_citation_link_pointer(pointer)
    except ValueError:
        event.raise_error(
            INVALID_CITATION_LINK_POINTER_ID,
            message=(
                'A link citation excerpt must be exactly '
                f'project_id:citation_id; got {pointer!r}.'
            ),
            excerpt=pointer,
        )

    # Origin resolve requires the catalog and a project-scoped store getter.
    event.verify(
        project_service is not None and get_project_dependency is not None,
        CITATION_LINK_ORIGIN_NOT_FOUND_ID,
        message=f'Citation link origin not found: {pointer}.',
        pointer=pointer,
    )

    # Origin project must exist in the catalog.
    project = project_service.get(origin_project_id)
    event.verify(
        project is not None,
        CITATION_LINK_ORIGIN_NOT_FOUND_ID,
        message=f'Citation link origin not found: {pointer}.',
        pointer=pointer,
        origin_project_id=origin_project_id,
    )

    # Load the origin citation from that project's store.
    origin_getter = get_project_dependency(project.id, project.h5_file)
    origin_citation_service = origin_getter('citation_service')
    origin = origin_citation_service.get(origin_citation_id)
    event.verify(
        origin is not None and origin.type == CITATION_TYPE_DEFAULT,
        CITATION_LINK_ORIGIN_NOT_FOUND_ID,
        message=f'Citation link origin not found: {pointer}.',
        pointer=pointer,
        origin_project_id=origin_project_id,
        origin_citation_id=origin_citation_id,
    )

    # Return the verified default origin citation.
    return origin

# ** function: citation_for_read
def citation_for_read(
        event: DomainEvent,
        citation: CitationAggregate,
        project_service: Optional[ProjectService] = None,
        get_project_dependency: Optional[Callable] = None,
    ) -> CitationAggregate:
    '''
    Return a display citation with origin excerpt/locator overlaid for links.

    The overlay is not persisted. Local title and context_note stay local.

    :param event: The calling event, used to raise structured errors.
    :type event: DomainEvent
    :param citation: The stored local citation.
    :type citation: CitationAggregate
    :param project_service: The catalog project service.
    :type project_service: Optional[ProjectService]
    :param get_project_dependency: Factory for a project-scoped get_dependency.
    :type get_project_dependency: Optional[Callable]
    :return: The stored citation, or an unsaved origin-resolved copy.
    :rtype: CitationAggregate
    '''

    # Default citations already carry local evidence text.
    if not citation.is_link:
        return citation

    # Overlay origin excerpt and locator without writing them onto the local row.
    origin = load_origin_citation(
        event,
        citation.excerpt,
        project_service,
        get_project_dependency,
    )

    # Origin passage is default-shaped evidence; callers restore type for show.
    return CitationAggregate(
        id=citation.id,
        source_id=origin.source_id,
        locator=origin.locator,
        excerpt=origin.excerpt,
        context_note=citation.context_note,
        title=citation.title,
        type=CITATION_TYPE_DEFAULT,
        created_at=citation.created_at,
    )

# ** function: source_for_read
def source_for_read(
        event: DomainEvent,
        citation: CitationAggregate,
        source_service: SourceService,
        project_service: Optional[ProjectService] = None,
        get_project_dependency: Optional[Callable] = None,
    ) -> SourceAggregate:
    '''
    Resolve the Source used to render or display a citation.

    :param event: The calling event, used to raise structured errors.
    :type event: DomainEvent
    :param citation: The stored local citation.
    :type citation: CitationAggregate
    :param source_service: The current project's source service.
    :type source_service: SourceService
    :param project_service: The catalog project service.
    :type project_service: Optional[ProjectService]
    :param get_project_dependency: Factory for a project-scoped get_dependency.
    :type get_project_dependency: Optional[Callable]
    :return: The local source, or the origin source for a link citation.
    :rtype: SourceAggregate
    '''

    # Default citations resolve Source in the current project store.
    if not citation.is_link:
        source = source_service.get(citation.source_id)
        event.verify(
            source is not None,
            SOURCE_NOT_FOUND_ID,
            message=f'Source not found: {citation.source_id}.',
            id=citation.source_id,
        )
        return source

    # Link citations follow the pointer to the origin project's Source.
    origin = load_origin_citation(
        event,
        citation.excerpt,
        project_service,
        get_project_dependency,
    )
    origin_project_id, _ = parse_citation_link_pointer(citation.excerpt)
    project = project_service.get(origin_project_id)
    origin_getter = get_project_dependency(project.id, project.h5_file)
    origin_source_service = origin_getter('source_service')
    source = origin_source_service.get(origin.source_id)
    event.verify(
        source is not None,
        CITATION_LINK_ORIGIN_NOT_FOUND_ID,
        message=f'Citation link origin not found: {citation.excerpt}.',
        pointer=citation.excerpt,
        origin_source_id=origin.source_id,
    )

    # Return the origin bibliographic record.
    return source

# *** events

# ** event: citation_event
class CitationEvent(DomainEvent):
    '''
    Base event providing the shared CitationService dependency.
    '''

    # * attribute: citation_service
    citation_service: CitationService

    # * init
    def __init__(self, citation_service: CitationService) -> None:
        '''
        Initialize the CitationEvent.

        :param citation_service: The citation service dependency.
        :type citation_service: CitationService
        '''

        # Set the citation service dependency.
        self.citation_service = citation_service

# ** event: add_citation
class AddCitation(CitationEvent):
    '''
    Add a new Citation, verifying its parent source and locator shape.
    '''

    # * attribute: source_service
    source_service: SourceService

    # * attribute: activity_service
    activity_service: ActivityService

    # * init
    def __init__(self,
            citation_service: CitationService,
            source_service: SourceService,
            activity_service: ActivityService,
        ) -> None:
        '''
        Initialize the AddCitation event.

        :param citation_service: The citation service dependency.
        :type citation_service: CitationService
        :param source_service: The source service dependency, used to verify
            the parent source and resolve its locator convention.
        :type source_service: SourceService
        :param activity_service: The activity service dependency.
        :type activity_service: ActivityService
        '''

        # Initialize the shared citation service dependency.
        super().__init__(citation_service)

        # Set the source service dependency.
        self.source_service = source_service

        # Set the activity service dependency.
        self.activity_service = activity_service

    # * method: execute
    @DomainEvent.parameters_required(['excerpt'])
    def execute(self,
            excerpt: str,
            source_id: Optional[str] = None,
            locator: Optional[str] = None,
            context_note: Optional[str] = None,
            title: Optional[str] = None,
            type: Optional[str] = None,
            project_service: Optional[ProjectService] = None,
            get_project_dependency: Optional[Callable] = None,
            **kwargs,
        ) -> CitationAggregate:
        '''
        Add a new citation.

        :param excerpt: Evidence text, or a live ``project_id:citation_id`` pointer.
        :type excerpt: str
        :param source_id: The local source identifier; required for default type.
        :type source_id: Optional[str]
        :param locator: The local locator; required for default type.
        :type locator: Optional[str]
        :param context_note: An optional surrounding-context note.
        :type context_note: Optional[str]
        :param title: An optional researcher-authored label for this citation.
        :type title: Optional[str]
        :param type: Citation type; omit or ``default`` keeps local capture.
        :type type: Optional[str]
        :param project_service: The catalog project service, used for link origins.
        :type project_service: Optional[ProjectService]
        :param get_project_dependency: Factory for a project-scoped get_dependency.
        :type get_project_dependency: Optional[Callable]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The created citation aggregate.
        :rtype: CitationAggregate
        '''

        # Classify the capture shape; unknown types are rejected before save.
        citation_type = normalize_citation_type(type)
        self.verify(
            citation_type in ALLOWED_CITATION_TYPES,
            INVALID_CITATION_TYPE_ID,
            message=(
                f'Unknown citation type {citation_type!r}; '
                f'allowed values are {ALLOWED_CITATION_TYPES}.'
            ),
            type=citation_type,
        )

        # A link citation stores a live pointer and does not require local source.
        if citation_type == CITATION_TYPE_LINK:
            load_origin_citation(
                self,
                excerpt,
                project_service,
                get_project_dependency,
            )
            new_citation = CitationAggregate(
                excerpt=excerpt,
                context_note=context_note,
                title=title,
                type=CITATION_TYPE_LINK,
            )
            self.citation_service.save(new_citation)
            record_activity(self.activity_service, ActivityAggregate(
                action=CITATION_ADDED_ACTION,
                subject_type=CITATION_SUBJECT_TYPE,
                subject_id=new_citation.id,
                changed_fields=['type'],
            ))
            return new_citation

        # Default capture still requires a local source, locator, and excerpt.
        self.verify(
            isinstance(source_id, str) and bool(source_id.strip()),
            COMMAND_PARAMETER_REQUIRED_ID,
            message='The required parameter source_id is missing.',
            parameter='source_id',
        )
        self.verify(
            isinstance(locator, str) and bool(locator.strip()),
            COMMAND_PARAMETER_REQUIRED_ID,
            message='The required parameter locator is missing.',
            parameter='locator',
        )

        # Verify the parent source exists.
        source = self.source_service.get(source_id)
        self.verify(
            source is not None,
            SOURCE_NOT_FOUND_ID,
            message=f'Source not found: {source_id}.',
            id=source_id,
        )

        # Verify the locator shape matches the source's locator convention.
        self.verify(
            is_valid_locator(source.locator_convention, locator),
            INVALID_LOCATOR_ID,
            message=f'Invalid locator {locator!r} for convention {source.locator_convention!r}.',
            locator=locator,
            locator_convention=source.locator_convention,
        )

        # Create and save the citation aggregate; the Citation title
        # validator normalizes blank input and rejects an overlong title.
        new_citation = CitationAggregate(
            source_id=source_id,
            locator=locator,
            excerpt=excerpt,
            context_note=context_note,
            title=title,
            type=CITATION_TYPE_DEFAULT,
        )
        self.citation_service.save(new_citation)

        # Best-effort: record the creation; excerpt/context_note/title values
        # are never carried onto the activity entry, only the field names.
        record_activity(self.activity_service, ActivityAggregate(
            action=CITATION_ADDED_ACTION,
            subject_type=CITATION_SUBJECT_TYPE,
            subject_id=new_citation.id,
        ))

        # Return the newly created citation.
        return new_citation

# ** event: get_citation
class GetCitation(CitationEvent):
    '''
    Retrieve a Citation by its ID.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> CitationAggregate:
        '''
        Retrieve a citation by ID.

        :param id: The citation identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The citation aggregate.
        :rtype: CitationAggregate
        '''

        # Retrieve the citation from the service.
        citation = self.citation_service.get(id)

        # Verify the citation exists.
        self.verify(
            citation is not None,
            CITATION_NOT_FOUND_ID,
            message=f'Citation not found: {id}.',
            id=id,
        )

        # Return the citation.
        return citation

# ** event: show_citation
class ShowCitation(CitationEvent):
    '''
    Display a Citation, resolving a link's origin excerpt, locator, and source.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self,
            id: str,
            project_service: Optional[ProjectService] = None,
            get_project_dependency: Optional[Callable] = None,
            **kwargs,
        ) -> CitationAggregate:
        '''
        Show a citation, overlaying origin evidence for a link without saving.

        :param id: The citation identifier.
        :type id: str
        :param project_service: The catalog project service.
        :type project_service: Optional[ProjectService]
        :param get_project_dependency: Factory for a project-scoped get_dependency.
        :type get_project_dependency: Optional[Callable]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The stored citation, or an unsaved origin-resolved copy.
        :rtype: CitationAggregate
        '''

        # Retrieve the citation and verify it exists.
        citation = self.citation_service.get(id)
        self.verify(
            citation is not None,
            CITATION_NOT_FOUND_ID,
            message=f'Citation not found: {id}.',
            id=id,
        )

        # Overlay origin excerpt and locator for display; do not persist them.
        display = citation_for_read(
            self,
            citation,
            project_service,
            get_project_dependency,
        )
        if not citation.is_link:
            return display

        # Restore type=link so show reports the stored capture shape.
        return CitationAggregate.model_construct(
            id=display.id,
            source_id=display.source_id,
            locator=display.locator,
            excerpt=display.excerpt,
            context_note=display.context_note,
            title=display.title,
            type=CITATION_TYPE_LINK,
            created_at=display.created_at,
        )

# ** event: list_citations_for_source
class ListCitationsForSource(CitationEvent):
    '''
    List citations, optionally filtered by source, without opening origin stores.
    '''

    # * method: execute
    def execute(self, source_id: Optional[str] = None, **kwargs) -> List[CitationAggregate]:
        '''
        List citations, optionally filtered by source_id.

        List stays metadata-light: stored rows including type and pointer
        excerpt, without resolving origin stores.

        :param source_id: Optional source identifier to filter citations by.
        :type source_id: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The matching citations, in insertion order.
        :rtype: List[CitationAggregate]
        '''

        # Apply the optional source_id filter; omit it to list every local row.
        if source_id is not None:
            return self.citation_service.list(source_id=source_id)
        return self.citation_service.list()

# ** event: update_citation
class UpdateCitation(CitationEvent):
    '''
    Update mutable fields on an existing Citation.
    '''

    # * attribute: source_service
    source_service: SourceService

    # * attribute: activity_service
    activity_service: ActivityService

    # * init
    def __init__(self,
            citation_service: CitationService,
            source_service: SourceService,
            activity_service: ActivityService,
        ) -> None:
        '''
        Initialize the UpdateCitation event.

        :param citation_service: The citation service dependency.
        :type citation_service: CitationService
        :param source_service: The source service dependency, used to
            re-validate locator shape against the parent source.
        :type source_service: SourceService
        :param activity_service: The activity service dependency.
        :type activity_service: ActivityService
        '''

        # Initialize the shared citation service dependency.
        super().__init__(citation_service)

        # Set the source service dependency.
        self.source_service = source_service

        # Set the activity service dependency.
        self.activity_service = activity_service

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self,
            id: str,
            locator: Optional[str] = None,
            excerpt: Optional[str] = None,
            context_note: Optional[str] = None,
            title: Optional[str] = None,
            clear_title: bool = False,
            **kwargs,
        ) -> CitationAggregate:
        '''
        Update an existing citation.

        :param id: The citation identifier.
        :type id: str
        :param locator: The updated locator, if provided.
        :type locator: Optional[str]
        :param excerpt: The updated excerpt, if provided.
        :type excerpt: Optional[str]
        :param context_note: The updated context note, if provided.
        :type context_note: Optional[str]
        :param title: The updated title, if provided.
        :type title: Optional[str]
        :param clear_title: When True, clear the title regardless of `title`.
        :type clear_title: bool
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated citation aggregate.
        :rtype: CitationAggregate
        '''

        # Retrieve the citation and verify it exists.
        citation = self.citation_service.get(id)
        self.verify(
            citation is not None,
            CITATION_NOT_FOUND_ID,
            message=f'Citation not found: {id}.',
            id=id,
        )

        # A link may change title/context_note, but not type or the pointer.
        if citation.is_link:
            self.verify(
                locator is None and excerpt is None,
                CITATION_LINK_IMMUTABLE_ID,
                message=(
                    'A link citation cannot retarget its pointer or change '
                    f'type in this slice: {id}.'
                ),
                id=id,
            )

        # Re-validate locator shape against the parent source when changing it.
        if locator is not None:
            source = self.source_service.get(citation.source_id)
            self.verify(
                source is not None,
                SOURCE_NOT_FOUND_ID,
                message=f'Source not found: {citation.source_id}.',
                id=citation.source_id,
            )
            self.verify(
                is_valid_locator(source.locator_convention, locator),
                INVALID_LOCATOR_ID,
                message=(
                    f'Invalid locator {locator!r} for convention '
                    f'{source.locator_convention!r}.'
                ),
                locator=locator,
                locator_convention=source.locator_convention,
            )
            citation.update_locator(locator)

        # Apply optional excerpt and context-note mutations.
        if excerpt is not None:
            citation.update_excerpt(excerpt)
        if context_note is not None:
            citation.update_context_note(context_note=context_note)

        # An explicit clear takes priority over a same-call title replacement;
        # omitting both leaves the existing title untouched.
        if clear_title:
            citation.update_title(clear=True)
        elif title is not None:
            citation.update_title(title=title)

        # Persist the updated citation via id-upsert save.
        self.citation_service.save(citation)

        # Record only the field names this call actually touched; an update
        # call that touched nothing is a no-op and records nothing.
        changed_fields = []
        if locator is not None:
            changed_fields.append('locator')
        if excerpt is not None:
            changed_fields.append('excerpt')
        if context_note is not None:
            changed_fields.append('context_note')
        if clear_title or title is not None:
            changed_fields.append('title')
        if changed_fields:
            record_activity(self.activity_service, ActivityAggregate(
                action=CITATION_UPDATED_ACTION,
                subject_type=CITATION_SUBJECT_TYPE,
                subject_id=citation.id,
                changed_fields=changed_fields,
            ))

        # Return the updated citation.
        return citation

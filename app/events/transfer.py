"""Lit Review Cross-Project Source and Citation Transfer Events"""

# *** imports

# ** core
from typing import Optional

# ** app
from tiferet import DomainEvent

from ..domain.activity import (
    CITATION_COPIED_ACTION,
    CITATION_MOVED_ACTION,
    CITATION_SUBJECT_TYPE,
    PROJECT_RELATED_TYPE,
    SOURCE_COPIED_ACTION,
    SOURCE_MOVED_ACTION,
    SOURCE_SUBJECT_TYPE,
)
from ..interfaces.activity import ActivityService
from ..interfaces.citation import CitationService
from ..interfaces.source import SourceService
from ..mappers.activity import ActivityAggregate
from ..mappers.citation import CitationAggregate
from ..mappers.source import SourceAggregate
from .activity import record_activity
from .citation import CITATION_NOT_FOUND_ID, CitationEvent
from .source import SOURCE_NOT_FOUND_ID, SourceEvent

# *** constants

# ** constant: transfer_same_project_id
TRANSFER_SAME_PROJECT_ID = 'TRANSFER_SAME_PROJECT'

# ** constant: source_already_exists_id
SOURCE_ALREADY_EXISTS_ID = 'SOURCE_ALREADY_EXISTS'

# ** constant: citation_already_exists_id
CITATION_ALREADY_EXISTS_ID = 'CITATION_ALREADY_EXISTS'

# ** constant: source_identity_conflict_id
SOURCE_IDENTITY_CONFLICT_ID = 'SOURCE_IDENTITY_CONFLICT'

# ** constant: source_has_citations_id
SOURCE_HAS_CITATIONS_ID = 'SOURCE_HAS_CITATIONS'

# *** functions

# ** function: clone_source
def clone_source(source: SourceAggregate) -> SourceAggregate:
    '''
    Clone a source aggregate, preserving its identifier and bibliographic attrs.

    :param source: The origin source aggregate.
    :type source: SourceAggregate
    :return: A new aggregate with the same id and bibliographic fields.
    :rtype: SourceAggregate
    '''

    # Reconstruct the source under the same id so transfer never mints a new one.
    clone = SourceAggregate(
        id=source.id,
        medium=source.medium,
        year=source.year,
        title=source.title,
        container_title=source.container_title,
        publisher=source.publisher,
        source_url=source.source_url,
        locator_convention=source.locator_convention,
        document_name=source.document_name,
        overview_note=source.overview_note,
        created_at=source.created_at,
        authors=[],
    )

    # Restore each copied author name through the aggregate lifecycle.
    for author in source.authors:
        clone.add_author(author.display_name)

    # Return the id-preserving clone.
    return clone

# ** function: clone_citation
def clone_citation(citation: CitationAggregate) -> CitationAggregate:
    '''
    Clone a citation aggregate, preserving its identifier and row fields.

    :param citation: The origin citation aggregate.
    :type citation: CitationAggregate
    :return: A new aggregate with the same id and citation fields.
    :rtype: CitationAggregate
    '''

    # Reconstruct the citation under the same id so transfer never mints a new one.
    return CitationAggregate(
        id=citation.id,
        source_id=citation.source_id,
        locator=citation.locator,
        excerpt=citation.excerpt,
        context_note=citation.context_note,
        title=citation.title,
        created_at=citation.created_at,
    )

# ** function: bibliographic_identity_matches
def bibliographic_identity_matches(
        left: SourceAggregate,
        right: SourceAggregate,
    ) -> bool:
    '''
    Compare bibliographic identity used to reuse a destination parent source.

    Identity is medium, authors, year, title, container title, and publisher.

    :param left: The origin source.
    :type left: SourceAggregate
    :param right: The destination source at the same id.
    :type right: SourceAggregate
    :return: True when bibliographic identity matches.
    :rtype: bool
    '''

    # Compare identity fields, including author display names in order.
    return (
        left.medium == right.medium
        and [author.display_name for author in left.authors]
        == [author.display_name for author in right.authors]
        and left.year == right.year
        and left.title == right.title
        and left.container_title == right.container_title
        and left.publisher == right.publisher
    )

# ** function: source_content_matches
def source_content_matches(
        origin: SourceAggregate,
        dest: Optional[SourceAggregate],
        origin_source_service: SourceService,
        dest_source_service: SourceService,
    ) -> bool:
    '''
    Compare transferred source content for dest verification and move retry.

    :param origin: The origin source aggregate.
    :type origin: SourceAggregate
    :param dest: The destination source aggregate, or None if missing.
    :type dest: Optional[SourceAggregate]
    :param origin_source_service: The origin source service.
    :type origin_source_service: SourceService
    :param dest_source_service: The destination source service.
    :type dest_source_service: SourceService
    :return: True when dest holds a matching copy of origin.
    :rtype: bool
    '''

    # A missing dest source is never a complete copy.
    if dest is None:
        return False

    # Identity plus remaining bibliographic attrs must match.
    if not bibliographic_identity_matches(origin, dest):
        return False
    if origin.document_name != dest.document_name:
        return False
    if origin.source_url != dest.source_url:
        return False
    if origin.overview_note != dest.overview_note:
        return False

    # Document array presence and bytes must match origin.
    origin_has_document = origin_source_service.has_document(origin.id)
    dest_has_document = dest_source_service.has_document(dest.id)
    if origin_has_document != dest_has_document:
        return False
    if origin_has_document and (
            origin_source_service.get_document(origin.id)
            != dest_source_service.get_document(dest.id)
        ):
        return False

    # Dest holds a matching source copy.
    return True

# ** function: citation_content_matches
def citation_content_matches(
        origin: CitationAggregate,
        dest: Optional[CitationAggregate],
    ) -> bool:
    '''
    Compare transferred citation row content for dest verification and move retry.

    :param origin: The origin citation aggregate.
    :type origin: CitationAggregate
    :param dest: The destination citation aggregate, or None if missing.
    :type dest: Optional[CitationAggregate]
    :return: True when dest holds a matching copy of origin.
    :rtype: bool
    '''

    # A missing dest citation is never a complete copy.
    if dest is None:
        return False

    # Compare the persisted citation row fields, excluding created_at.
    return (
        dest.id == origin.id
        and dest.source_id == origin.source_id
        and dest.locator == origin.locator
        and dest.excerpt == origin.excerpt
        and dest.context_note == origin.context_note
        and dest.title == origin.title
    )

# ** function: write_source_copy
def write_source_copy(
        origin_source_service: SourceService,
        dest_source_service: SourceService,
        source: SourceAggregate,
    ) -> SourceAggregate:
    '''
    Write a source copy into dest, including the document array when present.

    :param origin_source_service: The origin source service.
    :type origin_source_service: SourceService
    :param dest_source_service: The destination source service.
    :type dest_source_service: SourceService
    :param source: The origin source aggregate to copy.
    :type source: SourceAggregate
    :return: The cloned source written to dest.
    :rtype: SourceAggregate
    '''

    # Persist bibliographic node attrs under the same source id.
    clone = clone_source(source)
    dest_source_service.save(clone)

    # Copy the document array only when origin actually has one.
    if origin_source_service.has_document(source.id):
        dest_source_service.save_document(
            source.id,
            origin_source_service.get_document(source.id),
        )

    # Return the dest clone.
    return clone

# ** function: record_transfer_activity
def record_transfer_activity(
        activity_service: Optional[ActivityService],
        action: str,
        subject_type: str,
        subject_id: str,
        related_project_id: Optional[str] = None,
    ) -> None:
    '''
    Best-effort activity append for a successful copy or move.

    :param activity_service: The activity service for the involved project.
    :type activity_service: Optional[ActivityService]
    :param action: The copy or move action token.
    :type action: str
    :param subject_type: The transferred artifact type.
    :type subject_type: str
    :param subject_id: The transferred artifact identifier.
    :type subject_id: str
    :param related_project_id: The other project id, when cheap to set.
    :type related_project_id: Optional[str]
    '''

    # Skip when the caller did not supply an activity service.
    if activity_service is None:
        return

    # related_type is project only when the other project id is present.
    related_type = PROJECT_RELATED_TYPE if related_project_id else None

    # Best-effort append; a failed record never rolls back the transfer.
    record_activity(activity_service, ActivityAggregate(
        action=action,
        subject_type=subject_type,
        subject_id=subject_id,
        related_type=related_type,
        related_id=related_project_id,
    ))

# ** function: remove_origin_artifact
def remove_origin_artifact(service, artifact_id: str) -> None:
    '''
    Invoke the repository-private origin-only transfer removal helper.

    :param service: The origin repository exposing remove_for_transfer.
    :type service: object
    :param artifact_id: The origin artifact identifier to remove.
    :type artifact_id: str
    '''

    # Origin removal is repository-private and is not a Service API.
    service.remove_for_transfer(artifact_id)

# *** events

# ** event: copy_source
class CopySource(SourceEvent):
    '''
    Copy a Source's bibliographic node, and document when present, into another project.
    '''

    # * attribute: activity_service
    activity_service: ActivityService

    # * init
    def __init__(self, source_service: SourceService, activity_service: ActivityService) -> None:
        '''
        Initialize the CopySource event.

        :param source_service: The origin source service dependency.
        :type source_service: SourceService
        :param activity_service: The origin activity service dependency.
        :type activity_service: ActivityService
        '''

        # Initialize the shared origin source service dependency.
        super().__init__(source_service)

        # Set the origin activity service; dest activity arrives via execute kwargs.
        self.activity_service = activity_service

    # * method: execute
    @DomainEvent.parameters_required([
        'id',
        'dest_project_id',
        'dest_source_service',
    ])
    def execute(self,
            id: str,
            dest_project_id: str,
            dest_source_service: SourceService,
            project_id: Optional[str] = None,
            dest_activity_service: Optional[ActivityService] = None,
            **kwargs,
        ) -> SourceAggregate:
        '''
        Copy a source into the destination project under the same id.

        :param id: The source identifier to copy.
        :type id: str
        :param dest_project_id: The destination project identifier.
        :type dest_project_id: str
        :param dest_source_service: The destination source service.
        :type dest_source_service: SourceService
        :param project_id: The origin project identifier.
        :type project_id: Optional[str]
        :param dest_activity_service: The destination activity service.
        :type dest_activity_service: Optional[ActivityService]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The source aggregate written to dest.
        :rtype: SourceAggregate
        '''

        # Origin and destination must be different projects.
        self.verify(
            project_id != dest_project_id,
            TRANSFER_SAME_PROJECT_ID,
            message='Origin and destination project must be different.',
            origin_project_id=project_id,
            dest_project_id=dest_project_id,
        )

        # Retrieve the origin source and fail as not-found when it is missing.
        origin = self.source_service.get(id)
        self.verify(
            origin is not None,
            SOURCE_NOT_FOUND_ID,
            message=f'Source not found: {id}.',
            id=id,
        )

        # Dest occupancy always fails copy; never mint a new id or overwrite.
        self.verify(
            not dest_source_service.exists(id),
            SOURCE_ALREADY_EXISTS_ID,
            message=f'A source with ID {id} already exists in the destination project.',
            id=id,
        )

        # Write bibliographic attrs and the document array when origin has one.
        copied = write_source_copy(
            self.source_service,
            dest_source_service,
            origin,
        )

        # Dest records source.copied; origin is unchanged so it records nothing.
        record_transfer_activity(
            dest_activity_service,
            SOURCE_COPIED_ACTION,
            SOURCE_SUBJECT_TYPE,
            copied.id,
            related_project_id=project_id,
        )

        # Return the dest source.
        return copied

# ** event: move_source
class MoveSource(SourceEvent):
    '''
    Move a Source by copying it, verifying dest, then removing it from origin only.
    '''

    # * attribute: citation_service
    citation_service: CitationService

    # * attribute: activity_service
    activity_service: ActivityService

    # * init
    def __init__(self,
            source_service: SourceService,
            citation_service: CitationService,
            activity_service: ActivityService,
        ) -> None:
        '''
        Initialize the MoveSource event.

        :param source_service: The origin source service dependency.
        :type source_service: SourceService
        :param citation_service: The origin citation service dependency.
        :type citation_service: CitationService
        :param activity_service: The origin activity service dependency.
        :type activity_service: ActivityService
        '''

        # Initialize the shared origin source service dependency.
        super().__init__(source_service)

        # Set the origin citation service used to refuse orphaning citations.
        self.citation_service = citation_service

        # Set the origin activity service; dest activity arrives via execute kwargs.
        self.activity_service = activity_service

    # * method: execute
    @DomainEvent.parameters_required([
        'id',
        'dest_project_id',
        'dest_source_service',
    ])
    def execute(self,
            id: str,
            dest_project_id: str,
            dest_source_service: SourceService,
            project_id: Optional[str] = None,
            dest_activity_service: Optional[ActivityService] = None,
            **kwargs,
        ) -> SourceAggregate:
        '''
        Move a source into the destination project under the same id.

        :param id: The source identifier to move.
        :type id: str
        :param dest_project_id: The destination project identifier.
        :type dest_project_id: str
        :param dest_source_service: The destination source service.
        :type dest_source_service: SourceService
        :param project_id: The origin project identifier.
        :type project_id: Optional[str]
        :param dest_activity_service: The destination activity service.
        :type dest_activity_service: Optional[ActivityService]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The source aggregate left on dest.
        :rtype: SourceAggregate
        '''

        # Origin and destination must be different projects.
        self.verify(
            project_id != dest_project_id,
            TRANSFER_SAME_PROJECT_ID,
            message='Origin and destination project must be different.',
            origin_project_id=project_id,
            dest_project_id=dest_project_id,
        )

        # Retrieve the origin source and fail as not-found when it is missing.
        origin = self.source_service.get(id)
        self.verify(
            origin is not None,
            SOURCE_NOT_FOUND_ID,
            message=f'Source not found: {id}.',
            id=id,
        )

        # Refuse source move while origin still has citations for this source.
        remaining = self.citation_service.list(source_id=id)
        self.verify(
            len(remaining) == 0,
            SOURCE_HAS_CITATIONS_ID,
            message=f'Cannot move source {id} while citations still reference it.',
            id=id,
        )

        # Copy unless dest already holds matching content from a prior dest write.
        dest = dest_source_service.get(id)
        if dest is None:
            dest = write_source_copy(
                self.source_service,
                dest_source_service,
                origin,
            )
            record_transfer_activity(
                dest_activity_service,
                SOURCE_COPIED_ACTION,
                SOURCE_SUBJECT_TYPE,
                dest.id,
                related_project_id=project_id,
            )
        else:
            self.verify(
                source_content_matches(
                    origin,
                    dest,
                    self.source_service,
                    dest_source_service,
                ),
                SOURCE_ALREADY_EXISTS_ID,
                message=f'A source with ID {id} already exists in the destination project.',
                id=id,
            )

        # Never remove origin before dest verification succeeds.
        dest = dest_source_service.get(id)
        self.verify(
            source_content_matches(
                origin,
                dest,
                self.source_service,
                dest_source_service,
            ),
            SOURCE_ALREADY_EXISTS_ID,
            message=f'Destination source {id} is incomplete.',
            id=id,
        )

        # Origin-only remove is repository-private and is the last step of move.
        remove_origin_artifact(self.source_service, id)

        # Origin records source.moved only after origin remove succeeds.
        record_transfer_activity(
            self.activity_service,
            SOURCE_MOVED_ACTION,
            SOURCE_SUBJECT_TYPE,
            id,
            related_project_id=dest_project_id,
        )

        # Return the dest source.
        return dest

# ** event: copy_citation
class CopyCitation(CitationEvent):
    '''
    Copy a Citation row into another project, auto-copying a missing parent Source.
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
        Initialize the CopyCitation event.

        :param citation_service: The origin citation service dependency.
        :type citation_service: CitationService
        :param source_service: The origin source service dependency.
        :type source_service: SourceService
        :param activity_service: The origin activity service dependency.
        :type activity_service: ActivityService
        '''

        # Initialize the shared origin citation service dependency.
        super().__init__(citation_service)

        # Set the origin source service used to copy a missing parent.
        self.source_service = source_service

        # Set the origin activity service; dest activity arrives via execute kwargs.
        self.activity_service = activity_service

    # * method: execute
    @DomainEvent.parameters_required([
        'id',
        'dest_project_id',
        'dest_citation_service',
        'dest_source_service',
    ])
    def execute(self,
            id: str,
            dest_project_id: str,
            dest_citation_service: CitationService,
            dest_source_service: SourceService,
            project_id: Optional[str] = None,
            dest_activity_service: Optional[ActivityService] = None,
            **kwargs,
        ) -> CitationAggregate:
        '''
        Copy a citation into the destination project under the same id.

        :param id: The citation identifier to copy.
        :type id: str
        :param dest_project_id: The destination project identifier.
        :type dest_project_id: str
        :param dest_citation_service: The destination citation service.
        :type dest_citation_service: CitationService
        :param dest_source_service: The destination source service.
        :type dest_source_service: SourceService
        :param project_id: The origin project identifier.
        :type project_id: Optional[str]
        :param dest_activity_service: The destination activity service.
        :type dest_activity_service: Optional[ActivityService]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The citation aggregate written to dest.
        :rtype: CitationAggregate
        '''

        # Origin and destination must be different projects.
        self.verify(
            project_id != dest_project_id,
            TRANSFER_SAME_PROJECT_ID,
            message='Origin and destination project must be different.',
            origin_project_id=project_id,
            dest_project_id=dest_project_id,
        )

        # Retrieve the origin citation and fail as not-found when it is missing.
        origin = self.citation_service.get(id)
        self.verify(
            origin is not None,
            CITATION_NOT_FOUND_ID,
            message=f'Citation not found: {id}.',
            id=id,
        )

        # Dest citation occupancy always fails copy; never mint a new id.
        self.verify(
            not dest_citation_service.exists(id),
            CITATION_ALREADY_EXISTS_ID,
            message=f'A citation with ID {id} already exists in the destination project.',
            id=id,
        )

        # Ensure dest has the parent source, auto-copying when dest lacks it.
        self._ensure_parent_source(
            origin,
            dest_source_service,
            dest_activity_service,
            project_id,
        )

        # Write the citation row under the same citation id and source_id.
        copied = clone_citation(origin)
        dest_citation_service.save(copied)

        # Dest records citation.copied; the dest citation arrives unlinked.
        record_transfer_activity(
            dest_activity_service,
            CITATION_COPIED_ACTION,
            CITATION_SUBJECT_TYPE,
            copied.id,
            related_project_id=project_id,
        )

        # Return the dest citation.
        return copied

    # * method: _ensure_parent_source
    def _ensure_parent_source(self,
            citation: CitationAggregate,
            dest_source_service: SourceService,
            dest_activity_service: Optional[ActivityService],
            project_id: Optional[str],
        ) -> None:
        '''
        Copy or reuse the parent source on dest according to bibliographic identity.

        :param citation: The origin citation whose parent source is required.
        :type citation: CitationAggregate
        :param dest_source_service: The destination source service.
        :type dest_source_service: SourceService
        :param dest_activity_service: The destination activity service.
        :type dest_activity_service: Optional[ActivityService]
        :param project_id: The origin project identifier.
        :type project_id: Optional[str]
        '''

        # Retrieve the origin parent source; a citation cannot transfer without it.
        parent = self.source_service.get(citation.source_id)
        self.verify(
            parent is not None,
            SOURCE_NOT_FOUND_ID,
            message=f'Source not found: {citation.source_id}.',
            id=citation.source_id,
        )

        # Reuse a dest source at that id only when bibliographic identity matches.
        dest_parent = dest_source_service.get(citation.source_id)
        if dest_parent is not None:
            self.verify(
                bibliographic_identity_matches(parent, dest_parent),
                SOURCE_IDENTITY_CONFLICT_ID,
                message=(
                    f'Destination already has a different source at ID '
                    f'{citation.source_id}.'
                ),
                id=citation.source_id,
            )
            return

        # Dest lacks the parent: copy source and document under the same source id.
        write_source_copy(
            self.source_service,
            dest_source_service,
            parent,
        )
        record_transfer_activity(
            dest_activity_service,
            SOURCE_COPIED_ACTION,
            SOURCE_SUBJECT_TYPE,
            parent.id,
            related_project_id=project_id,
        )

# ** event: move_citation
class MoveCitation(CopyCitation):
    '''
    Move a Citation by copying it, verifying dest, then removing the origin row only.
    '''

    # * method: execute
    @DomainEvent.parameters_required([
        'id',
        'dest_project_id',
        'dest_citation_service',
        'dest_source_service',
    ])
    def execute(self,
            id: str,
            dest_project_id: str,
            dest_citation_service: CitationService,
            dest_source_service: SourceService,
            project_id: Optional[str] = None,
            dest_activity_service: Optional[ActivityService] = None,
            **kwargs,
        ) -> CitationAggregate:
        '''
        Move a citation into the destination project under the same id.

        :param id: The citation identifier to move.
        :type id: str
        :param dest_project_id: The destination project identifier.
        :type dest_project_id: str
        :param dest_citation_service: The destination citation service.
        :type dest_citation_service: CitationService
        :param dest_source_service: The destination source service.
        :type dest_source_service: SourceService
        :param project_id: The origin project identifier.
        :type project_id: Optional[str]
        :param dest_activity_service: The destination activity service.
        :type dest_activity_service: Optional[ActivityService]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The citation aggregate left on dest.
        :rtype: CitationAggregate
        '''

        # Origin and destination must be different projects.
        self.verify(
            project_id != dest_project_id,
            TRANSFER_SAME_PROJECT_ID,
            message='Origin and destination project must be different.',
            origin_project_id=project_id,
            dest_project_id=dest_project_id,
        )

        # Retrieve the origin citation and fail as not-found when it is missing.
        origin = self.citation_service.get(id)
        self.verify(
            origin is not None,
            CITATION_NOT_FOUND_ID,
            message=f'Citation not found: {id}.',
            id=id,
        )

        # Copy unless dest already holds matching citation content.
        dest = dest_citation_service.get(id)
        if dest is None:
            self._ensure_parent_source(
                origin,
                dest_source_service,
                dest_activity_service,
                project_id,
            )
            dest = clone_citation(origin)
            dest_citation_service.save(dest)
            record_transfer_activity(
                dest_activity_service,
                CITATION_COPIED_ACTION,
                CITATION_SUBJECT_TYPE,
                dest.id,
                related_project_id=project_id,
            )
        else:
            self.verify(
                citation_content_matches(origin, dest),
                CITATION_ALREADY_EXISTS_ID,
                message=f'A citation with ID {id} already exists in the destination project.',
                id=id,
            )
            self.verify(
                dest_source_service.get(origin.source_id) is not None,
                SOURCE_NOT_FOUND_ID,
                message=f'Source not found: {origin.source_id}.',
                id=origin.source_id,
            )

        # Never remove origin before dest verification succeeds.
        dest = dest_citation_service.get(id)
        self.verify(
            citation_content_matches(origin, dest),
            CITATION_ALREADY_EXISTS_ID,
            message=f'Destination citation {id} is incomplete.',
            id=id,
        )
        self.verify(
            dest_source_service.get(origin.source_id) is not None,
            SOURCE_NOT_FOUND_ID,
            message=f'Source not found: {origin.source_id}.',
            id=origin.source_id,
        )

        # Origin-only remove is repository-private and leaves the parent source.
        remove_origin_artifact(self.citation_service, id)

        # Origin records citation.moved only after origin remove succeeds.
        record_transfer_activity(
            self.activity_service,
            CITATION_MOVED_ACTION,
            CITATION_SUBJECT_TYPE,
            id,
            related_project_id=dest_project_id,
        )

        # Return the dest citation.
        return dest

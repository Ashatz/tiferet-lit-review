"""Lit Review Source Events"""

# *** imports

# ** core
from pathlib import Path
from typing import List, Optional

# ** app
from tiferet import DomainEvent

from ..domain.activity import (
    SOURCE_ADDED_ACTION,
    SOURCE_DOCUMENT_ATTACHED_ACTION,
    SOURCE_SUBJECT_TYPE,
    SOURCE_UPDATED_ACTION,
)
from ..interfaces.activity import ActivityService
from ..interfaces.file import DocumentFileService
from ..interfaces.source import SourceService
from ..mappers.activity import ActivityAggregate
from ..mappers.source import SourceAggregate, SourceDocumentResponse
from .activity import record_activity

# *** constants

# ** constant: source_not_found_id
SOURCE_NOT_FOUND_ID = 'SOURCE_NOT_FOUND'

# ** constant: source_author_required_id
SOURCE_AUTHOR_REQUIRED_ID = 'SOURCE_AUTHOR_REQUIRED'

# ** constant: source_document_not_found_id
SOURCE_DOCUMENT_NOT_FOUND_ID = 'SOURCE_DOCUMENT_NOT_FOUND'

# *** events

# ** event: source_event
class SourceEvent(DomainEvent):
    '''
    Base event providing the shared SourceService dependency.
    '''

    # * attribute: source_service
    source_service: SourceService

    # * init
    def __init__(self, source_service: SourceService) -> None:
        '''
        Initialize the SourceEvent.

        :param source_service: The source service dependency.
        :type source_service: SourceService
        '''

        # Set the source service dependency.
        self.source_service = source_service

# ** event: add_source
class AddSource(SourceEvent):
    '''
    Register a new Source with its bibliographic record.
    '''

    # * attribute: activity_service
    activity_service: ActivityService

    # * init
    def __init__(self, source_service: SourceService, activity_service: ActivityService) -> None:
        '''
        Initialize the AddSource event.

        :param source_service: The source service dependency.
        :type source_service: SourceService
        :param activity_service: The activity service dependency.
        :type activity_service: ActivityService
        '''

        # Initialize the shared source service dependency.
        super().__init__(source_service)

        # Set the activity service dependency.
        self.activity_service = activity_service

    # * method: execute
    @DomainEvent.parameters_required(['source_medium', 'authors', 'year', 'title'])
    def execute(self,
            source_medium: str,
            authors: List[str],
            year: int,
            title: str,
            container_title: Optional[str] = None,
            publisher: Optional[str] = None,
            source_url: Optional[str] = None,
            url: Optional[str] = None,
            overview_note: Optional[str] = None,
            **kwargs,
        ) -> SourceAggregate:
        '''
        Add a new source.

        :param source_medium: The source medium (e.g. "pdf", "book").
        :type source_medium: str
        :param authors: The source authors.
        :type authors: List[str]
        :param year: The source publication year.
        :type year: int
        :param title: The source title.
        :type title: str
        :param container_title: The journal or collection title, where applicable.
        :type container_title: Optional[str]
        :param publisher: The source publisher, where applicable.
        :type publisher: Optional[str]
        :param source_url: The optional programmatic source URL.
        :type source_url: Optional[str]
        :param url: The optional CLI source URL alias.
        :type url: Optional[str]
        :param overview_note: An optional, medium-agnostic note about the work as a whole.
        :type overview_note: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The created source aggregate.
        :rtype: SourceAggregate
        '''

        # A source must carry at least one copied author name.
        self.verify(
            len(authors) > 0,
            SOURCE_AUTHOR_REQUIRED_ID,
            message='A source requires at least one author.',
        )
        # Prefer the programmatic field while accepting the CLI alias directly.
        resolved_source_url = source_url if source_url is not None else url

        # Create the source aggregate; the medium/locator_convention validator
        # on Source itself enforces the declared medium set.
        new_source = SourceAggregate(
            medium=source_medium,
            year=year,
            title=title,
            container_title=container_title,
            publisher=publisher,
            source_url=resolved_source_url,
            overview_note=overview_note,
        )

        # Copy each printed name onto the source through the aggregate lifecycle.
        for display_name in authors:
            new_source.add_author(display_name)
        self.source_service.save(new_source)

        # Best-effort: record the creation; a failed append never affects
        # the already-successful save above.
        record_activity(self.activity_service, ActivityAggregate(
            action=SOURCE_ADDED_ACTION,
            subject_type=SOURCE_SUBJECT_TYPE,
            subject_id=new_source.id,
        ))

        # Return the newly created source.
        return new_source

# ** event: get_source
class GetSource(SourceEvent):
    '''
    Retrieve a Source by its ID.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> SourceAggregate:
        '''
        Retrieve a source by ID.

        :param id: The source identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The source aggregate.
        :rtype: SourceAggregate
        '''

        # Retrieve the source from the service.
        source = self.source_service.get(id)

        # Verify the source exists.
        self.verify(
            source is not None,
            SOURCE_NOT_FOUND_ID,
            message=f'Source not found: {id}.',
            id=id,
        )

        # Return the source.
        return source

# ** event: list_sources
class ListSources(SourceEvent):
    '''
    List all sources.
    '''

    # * method: execute
    def execute(self, **kwargs) -> List[SourceAggregate]:
        '''
        List all sources.

        :param kwargs: Additional keyword arguments (unused).
        :type kwargs: dict
        :return: All source aggregates.
        :rtype: List[SourceAggregate]
        '''

        # Return all sources from the service.
        return self.source_service.list()

# ** event: update_source
class UpdateSource(SourceEvent):
    '''
    Update mutable bibliographic fields on an existing Source.
    '''

    # * attribute: activity_service
    activity_service: ActivityService

    # * init
    def __init__(self, source_service: SourceService, activity_service: ActivityService) -> None:
        '''
        Initialize the UpdateSource event.

        :param source_service: The source service dependency.
        :type source_service: SourceService
        :param activity_service: The activity service dependency.
        :type activity_service: ActivityService
        '''

        # Initialize the shared source service dependency.
        super().__init__(source_service)

        # Set the activity service dependency.
        self.activity_service = activity_service

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self,
            id: str,
            authors: Optional[List[str]] = None,
            year: Optional[int] = None,
            title: Optional[str] = None,
            container_title: Optional[str] = None,
            publisher: Optional[str] = None,
            source_url: Optional[str] = None,
            url: Optional[str] = None,
            overview_note: Optional[str] = None,
            clear_source_url: bool = False,
            clear_url: bool = False,
            clear_overview_note: bool = False,
            **kwargs,
        ) -> SourceAggregate:
        '''
        Update an existing source.

        :param id: The source identifier.
        :type id: str
        :param authors: The updated author list, if provided.
        :type authors: Optional[List[str]]
        :param year: The updated publication year, if provided.
        :type year: Optional[int]
        :param title: The updated title, if provided.
        :type title: Optional[str]
        :param container_title: The updated container title, if provided.
        :type container_title: Optional[str]
        :param publisher: The updated publisher, if provided.
        :type publisher: Optional[str]
        :param source_url: The optional programmatic source URL replacement.
        :type source_url: Optional[str]
        :param url: The optional CLI source URL replacement.
        :type url: Optional[str]
        :param overview_note: The updated overview note, if provided.
        :type overview_note: Optional[str]
        :param clear_source_url: When True, remove the source URL.
        :type clear_source_url: bool
        :param clear_url: The CLI alias for clear_source_url.
        :type clear_url: bool
        :param clear_overview_note: When True, remove the overview note.
        :type clear_overview_note: bool
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated source aggregate.
        :rtype: SourceAggregate
        '''

        # Retrieve the source and verify it exists.
        source = self.source_service.get(id)
        self.verify(
            source is not None,
            SOURCE_NOT_FOUND_ID,
            message=f'Source not found: {id}.',
            id=id,
        )

        # An author-list update must still leave at least one copied name.
        if authors is not None:
            self.verify(
                len(authors) > 0,
                SOURCE_AUTHOR_REQUIRED_ID,
                message='A source requires at least one author.',
            )
        # Prefer the programmatic field; blank aliases mean no requested update.
        resolved_source_url = source_url if source_url is not None else url
        if resolved_source_url is not None and not resolved_source_url.strip():
            resolved_source_url = None

        # Apply the requested bibliographic mutations.
        source.update_record(
            authors=authors,
            year=year,
            title=title,
            container_title=container_title,
            publisher=publisher,
            source_url=resolved_source_url,
            overview_note=overview_note,
            clear_source_url=clear_source_url or clear_url,
            clear_overview_note=clear_overview_note,
        )
        self.source_service.save(source)

        # Record only the field names this call actually touched; an update
        # call that touched nothing is a no-op and records nothing.
        changed_fields = []
        if authors is not None:
            changed_fields.append('authors')
        if year is not None:
            changed_fields.append('year')
        if title is not None:
            changed_fields.append('title')
        if container_title is not None:
            changed_fields.append('container_title')
        if publisher is not None:
            changed_fields.append('publisher')
        if clear_source_url or clear_url or resolved_source_url is not None:
            changed_fields.append('source_url')
        if clear_overview_note or overview_note is not None:
            changed_fields.append('overview_note')
        if changed_fields:
            record_activity(self.activity_service, ActivityAggregate(
                action=SOURCE_UPDATED_ACTION,
                subject_type=SOURCE_SUBJECT_TYPE,
                subject_id=source.id,
                changed_fields=changed_fields,
            ))

        # Return the updated source.
        return source

# ** event: attach_source_document
class AttachSourceDocument(SourceEvent):
    '''
    Attach a named source document to an existing Source.
    '''

    # * attribute: document_file_service
    document_file_service: DocumentFileService

    # * attribute: activity_service
    activity_service: ActivityService

    # * init
    def __init__(self,
            source_service: SourceService,
            document_file_service: DocumentFileService,
            activity_service: ActivityService,
        ) -> None:
        '''
        Initialize the AttachSourceDocument event.

        :param source_service: The source service dependency.
        :type source_service: SourceService
        :param document_file_service: Reads raw upload bytes from disk.
        :type document_file_service: DocumentFileService
        :param activity_service: The activity service dependency.
        :type activity_service: ActivityService
        '''

        # Initialize the shared source service dependency.
        super().__init__(source_service)

        # Set the document file service dependency.
        self.document_file_service = document_file_service

        # Set the activity service dependency.
        self.activity_service = activity_service

    # * method: execute
    @DomainEvent.parameters_required(['source_id', 'path'])
    def execute(self,
            source_id: str,
            path: str,
            document_name: Optional[str] = None,
            name: Optional[str] = None,
            **kwargs,
        ) -> SourceAggregate:
        '''
        Attach a document to a source, replacing any previous array.

        :param source_id: The source identifier to attach to.
        :type source_id: str
        :param path: Filesystem path of the file being uploaded.
        :type path: str
        :param document_name: Optional API / download name override for
            programmatic callers.
        :type document_name: Optional[str]
        :param name: Optional CLI-facing alias for document_name.
        :type name: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated source aggregate.
        :rtype: SourceAggregate
        '''

        # Retrieve the source and verify it exists before any write.
        source = self.source_service.get(source_id)
        self.verify(
            source is not None,
            SOURCE_NOT_FOUND_ID,
            message=f'Source not found: {source_id}.',
            id=source_id,
        )

        # Read the upload as raw bytes; do not parse or OCR it.
        content = self.document_file_service.read_bytes(path)

        # Prefer the programmatic override, then the CLI alias, then derivation.
        attached_name = document_name or name or source.derive_document_name(path=path)
        source.attach_document(attached_name)

        # Persist the name first, then replace the single document array.
        self.source_service.save(source)
        self.source_service.save_document(source.id, content)

        # Attaching always changes document_name; never a byte, path, or URL.
        record_activity(self.activity_service, ActivityAggregate(
            action=SOURCE_DOCUMENT_ATTACHED_ACTION,
            subject_type=SOURCE_SUBJECT_TYPE,
            subject_id=source.id,
            changed_fields=['document_name'],
        ))

        # Return the updated source.
        return source

# ** event: get_source_document
class GetSourceDocument(SourceEvent):
    '''
    Retrieve a source document's bytes and API name.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['source_id'])
    def execute(self, source_id: str, **kwargs) -> SourceDocumentResponse:
        '''
        Retrieve the attached source document.

        :param source_id: The source identifier.
        :type source_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The source document response.
        :rtype: SourceDocumentResponse
        '''

        # Retrieve the source and verify it exists.
        source = self.source_service.get(source_id)
        self.verify(
            source is not None,
            SOURCE_NOT_FOUND_ID,
            message=f'Source not found: {source_id}.',
            id=source_id,
        )

        # Retrieve the array only on this path; ordinary get/list stay metadata-only.
        content = self.source_service.get_document(source_id)
        self.verify(
            bool(source.document_name) and content is not None,
            SOURCE_DOCUMENT_NOT_FOUND_ID,
            message=f'Source document not found: {source_id}.',
            id=source_id,
        )

        # Return the named body for download or compare-by-retrieve.
        return SourceDocumentResponse.from_aggregate(
            source,
            content=content,
        )

# ** event: download_source_document
class DownloadSourceDocument(SourceEvent):
    '''
    Write an attached source document to disk under its API name.
    '''

    # * attribute: document_file_service
    document_file_service: DocumentFileService

    # * init
    def __init__(self,
            source_service: SourceService,
            document_file_service: DocumentFileService,
        ) -> None:
        '''
        Initialize the DownloadSourceDocument event.

        :param source_service: The source service dependency.
        :type source_service: SourceService
        :param document_file_service: Writes retrieved bytes to disk.
        :type document_file_service: DocumentFileService
        '''

        # Initialize the shared source service dependency.
        super().__init__(source_service)

        # Set the document file service dependency.
        self.document_file_service = document_file_service

    # * method: execute
    @DomainEvent.parameters_required(['source_id'])
    def execute(self,
            source_id: str,
            out: Optional[str] = None,
            **kwargs,
        ) -> SourceDocumentResponse:
        '''
        Download a source document under its stored document name.

        :param source_id: The source identifier.
        :type source_id: str
        :param out: Optional destination directory; defaults to the cwd.
        :type out: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The source document response that was written.
        :rtype: SourceDocumentResponse
        '''

        # Retrieve the source and verify it exists.
        source = self.source_service.get(source_id)
        self.verify(
            source is not None,
            SOURCE_NOT_FOUND_ID,
            message=f'Source not found: {source_id}.',
            id=source_id,
        )

        # Retrieve the attached body; missing name or array is the same error.
        content = self.source_service.get_document(source_id)
        self.verify(
            bool(source.document_name) and content is not None,
            SOURCE_DOCUMENT_NOT_FOUND_ID,
            message=f'Source document not found: {source_id}.',
            id=source_id,
        )

        # Write the file as document_name, not the original upload basename.
        destination = Path(out) if out else Path.cwd()
        target = destination / source.document_name
        self.document_file_service.write_bytes(str(target), content)

        # Return the named body that was written.
        return SourceDocumentResponse.from_aggregate(
            source,
            content=content,
        )

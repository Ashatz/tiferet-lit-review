"""Lit Review Source Events"""

# *** imports

# ** core
from typing import List, Optional

# ** app
from tiferet import DomainEvent

from ..interfaces.source import SourceService
from ..mappers.source import SourceAggregate

# *** constants

# ** constant: source_not_found_id
SOURCE_NOT_FOUND_ID = 'SOURCE_NOT_FOUND'

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

    # * method: execute
    @DomainEvent.parameters_required(['source_medium', 'authors', 'year', 'title'])
    def execute(self,
            source_medium: str,
            authors: List[str],
            year: int,
            title: str,
            container_title: Optional[str] = None,
            publisher: Optional[str] = None,
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
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The created source aggregate.
        :rtype: SourceAggregate
        '''

        # Create and save the source aggregate; the medium/locator_convention
        # validator on Source itself enforces the declared medium set.
        new_source = SourceAggregate(
            medium=source_medium,
            authors=authors,
            year=year,
            title=title,
            container_title=container_title,
            publisher=publisher,
        )
        self.source_service.save(new_source)

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

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self,
            id: str,
            authors: Optional[List[str]] = None,
            year: Optional[int] = None,
            title: Optional[str] = None,
            container_title: Optional[str] = None,
            publisher: Optional[str] = None,
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

        # Apply the requested bibliographic mutations.
        source.update_record(
            authors=authors,
            year=year,
            title=title,
            container_title=container_title,
            publisher=publisher,
        )
        self.source_service.save(source)

        # Return the updated source.
        return source

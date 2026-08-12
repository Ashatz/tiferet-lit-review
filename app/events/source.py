"""Lit Review Source Events"""

# *** imports

# ** core
from typing import List, Optional

# ** app
from tiferet import DomainEvent

from .. import assets as a
from ..domain.source import Source
from ..interfaces.source import SourceService
from ..mappers.source import SourceAggregate

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
        ) -> Source:
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
        :return: The created Source domain object.
        :rtype: Source
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
    def execute(self, id: str, **kwargs) -> Source:
        '''
        Retrieve a source by ID.

        :param id: The source identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The Source domain object.
        :rtype: Source
        '''

        # Retrieve the source from the service.
        source = self.source_service.get(id)

        # Verify the source exists.
        self.verify(
            source is not None,
            a.error.SOURCE_NOT_FOUND_ID,
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
    def execute(self, **kwargs) -> List[Source]:
        '''
        List all sources.

        :param kwargs: Additional keyword arguments (unused).
        :type kwargs: dict
        :return: All sources.
        :rtype: List[Source]
        '''

        # Return all sources from the service.
        return self.source_service.list()

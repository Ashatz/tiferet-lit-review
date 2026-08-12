"""Lit Review Citation Events"""

# *** imports

# ** core
from typing import List, Optional

# ** app
from tiferet import DomainEvent

from .. import assets as a
from ..domain.citation import Citation
from ..domain.source import is_valid_locator
from ..interfaces.citation import CitationService
from ..interfaces.source import SourceService
from ..mappers.citation import CitationAggregate

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

    # * init
    def __init__(self, citation_service: CitationService, source_service: SourceService) -> None:
        '''
        Initialize the AddCitation event.

        :param citation_service: The citation service dependency.
        :type citation_service: CitationService
        :param source_service: The source service dependency, used to verify
            the parent source and resolve its locator convention.
        :type source_service: SourceService
        '''

        # Initialize the shared citation service dependency.
        super().__init__(citation_service)

        # Set the source service dependency.
        self.source_service = source_service

    # * method: execute
    @DomainEvent.parameters_required(['source_id', 'locator', 'excerpt'])
    def execute(self,
            source_id: str,
            locator: str,
            excerpt: str,
            context_note: Optional[str] = None,
            **kwargs,
        ) -> Citation:
        '''
        Add a new citation.

        :param source_id: The identifier of the source this citation was pulled from.
        :type source_id: str
        :param locator: The precise locator of the excerpt within its source.
        :type locator: str
        :param excerpt: The quoted or paraphrased text pulled from the source.
        :type excerpt: str
        :param context_note: An optional surrounding-context note.
        :type context_note: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The created Citation domain object.
        :rtype: Citation
        '''

        # Verify the parent source exists.
        source = self.source_service.get(source_id)
        self.verify(
            source is not None,
            a.error.SOURCE_NOT_FOUND_ID,
            message=f'Source not found: {source_id}.',
            source_id=source_id,
        )

        # Verify the locator shape matches the source's locator convention.
        self.verify(
            is_valid_locator(source.locator_convention, locator),
            a.error.INVALID_LOCATOR_ID,
            message=f'Invalid locator {locator!r} for convention {source.locator_convention!r}.',
            locator=locator,
            locator_convention=source.locator_convention,
        )

        # Create and save the citation aggregate.
        new_citation = CitationAggregate(
            source_id=source_id,
            locator=locator,
            excerpt=excerpt,
            context_note=context_note,
        )
        self.citation_service.save(new_citation)

        # Return the newly created citation.
        return new_citation

# ** event: get_citation
class GetCitation(CitationEvent):
    '''
    Retrieve a Citation by its ID.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> Citation:
        '''
        Retrieve a citation by ID.

        :param id: The citation identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The Citation domain object.
        :rtype: Citation
        '''

        # Retrieve the citation from the service.
        citation = self.citation_service.get(id)

        # Verify the citation exists.
        self.verify(
            citation is not None,
            a.error.CITATION_NOT_FOUND_ID,
            message=f'Citation not found: {id}.',
            id=id,
        )

        # Return the citation.
        return citation

# ** event: list_citations_for_source
class ListCitationsForSource(CitationEvent):
    '''
    List all citations belonging to a given source, in insertion order.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['source_id'])
    def execute(self, source_id: str, **kwargs) -> List[Citation]:
        '''
        List all citations for a source.

        :param source_id: The source identifier to filter citations by.
        :type source_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The citations belonging to the source, in insertion order.
        :rtype: List[Citation]
        '''

        # Return the citations filtered by source_id.
        return self.citation_service.list(source_id=source_id)

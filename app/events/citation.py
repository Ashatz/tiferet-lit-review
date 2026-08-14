"""Lit Review Citation Events"""

# *** imports

# ** core
from typing import List, Optional

# ** app
from tiferet import DomainEvent

from ..domain.source import is_valid_locator
from ..interfaces.citation import CitationService
from ..interfaces.source import SourceService
from ..mappers.citation import CitationAggregate
from .source import SOURCE_NOT_FOUND_ID

# *** constants

# ** constant: citation_not_found_id
CITATION_NOT_FOUND_ID = 'CITATION_NOT_FOUND'

# ** constant: invalid_locator_id
INVALID_LOCATOR_ID = 'INVALID_LOCATOR'

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
        ) -> CitationAggregate:
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
        :return: The created citation aggregate.
        :rtype: CitationAggregate
        '''

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

# ** event: list_citations_for_source
class ListCitationsForSource(CitationEvent):
    '''
    List all citations belonging to a given source, in insertion order.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['source_id'])
    def execute(self, source_id: str, **kwargs) -> List[CitationAggregate]:
        '''
        List all citations for a source.

        :param source_id: The source identifier to filter citations by.
        :type source_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The citations belonging to the source, in insertion order.
        :rtype: List[CitationAggregate]
        '''

        # Return the citations filtered by source_id.
        return self.citation_service.list(source_id=source_id)

# ** event: update_citation
class UpdateCitation(CitationEvent):
    '''
    Update mutable fields on an existing Citation.
    '''

    # * attribute: source_service
    source_service: SourceService

    # * init
    def __init__(self, citation_service: CitationService, source_service: SourceService) -> None:
        '''
        Initialize the UpdateCitation event.

        :param citation_service: The citation service dependency.
        :type citation_service: CitationService
        :param source_service: The source service dependency, used to
            re-validate locator shape against the parent source.
        :type source_service: SourceService
        '''

        # Initialize the shared citation service dependency.
        super().__init__(citation_service)

        # Set the source service dependency.
        self.source_service = source_service

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self,
            id: str,
            locator: Optional[str] = None,
            excerpt: Optional[str] = None,
            context_note: Optional[str] = None,
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

        # Persist the updated citation via id-upsert save.
        self.citation_service.save(citation)

        # Return the updated citation.
        return citation

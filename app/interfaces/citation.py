"""Lit Review Citation Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional

# ** app
from tiferet.interfaces.core import Service

from ..mappers.citation import CitationAggregate

# *** interfaces

# ** interface: citation_service
class CitationService(Service):
    '''
    Vertical interface for managing Citation aggregates.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, id: str) -> bool:
        '''
        Check whether a citation with the given ID exists.

        :param id: The citation identifier.
        :type id: str
        :return: True if the citation exists, otherwise False.
        :rtype: bool
        '''
        raise NotImplementedError()

    # * method: get
    @abstractmethod
    def get(self, id: str) -> Optional[CitationAggregate]:
        '''
        Retrieve a Citation by its ID.

        :param id: The citation identifier.
        :type id: str
        :return: The citation aggregate, or None if not found.
        :rtype: Optional[CitationAggregate]
        '''
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self, **filters) -> List[CitationAggregate]:
        '''
        List Citation aggregates, optionally filtered (e.g. by source_id).

        :param filters: Optional filter criteria.
        :type filters: dict
        :return: The matching citation aggregates, in insertion order.
        :rtype: List[CitationAggregate]
        '''
        raise NotImplementedError()

    # * method: save
    @abstractmethod
    def save(self, citation: CitationAggregate) -> None:
        '''
        Persist a Citation aggregate.

        :param citation: The citation aggregate to persist.
        :type citation: CitationAggregate
        '''
        raise NotImplementedError()

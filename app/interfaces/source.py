"""Lit Review Source Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional

# ** app
from tiferet.interfaces.core import Service

from ..mappers.source import SourceAggregate

# *** interfaces

# ** interface: source_service
class SourceService(Service):
    '''
    Vertical interface for managing Source aggregates.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, id: str) -> bool:
        '''
        Check whether a source with the given ID exists.

        :param id: The source identifier.
        :type id: str
        :return: True if the source exists, otherwise False.
        :rtype: bool
        '''
        raise NotImplementedError()

    # * method: get
    @abstractmethod
    def get(self, id: str) -> Optional[SourceAggregate]:
        '''
        Retrieve a Source by its ID.

        :param id: The source identifier.
        :type id: str
        :return: The source aggregate, or None if not found.
        :rtype: Optional[SourceAggregate]
        '''
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self, **filters) -> List[SourceAggregate]:
        '''
        List Source aggregates, optionally filtered.

        :param filters: Optional filter criteria.
        :type filters: dict
        :return: The matching source aggregates.
        :rtype: List[SourceAggregate]
        '''
        raise NotImplementedError()

    # * method: save
    @abstractmethod
    def save(self, source: SourceAggregate) -> None:
        '''
        Persist a Source aggregate.

        :param source: The source aggregate to persist.
        :type source: SourceAggregate
        '''
        raise NotImplementedError()

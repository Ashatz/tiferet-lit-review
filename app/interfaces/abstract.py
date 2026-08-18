"""Lit Review Abstract Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional

# ** app
from tiferet.interfaces.core import Service

from ..mappers.abstract import AbstractAggregate

# *** interfaces

# ** interface: abstract_service
class AbstractService(Service):
    '''
    Vertical interface for managing Abstract aggregates.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, id: str) -> bool:
        '''
        Check whether an abstract with the given ID exists.

        :param id: The abstract identifier.
        :type id: str
        :return: True if the abstract exists, otherwise False.
        :rtype: bool
        '''
        raise NotImplementedError()

    # * method: get
    @abstractmethod
    def get(self, id: str) -> Optional[AbstractAggregate]:
        '''
        Retrieve an Abstract by its ID.

        :param id: The abstract identifier.
        :type id: str
        :return: The abstract aggregate, or None if not found.
        :rtype: Optional[AbstractAggregate]
        '''
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self, name: Optional[str] = None) -> List[AbstractAggregate]:
        '''
        List Abstract aggregates, optionally filtered by name.

        :param name: Optional abstract name to match exactly.
        :type name: Optional[str]
        :return: The matching abstract aggregates.
        :rtype: List[AbstractAggregate]
        '''
        raise NotImplementedError()

    # * method: save
    @abstractmethod
    def save(self, abstract: AbstractAggregate) -> None:
        '''
        Persist an Abstract aggregate.

        :param abstract: The abstract aggregate to persist.
        :type abstract: AbstractAggregate
        '''
        raise NotImplementedError()

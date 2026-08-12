"""Lit Review Source Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional

# ** app
from tiferet.interfaces.core import Service

from ..domain.source import Source

# *** interfaces

# ** interface: source_service
class SourceService(Service):
    '''
    Vertical interface for managing Source domain objects.
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
    def get(self, id: str) -> Optional[Source]:
        '''
        Retrieve a Source by its ID.

        :param id: The source identifier.
        :type id: str
        :return: The Source domain object, or None if not found.
        :rtype: Optional[Source]
        '''
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self, **filters) -> List[Source]:
        '''
        List Source domain objects, optionally filtered.

        :param filters: Optional filter criteria.
        :type filters: dict
        :return: The matching sources.
        :rtype: List[Source]
        '''
        raise NotImplementedError()

    # * method: save
    @abstractmethod
    def save(self, source: Source) -> None:
        '''
        Persist a Source domain object.

        :param source: The source to persist.
        :type source: Source
        '''
        raise NotImplementedError()

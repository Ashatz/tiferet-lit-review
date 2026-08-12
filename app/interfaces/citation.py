"""Lit Review Citation Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional

# ** app
from tiferet.interfaces.core import Service

from ..domain.citation import Citation

# *** interfaces

# ** interface: citation_service
class CitationService(Service):
    '''
    Vertical interface for managing Citation domain objects.
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
    def get(self, id: str) -> Optional[Citation]:
        '''
        Retrieve a Citation by its ID.

        :param id: The citation identifier.
        :type id: str
        :return: The Citation domain object, or None if not found.
        :rtype: Optional[Citation]
        '''
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self, **filters) -> List[Citation]:
        '''
        List Citation domain objects, optionally filtered (e.g. by source_id).

        :param filters: Optional filter criteria.
        :type filters: dict
        :return: The matching citations, in insertion order.
        :rtype: List[Citation]
        '''
        raise NotImplementedError()

    # * method: save
    @abstractmethod
    def save(self, citation: Citation) -> None:
        '''
        Persist a Citation domain object.

        :param citation: The citation to persist.
        :type citation: Citation
        '''
        raise NotImplementedError()

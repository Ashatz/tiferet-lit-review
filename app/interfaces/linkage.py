"""Lit Review Linkage Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional

# ** app
from tiferet.interfaces.core import Service

from ..mappers.linkage import LinkageAggregate

# *** interfaces

# ** interface: linkage_service
class LinkageService(Service):
    '''
    Vertical interface for managing Linkage aggregates.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, id: str) -> bool:
        '''
        Check whether a linkage with the given ID exists.

        :param id: The linkage identifier.
        :type id: str
        :return: True if the linkage exists, otherwise False.
        :rtype: bool
        '''
        raise NotImplementedError()

    # * method: get
    @abstractmethod
    def get(self, id: str) -> Optional[LinkageAggregate]:
        '''
        Retrieve a Linkage by its ID.

        :param id: The linkage identifier.
        :type id: str
        :return: The linkage aggregate, or None if not found.
        :rtype: Optional[LinkageAggregate]
        '''
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self,
            theme_id: Optional[str] = None,
            citation_id: Optional[str] = None,
        ) -> List[LinkageAggregate]:
        '''
        List Linkage aggregates, optionally filtered by theme or citation.

        :param theme_id: Optional theme identifier to match.
        :type theme_id: Optional[str]
        :param citation_id: Optional citation identifier to match.
        :type citation_id: Optional[str]
        :return: The matching linkage aggregates, in insertion order.
        :rtype: List[LinkageAggregate]
        '''
        raise NotImplementedError()

    # * method: save
    @abstractmethod
    def save(self, linkage: LinkageAggregate) -> None:
        '''
        Persist a Linkage aggregate.

        :param linkage: The linkage aggregate to persist.
        :type linkage: LinkageAggregate
        '''
        raise NotImplementedError()

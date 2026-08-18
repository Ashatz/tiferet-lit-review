"""Lit Review Outline Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional

# ** app
from tiferet.interfaces.core import Service

from ..mappers.outline import OutlineAggregate

# *** interfaces

# ** interface: outline_service
class OutlineService(Service):
    '''
    Vertical interface for managing Outline aggregates.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, id: str) -> bool:
        '''
        Check whether an outline with the given ID exists.

        :param id: The outline identifier.
        :type id: str
        :return: True if the outline exists, otherwise False.
        :rtype: bool
        '''
        raise NotImplementedError()

    # * method: get
    @abstractmethod
    def get(self, id: str) -> Optional[OutlineAggregate]:
        '''
        Retrieve an Outline by its ID.

        :param id: The outline identifier.
        :type id: str
        :return: The outline aggregate, or None if not found.
        :rtype: Optional[OutlineAggregate]
        '''
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self,
            title: Optional[str] = None,
            theme_id: Optional[str] = None,
        ) -> List[OutlineAggregate]:
        '''
        List Outline aggregates, optionally filtered by title or theme.

        :param title: Optional outline title to match exactly.
        :type title: Optional[str]
        :param theme_id: Optional theme identifier included in a slot.
        :type theme_id: Optional[str]
        :return: The matching outline aggregates.
        :rtype: List[OutlineAggregate]
        '''
        raise NotImplementedError()

    # * method: save
    @abstractmethod
    def save(self, outline: OutlineAggregate) -> None:
        '''
        Persist an Outline aggregate.

        :param outline: The outline aggregate to persist.
        :type outline: OutlineAggregate
        '''
        raise NotImplementedError()

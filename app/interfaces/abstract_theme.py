"""Lit Review AbstractTheme Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional

# ** app
from tiferet.interfaces.core import Service

from ..mappers.abstract_theme import AbstractThemeAggregate

# *** interfaces

# ** interface: abstract_theme_service
class AbstractThemeService(Service):
    '''
    Vertical interface for managing AbstractTheme aggregates.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, id: str) -> bool:
        '''
        Check whether a join with the given ID exists.

        :param id: The join identifier.
        :type id: str
        :return: True if the join exists, otherwise False.
        :rtype: bool
        '''
        raise NotImplementedError()

    # * method: get
    @abstractmethod
    def get(self, id: str) -> Optional[AbstractThemeAggregate]:
        '''
        Retrieve an AbstractTheme by its ID.

        :param id: The join identifier.
        :type id: str
        :return: The join aggregate, or None if not found.
        :rtype: Optional[AbstractThemeAggregate]
        '''
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self,
            abstract_id: Optional[str] = None,
            theme_id: Optional[str] = None,
        ) -> List[AbstractThemeAggregate]:
        '''
        List AbstractTheme aggregates, optionally filtered by abstract or theme.

        :param abstract_id: Optional abstract identifier to match.
        :type abstract_id: Optional[str]
        :param theme_id: Optional theme identifier to match.
        :type theme_id: Optional[str]
        :return: The matching join aggregates, in insertion order.
        :rtype: List[AbstractThemeAggregate]
        '''
        raise NotImplementedError()

    # * method: save
    @abstractmethod
    def save(self, abstract_theme: AbstractThemeAggregate) -> None:
        '''
        Persist an AbstractTheme aggregate.

        :param abstract_theme: The join aggregate to persist.
        :type abstract_theme: AbstractThemeAggregate
        '''
        raise NotImplementedError()

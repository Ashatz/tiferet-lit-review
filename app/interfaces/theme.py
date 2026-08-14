"""Lit Review Theme Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional

# ** app
from tiferet.interfaces.core import Service

from ..mappers.theme import ThemeAggregate

# *** interfaces

# ** interface: theme_service
class ThemeService(Service):
    '''
    Vertical interface for managing Theme aggregates.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, id: str) -> bool:
        '''
        Check whether a theme with the given ID exists.

        :param id: The theme identifier.
        :type id: str
        :return: True if the theme exists, otherwise False.
        :rtype: bool
        '''
        raise NotImplementedError()

    # * method: get
    @abstractmethod
    def get(self, id: str) -> Optional[ThemeAggregate]:
        '''
        Retrieve a Theme by its ID.

        :param id: The theme identifier.
        :type id: str
        :return: The theme aggregate, or None if not found.
        :rtype: Optional[ThemeAggregate]
        '''
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self, **filters) -> List[ThemeAggregate]:
        '''
        List Theme aggregates, optionally filtered.

        :param filters: Optional filter criteria.
        :type filters: dict
        :return: The matching theme aggregates.
        :rtype: List[ThemeAggregate]
        '''
        raise NotImplementedError()

    # * method: save
    @abstractmethod
    def save(self, theme: ThemeAggregate) -> None:
        '''
        Persist a Theme aggregate.

        :param theme: The theme aggregate to persist.
        :type theme: ThemeAggregate
        '''
        raise NotImplementedError()

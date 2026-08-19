"""Lit Review Paper Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional

# ** app
from tiferet.interfaces.core import Service

from ..mappers.paper import PaperAggregate

# *** interfaces

# ** interface: paper_service
class PaperService(Service):
    '''
    Vertical interface for managing Paper aggregates.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, id: str) -> bool:
        '''
        Check whether a paper with the given ID exists.

        :param id: The paper identifier.
        :type id: str
        :return: True if the paper exists, otherwise False.
        :rtype: bool
        '''
        raise NotImplementedError()

    # * method: get
    @abstractmethod
    def get(self, id: str) -> Optional[PaperAggregate]:
        '''
        Retrieve a Paper by its ID.

        :param id: The paper identifier.
        :type id: str
        :return: The paper aggregate, or None if not found.
        :rtype: Optional[PaperAggregate]
        '''
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self,
            title: Optional[str] = None,
            outline_id: Optional[str] = None,
        ) -> List[PaperAggregate]:
        '''
        List Paper aggregates, optionally filtered by title or origin outline.

        :param title: Optional paper title to match exactly.
        :type title: Optional[str]
        :param outline_id: Optional origin outline identifier.
        :type outline_id: Optional[str]
        :return: The matching paper aggregates.
        :rtype: List[PaperAggregate]
        '''
        raise NotImplementedError()

    # * method: save
    @abstractmethod
    def save(self, paper: PaperAggregate) -> None:
        '''
        Persist a Paper aggregate.

        :param paper: The paper aggregate to persist.
        :type paper: PaperAggregate
        '''
        raise NotImplementedError()

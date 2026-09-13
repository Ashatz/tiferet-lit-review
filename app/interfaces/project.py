"""Lit Review Project Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional

# ** app
from tiferet.interfaces.core import Service

from ..mappers.project import ProjectAggregate

# *** interfaces

# ** interface: project_service
class ProjectService(Service):
    '''
    Vertical interface for the Project catalog outside any research-graph store.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, id: str) -> bool:
        '''
        Check whether a project with the given ID exists in the catalog.

        :param id: The project identifier.
        :type id: str
        :return: True if the project exists, otherwise False.
        :rtype: bool
        '''
        raise NotImplementedError()

    # * method: get
    @abstractmethod
    def get(self, id: str) -> Optional[ProjectAggregate]:
        '''
        Retrieve a Project by its ID.

        :param id: The project identifier.
        :type id: str
        :return: The project aggregate, or None if not found.
        :rtype: Optional[ProjectAggregate]
        '''
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self) -> List[ProjectAggregate]:
        '''
        List all Project catalog records.

        :return: All stored project aggregates.
        :rtype: List[ProjectAggregate]
        '''
        raise NotImplementedError()

    # * method: save
    @abstractmethod
    def save(self, project: ProjectAggregate) -> None:
        '''
        Persist a Project catalog record.

        :param project: The project aggregate to persist.
        :type project: ProjectAggregate
        '''
        raise NotImplementedError()

"""Lit Review Project Catalog Events"""

# *** imports

# ** core
from pathlib import Path
from typing import List

# ** infra
import tables

# ** app
from tiferet import DomainEvent

from ..interfaces.project import ProjectService
from ..mappers.project import ProjectAggregate

# *** constants

# ** constant: project_not_found_id
PROJECT_NOT_FOUND_ID = 'PROJECT_NOT_FOUND'

# ** constant: project_already_exists_id
PROJECT_ALREADY_EXISTS_ID = 'PROJECT_ALREADY_EXISTS'

# *** functions

# ** function: ensure_h5_file
def ensure_h5_file(h5_file: str) -> None:
    '''
    Create an empty HDF5 file at the recorded path when it does not exist.

    :param h5_file: Filesystem path for the new research store.
    :type h5_file: str
    '''

    # Ensure the parent directory exists before opening the store.
    path = Path(h5_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Open-append creates a valid HDF5 file without truncating an existing one.
    tables.open_file(str(path), mode='a').close()

# *** events

# ** event: project_event
class ProjectEvent(DomainEvent):
    '''
    Base event providing the shared ProjectService catalog dependency.
    '''

    # * attribute: project_service
    project_service: ProjectService

    # * init
    def __init__(self, project_service: ProjectService) -> None:
        '''
        Initialize the ProjectEvent.

        :param project_service: The project catalog service dependency.
        :type project_service: ProjectService
        '''

        # Set the project catalog service dependency.
        self.project_service = project_service


# ** event: add_project
class AddProject(ProjectEvent):
    '''
    Add a catalog entry and create an empty HDF5 research store at its path.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id', 'name', 'h5_file'])
    def execute(self,
            id: str,
            name: str,
            h5_file: str,
            **kwargs,
        ) -> ProjectAggregate:
        '''
        Add a new project catalog record and create its store file.

        :param id: The unique project identifier.
        :type id: str
        :param name: The human-readable project name.
        :type name: str
        :param h5_file: Filesystem path for the new HDF5 store.
        :type h5_file: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The created project aggregate.
        :rtype: ProjectAggregate
        '''

        # Verify the project does not already exist in the catalog.
        self.verify(
            not self.project_service.exists(id),
            PROJECT_ALREADY_EXISTS_ID,
            message=f'A project with ID {id} already exists.',
            id=id,
        )

        # Create and save the catalog record without binding a research store.
        new_project = ProjectAggregate(
            id=id,
            name=name,
            h5_file=h5_file,
        )
        self.project_service.save(new_project)

        # Create an empty/new HDF5 file at the recorded path.
        ensure_h5_file(h5_file)

        # Return the newly created project.
        return new_project


# ** event: list_projects
class ListProjects(ProjectEvent):
    '''
    List project catalog records without opening a research-graph store.
    '''

    # * method: execute
    def execute(self, **kwargs) -> List[ProjectAggregate]:
        '''
        List all project catalog records.

        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: All stored project aggregates.
        :rtype: List[ProjectAggregate]
        '''

        # Return the catalog rows only.
        return self.project_service.list()


# ** event: get_project
class GetProject(ProjectEvent):
    '''
    Retrieve a project catalog record by identifier.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> ProjectAggregate:
        '''
        Retrieve a project by ID.

        :param id: The project identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The project aggregate.
        :rtype: ProjectAggregate
        '''

        # Retrieve the project from the catalog.
        project = self.project_service.get(id)

        # Verify the project exists.
        self.verify(
            project is not None,
            PROJECT_NOT_FOUND_ID,
            message=f'Project not found: {id}.',
            id=id,
        )

        # Return the project.
        return project

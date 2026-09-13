"""Lit Review Project Catalog Event Tests"""

# *** imports

# ** infra
import pytest
from unittest import mock

# ** app
from tiferet import DomainEvent
from tiferet.assets import TiferetError

from app.events.project import (
    PROJECT_ALREADY_EXISTS_ID,
    PROJECT_NOT_FOUND_ID,
    AddProject,
    GetProject,
    ListProjects,
    ensure_h5_file,
)
from app.interfaces.project import ProjectService
from app.mappers.project import ProjectAggregate

# *** constants

# ** constant: project_id
PROJECT_ID = 'dissertation'

# ** constant: project_name
PROJECT_NAME = 'Dissertation'

# *** fixtures

# ** fixture: project
@pytest.fixture
def project() -> ProjectAggregate:
    '''
    Build a sample project catalog record.

    :return: A project aggregate.
    :rtype: ProjectAggregate
    '''

    # Return a catalog record used by get/list tests.
    return ProjectAggregate(
        id=PROJECT_ID,
        name=PROJECT_NAME,
        h5_file='/tmp/dissertation.h5',
        created_at=1700000000,
    )


# ** fixture: project_service
@pytest.fixture
def project_service(project) -> mock.Mock:
    '''
    Build a mocked project catalog service.

    :param project: The sample project fixture.
    :type project: ProjectAggregate
    :return: A mocked ProjectService.
    :rtype: mock.Mock
    '''

    # Mock the catalog interface with no pre-existing row.
    service = mock.Mock(spec=ProjectService)
    service.exists.return_value = False
    service.get.return_value = project
    service.list.return_value = [project]
    return service

# *** tests

# ** test: test_add_project_saves_catalog_and_creates_h5
def test_add_project_saves_catalog_and_creates_h5(project_service, tmp_path):
    '''
    AddProject writes a catalog entry and creates an HDF5 file at the path.

    :param project_service: The mocked project catalog service.
    :type project_service: mock.Mock
    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    '''

    # Add a project whose store path lives under the temp directory.
    h5_file = str(tmp_path / 'stores' / 'dissertation.h5')
    result = DomainEvent.handle(
        AddProject,
        dependencies={'project_service': project_service},
        id=PROJECT_ID,
        name=PROJECT_NAME,
        h5_file=h5_file,
    )

    # The catalog row is saved and a new HDF5 file exists at the recorded path.
    project_service.save.assert_called_once()
    assert result.id == PROJECT_ID
    assert result.name == PROJECT_NAME
    assert result.h5_file == h5_file
    assert (tmp_path / 'stores' / 'dissertation.h5').is_file()


# ** test: test_add_project_rejects_duplicate_id
def test_add_project_rejects_duplicate_id(project_service):
    '''
    AddProject raises when the catalog already has the requested id.

    :param project_service: The mocked project catalog service.
    :type project_service: mock.Mock
    '''

    # Pretend the identifier is already catalogued.
    project_service.exists.return_value = True

    # Execute and expect PROJECT_ALREADY_EXISTS before any save.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            AddProject,
            dependencies={'project_service': project_service},
            id=PROJECT_ID,
            name=PROJECT_NAME,
            h5_file='/tmp/dissertation.h5',
        )

    # Assert the structured error and that the catalog was not written.
    assert exc_info.value.error_code == PROJECT_ALREADY_EXISTS_ID
    project_service.save.assert_not_called()


# ** test: test_list_projects_returns_catalog_rows
def test_list_projects_returns_catalog_rows(project_service, project):
    '''
    ListProjects returns catalog records without extra arguments.

    :param project_service: The mocked project catalog service.
    :type project_service: mock.Mock
    :param project: The sample project fixture.
    :type project: ProjectAggregate
    '''

    # List the catalog.
    result = DomainEvent.handle(
        ListProjects,
        dependencies={'project_service': project_service},
    )

    # The catalog service is the only collaborator consulted.
    project_service.list.assert_called_once_with()
    assert result == [project]


# ** test: test_get_project_missing_raises
def test_get_project_missing_raises(project_service):
    '''
    GetProject raises PROJECT_NOT_FOUND when the catalog has no row.

    :param project_service: The mocked project catalog service.
    :type project_service: mock.Mock
    '''

    # The catalog has no matching row.
    project_service.get.return_value = None

    # Execute and expect PROJECT_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            GetProject,
            dependencies={'project_service': project_service},
            id='missing',
        )

    # Assert the structured error.
    assert exc_info.value.error_code == PROJECT_NOT_FOUND_ID


# ** test: test_ensure_h5_file_does_not_truncate
def test_ensure_h5_file_does_not_truncate(tmp_path):
    '''
    ensure_h5_file leaves an existing HDF5 file intact.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    '''

    # Create an HDF5 file with a marker group, then reopen via ensure_h5_file.
    h5_file = str(tmp_path / 'existing.h5')
    ensure_h5_file(h5_file)
    import tables
    with tables.open_file(h5_file, mode='a') as handle:
        handle.create_group('/', 'marker')
    ensure_h5_file(h5_file)

    # The marker group survives the second open-append.
    with tables.open_file(h5_file, mode='r') as handle:
        assert '/marker' in handle

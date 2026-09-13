"""Lit Review Project Catalog Repository Integration Tests"""

# *** imports

# ** infra
import pytest

# ** app
from app.mappers.project import ProjectAggregate
from app.repos.project import (
    DEFAULT_H5_FILE,
    DEFAULT_PROJECT_ID,
    ProjectConfigRepository,
)

# *** fixtures

# ** fixture: repo
@pytest.fixture
def repo(tmp_path) -> ProjectConfigRepository:
    '''
    Build a project catalog repository against a temporary YAML file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: A project catalog repository.
    :rtype: ProjectConfigRepository
    '''

    # Return a repository pointing at an isolated catalog file.
    return ProjectConfigRepository(
        project_config=str(tmp_path / 'projects.yml'),
    )

# *** tests

# ** test_int: test_list_bootstraps_default_without_opening_h5
def test_list_bootstraps_default_without_opening_h5(repo, tmp_path):
    '''
    First-run list seeds project id default and does not create an HDF5 file.

    :param repo: The temporary project catalog repository.
    :type repo: ProjectConfigRepository
    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    '''

    # List an empty catalog so bootstrap writes the default row.
    projects = repo.list()

    # The default catalog row is present and no research store was opened.
    assert len(projects) == 1
    assert projects[0].id == DEFAULT_PROJECT_ID
    assert projects[0].h5_file == DEFAULT_H5_FILE
    assert (tmp_path / 'lit_review.h5').exists() is False


# ** test_int: test_save_and_get_round_trip
def test_save_and_get_round_trip(repo):
    '''
    Saving a catalog row makes it retrievable by id.

    :param repo: The temporary project catalog repository.
    :type repo: ProjectConfigRepository
    '''

    # Persist a named catalog record.
    project = ProjectAggregate(
        id='dissertation',
        name='Dissertation',
        h5_file='/tmp/dissertation.h5',
        created_at=1700000000,
    )
    repo.save(project)

    # The stored row round-trips through YAML.
    loaded = repo.get('dissertation')
    assert loaded is not None
    assert loaded.id == 'dissertation'
    assert loaded.name == 'Dissertation'
    assert loaded.h5_file == '/tmp/dissertation.h5'
    assert loaded.created_at == 1700000000

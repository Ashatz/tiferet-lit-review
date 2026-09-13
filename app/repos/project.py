"""Lit Review Project Catalog Repository"""

# *** imports

# ** core
from pathlib import Path
from time import time
from typing import List, Optional

# ** app
from tiferet.repos.core import ConfigurationRepository

from ..interfaces.project import ProjectService
from ..mappers.project import ProjectAggregate, ProjectConfigObject

# *** constants

# ** constant: default_project_config
DEFAULT_PROJECT_CONFIG = '.lit_review/projects.yml'

# ** constant: default_project_id
DEFAULT_PROJECT_ID = 'default'

# ** constant: default_project_name
DEFAULT_PROJECT_NAME = 'Default'

# ** constant: default_h5_file
DEFAULT_H5_FILE = '.lit_review/lit_review.h5'

# *** repos

# ** repo: project_config_repository
class ProjectConfigRepository(ProjectService, ConfigurationRepository):
    '''
    YAML-backed catalog of named research stores.

    The catalog lives under ``.lit_review/`` and is never written into a
    project HDF5 file. First-run and legacy bootstrap seed project id
    ``default`` pointing at ``.lit_review/lit_review.h5``.
    '''

    # * init
    def __init__(self,
            project_config: str = DEFAULT_PROJECT_CONFIG,
            encoding: str = 'utf-8',
        ) -> None:
        '''
        Initialize the project catalog repository.

        :param project_config: Path to the projects YAML file.
        :type project_config: str
        :param encoding: File encoding.
        :type encoding: str
        '''

        # Initialize the configuration repository base.
        ConfigurationRepository.__init__(
            self,
            config_file=project_config,
            encoding=encoding,
        )

    # * method: _seed_default
    def _seed_default(self) -> None:
        '''
        Write the default catalog row so an existing store stays reachable.
        '''

        # Build the default catalog record pointing at the legacy store path.
        default_project = ProjectAggregate(
            id=DEFAULT_PROJECT_ID,
            name=DEFAULT_PROJECT_NAME,
            h5_file=DEFAULT_H5_FILE,
            created_at=int(time()),
        )

        # Persist only the default row; do not open the research-graph store.
        Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
        self._save({
            'projects': {
                DEFAULT_PROJECT_ID: ProjectConfigObject.from_model(
                    default_project,
                ).to_primitive(self.default_role),
            },
        })

    # * method: _ensure_catalog
    def _ensure_catalog(self) -> dict:
        '''
        Return the projects mapping, seeding ``default`` when the catalog is empty.

        :return: The projects mapping keyed by project id.
        :rtype: dict
        '''

        # Seed the catalog when the YAML file has not been created yet.
        catalog_path = Path(self.config_file)
        if not catalog_path.exists():
            self._seed_default()

        # Load the projects mapping, treating a missing section as empty.
        projects_data = self._load(
            start_node=lambda data: (data or {}).get('projects', {}) or {},
        )

        # Seed default when an existing file has no catalog rows.
        if not projects_data:
            self._seed_default()
            projects_data = self._load(
                start_node=lambda data: (data or {}).get('projects', {}) or {},
            )

        # Return the catalog mapping.
        return projects_data

    # * method: exists
    def exists(self, id: str) -> bool:
        '''
        Check whether a project with the given ID exists in the catalog.

        :param id: The project identifier.
        :type id: str
        :return: True if the project exists, otherwise False.
        :rtype: bool
        '''

        # Bootstrap the catalog, then probe the mapping key.
        projects_data = self._ensure_catalog()
        return id in projects_data

    # * method: get
    def get(self, id: str) -> Optional[ProjectAggregate]:
        '''
        Retrieve a Project by its ID.

        :param id: The project identifier.
        :type id: str
        :return: The project aggregate, or None if not found.
        :rtype: Optional[ProjectAggregate]
        '''

        # Bootstrap the catalog, then load the named row.
        projects_data = self._ensure_catalog()
        project_data = projects_data.get(id)
        if not project_data:
            return None

        # Map the YAML entry, injecting the mapping key as id.
        return ProjectConfigObject.model_validate(
            {**project_data, 'id': id},
        ).map()

    # * method: list
    def list(self) -> List[ProjectAggregate]:
        '''
        List all Project catalog records.

        :return: All stored project aggregates.
        :rtype: List[ProjectAggregate]
        '''

        # Bootstrap the catalog, then map every row.
        projects_data = self._ensure_catalog()
        return [
            ProjectConfigObject.model_validate(
                {**project_data, 'id': project_id},
            ).map()
            for project_id, project_data in projects_data.items()
        ]

    # * method: save
    def save(self, project: ProjectAggregate) -> None:
        '''
        Persist a Project catalog record.

        :param project: The project aggregate to persist.
        :type project: ProjectAggregate
        '''

        # Convert the aggregate to configuration data.
        project_data = ProjectConfigObject.from_model(project)

        # Load the full catalog file when it exists; otherwise start empty.
        catalog_path = Path(self.config_file)
        if catalog_path.exists():
            full_data = self._load() or {}
        else:
            full_data = {}

        # Insert or update the project entry.
        full_data.setdefault('projects', {})[project.id] = project_data.to_primitive(
            self.default_role,
        )

        # Persist the updated catalog.
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        self._save(full_data)

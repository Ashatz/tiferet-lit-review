"""Lit Review Project Domain Model"""

# *** imports

# ** core
from time import time

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** constants

# ** constant: default_project_id
DEFAULT_PROJECT_ID = 'default'

# ** constant: default_project_name
DEFAULT_PROJECT_NAME = 'Default'

# ** constant: default_h5_file
DEFAULT_H5_FILE = '.lit_review/lit_review.h5'

# *** models

# ** model: project
class Project(DomainObject):
    '''
    A named handle for which HDF5 research store a request reads and writes.

    Project is a catalog noun, not a research-graph noun. It does not
    participate in sources, citations, themes, or linkages.
    '''

    # * attribute: id
    id: str = Field(
        ...,
        description='The unique project identifier (e.g. "default").',
    )

    # * attribute: name
    name: str = Field(
        ...,
        description='The human-readable project name.',
    )

    # * attribute: h5_file
    h5_file: str = Field(
        ...,
        description='Filesystem path to this project\'s HDF5 research store.',
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )

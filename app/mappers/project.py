"""Lit Review Project Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict

# ** app
from tiferet.mappers.core import Aggregate, TransferObject

from ..domain.project import Project

# *** mappers

# ** mapper: project_aggregate
class ProjectAggregate(Project, Aggregate):
    '''
    Mutable aggregate for the Project catalog record.
    '''


# ** mapper: project_config_object
class ProjectConfigObject(Project, TransferObject):
    '''
    YAML configuration representation of a Project catalog record.

    id is the YAML mapping key, so it is excluded from to_data.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_data': {
            'exclude': {'id'},
        },
    }

    # * method: map
    def map(self, **overrides) -> ProjectAggregate:
        '''
        Map the configuration data to a ProjectAggregate.

        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The project aggregate.
        :rtype: ProjectAggregate
        '''

        # Map to the catalog aggregate.
        return super().map(ProjectAggregate, **overrides)

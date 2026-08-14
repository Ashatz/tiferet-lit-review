"""Lit Review Theme Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict, List, Optional

# ** infra
from pydantic import Field
from tiferet_h5 import NodeObject

# ** app
from tiferet.mappers.core import Aggregate, TransferObject

from ..domain.citation import Citation
from ..domain.theme import Theme

# *** mappers

# ** mapper: theme_aggregate
class ThemeAggregate(Theme, Aggregate):
    '''
    Mutable aggregate for the Theme domain object.
    '''

    # * method: update_synthesis
    def update_synthesis(self, synthesized_description: str, linkage_count: int) -> None:
        '''
        Update the theme's synthesized description and denormalized linkage count.

        :param synthesized_description: The new synthesis text.
        :type synthesized_description: str
        :param linkage_count: The updated number of linkages on this theme.
        :type linkage_count: int
        '''

        # Apply both synthesis fields through validated mutation.
        self.set_attribute('synthesized_description', synthesized_description)
        self.set_attribute('linkage_count', linkage_count)


# ** mapper: theme_node_object
class ThemeNodeObject(Theme, NodeObject):
    '''
    HDF5 node mapper for Theme: one HDF5 group per theme, with theme fields
    stored as node attributes.
    '''


# ** mapper: theme_response
class ThemeResponse(Theme, TransferObject):
    '''
    Transfer object for theme CLI/API responses.

    Extends Theme so the synthesis fields serialize natively; adds the linked
    citations when a show/display needs more than the theme itself.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_data': {
            'exclude': {'created_at'},
        },
    }

    # * attribute: citations
    citations: List[Citation] = Field(
        default_factory=list,
        description='Linked citations included on show/display responses.',
    )

    # * method: from_aggregate (static)
    @staticmethod
    def from_aggregate(
            theme: ThemeAggregate,
            citations: Optional[List[Citation]] = None,
        ) -> 'ThemeResponse':
        '''
        Map a ThemeAggregate into a ThemeResponse.

        :param theme: The theme aggregate to map.
        :type theme: ThemeAggregate
        :param citations: Optional linked citations to include on the response.
        :type citations: Optional[List[Citation]]
        :return: The theme response transfer object.
        :rtype: ThemeResponse
        '''

        # Delegate to TransferObject.from_model, attaching citations when given.
        return ThemeResponse.from_model(
            theme,
            citations=citations or [],
        )

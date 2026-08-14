"""Lit Review Theme Mappers"""

# *** imports

# ** infra
from tiferet_h5 import NodeObject

# ** app
from tiferet.mappers.core import Aggregate

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

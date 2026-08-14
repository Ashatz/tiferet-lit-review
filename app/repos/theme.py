"""Lit Review Theme H5 Repository"""

# *** imports

# ** core
from typing import List, Optional

# ** infra
from tiferet_h5 import H5Repository

# ** app
from ..interfaces.theme import ThemeService
from ..mappers.theme import ThemeAggregate, ThemeNodeObject

# *** constants

# ** constant: themes_group_path
THEMES_GROUP_PATH = '/lit_review/themes'

# *** repos

# ** repo: theme_h5_repository
class ThemeH5Repository(ThemeService, H5Repository):
    '''
    HDF5 node-based repository for Theme domain objects. One HDF5 group per
    theme, at THEMES_GROUP_PATH/<theme_id>, with theme fields stored as node
    attributes.
    '''

    # * init
    def __init__(self, h5_file: str, mode: str = 'a') -> None:
        '''
        Initialize the theme H5 repository.

        :param h5_file: Path to the shared lit_review HDF5 file.
        :type h5_file: str
        :param mode: Default PyTables open mode.
        :type mode: str
        '''

        # Initialize the H5 repository base.
        H5Repository.__init__(self, h5_file=h5_file, mode=mode)

    # * method: exists
    def exists(self, id: str) -> bool:
        '''
        Check whether a theme with the given ID exists.

        :param id: The theme identifier.
        :type id: str
        :return: True if the theme exists, otherwise False.
        :rtype: bool
        '''

        # Check for the theme's group node.
        with self.client() as h5:
            return h5.node_exists(f'{THEMES_GROUP_PATH}/{id}')

    # * method: get
    def get(self, id: str) -> Optional[ThemeAggregate]:
        '''
        Retrieve a Theme by its ID.

        :param id: The theme identifier.
        :type id: str
        :return: The theme aggregate, or None if not found.
        :rtype: Optional[ThemeAggregate]
        '''

        # Read the theme's node attributes, guarding against a missing node.
        path = f'{THEMES_GROUP_PATH}/{id}'
        with self.client() as h5:
            if not h5.node_exists(path):
                return None
            attrs = h5.get_node_attrs(path)

        # Map the attributes to a theme aggregate.
        return ThemeNodeObject.from_attrs(attrs).map(ThemeAggregate)

    # * method: list
    def list(self, name: Optional[str] = None) -> List[ThemeAggregate]:
        '''
        List themes, optionally filtered by name.

        :param name: Optional theme name to match exactly.
        :type name: Optional[str]
        :return: The matching theme aggregates.
        :rtype: List[ThemeAggregate]
        '''

        # Iterate the child groups of the themes group, if it exists.
        with self.client() as h5:
            if not h5.node_exists(THEMES_GROUP_PATH):
                return []
            group = h5.get_group(THEMES_GROUP_PATH)
            themes = [
                ThemeNodeObject.from_attrs(
                    h5.get_node_attrs(f'{THEMES_GROUP_PATH}/{child_name}')
                ).map(ThemeAggregate)
                for child_name in group._v_children
            ]

        # Apply the optional exact-name filter.
        if name is not None:
            themes = [theme for theme in themes if theme.name == name]

        # Return the mapped theme aggregates.
        return themes

    # * method: save
    def save(self, theme: ThemeAggregate) -> None:
        '''
        Persist a Theme aggregate.

        :param theme: The theme aggregate to persist.
        :type theme: ThemeAggregate
        '''

        # Serialize the theme to node attributes.
        path = f'{THEMES_GROUP_PATH}/{theme.id}'
        attrs = ThemeNodeObject.from_model(theme).to_attrs()

        # Ensure the group exists, then write each attribute.
        with self.client() as h5:
            if not h5.node_exists(path):
                h5.create_group(path)
            for name, value in attrs.items():
                h5.set_node_attr(path, name, value)

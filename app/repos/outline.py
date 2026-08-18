"""Lit Review Outline H5 Repository"""

# *** imports

# ** core
from typing import List, Optional

# ** infra
from tiferet_h5 import H5Repository

# ** app
from ..interfaces.outline import OutlineService
from ..mappers.outline import OutlineAggregate, OutlineNodeObject

# *** constants

# ** constant: outlines_group_path
OUTLINES_GROUP_PATH = '/lit_review/outlines'

# *** repos

# ** repo: outline_h5_repository
class OutlineH5Repository(OutlineService, H5Repository):
    '''
    HDF5 node-based repository for Outline aggregates. One HDF5 group per
    outline, at OUTLINES_GROUP_PATH/<outline_id>, with outline fields
    and owned slots stored as node attributes.
    '''

    # * init
    def __init__(self, h5_file: str, mode: str = 'a') -> None:
        '''
        Initialize the outline H5 repository.

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
        Check whether an outline with the given ID exists.

        :param id: The outline identifier.
        :type id: str
        :return: True if the outline exists, otherwise False.
        :rtype: bool
        '''

        # Check for the outline's group node.
        with self.client() as h5:
            return h5.node_exists(f'{OUTLINES_GROUP_PATH}/{id}')

    # * method: get
    def get(self, id: str) -> Optional[OutlineAggregate]:
        '''
        Retrieve an Outline by its ID, including owned slots.

        :param id: The outline identifier.
        :type id: str
        :return: The outline aggregate, or None if not found.
        :rtype: Optional[OutlineAggregate]
        '''

        # Read the outline's node attributes, guarding against a missing node.
        path = f'{OUTLINES_GROUP_PATH}/{id}'
        with self.client() as h5:
            if not h5.node_exists(path):
                return None
            attrs = h5.get_node_attrs(path)

        # Map the attributes to an outline aggregate, restoring owned slots.
        return OutlineNodeObject.from_attrs(attrs).map(OutlineAggregate)

    # * method: list
    def list(self,
            title: Optional[str] = None,
            theme_id: Optional[str] = None,
        ) -> List[OutlineAggregate]:
        '''
        List outlines, optionally filtered by title or included theme.

        :param title: Optional outline title to match exactly.
        :type title: Optional[str]
        :param theme_id: Optional theme identifier included in a slot.
        :type theme_id: Optional[str]
        :return: The matching outline aggregates.
        :rtype: List[OutlineAggregate]
        '''

        # Iterate the child groups of the outlines group, if it exists.
        with self.client() as h5:
            if not h5.node_exists(OUTLINES_GROUP_PATH):
                return []
            group = h5.get_group(OUTLINES_GROUP_PATH)
            outlines = [
                OutlineNodeObject.from_attrs(
                    h5.get_node_attrs(f'{OUTLINES_GROUP_PATH}/{child_name}')
                ).map(OutlineAggregate)
                for child_name in group._v_children
            ]

        # Apply the optional exact-title filter.
        if title is not None:
            outlines = [
                outline for outline in outlines if outline.title == title
            ]

        # Apply the optional included-theme filter.
        if theme_id is not None:
            outlines = [
                outline for outline in outlines
                if any(slot.theme_id == theme_id for slot in outline.slots)
            ]

        # Return the mapped outline aggregates.
        return outlines

    # * method: save
    def save(self, outline: OutlineAggregate) -> None:
        '''
        Persist an Outline aggregate, including its owned slots.

        :param outline: The outline aggregate to persist.
        :type outline: OutlineAggregate
        '''

        # Serialize the outline to node attributes.
        path = f'{OUTLINES_GROUP_PATH}/{outline.id}'
        attrs = OutlineNodeObject.from_model(outline).to_attrs()

        # Ensure the group exists, then write each attribute.
        with self.client() as h5:
            if not h5.node_exists(path):
                h5.create_group(path)
            for name, value in attrs.items():
                h5.set_node_attr(path, name, value)

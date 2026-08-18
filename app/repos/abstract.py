"""Lit Review Abstract H5 Repository"""

# *** imports

# ** core
from typing import List, Optional

# ** infra
from tiferet_h5 import H5Repository

# ** app
from ..interfaces.abstract import AbstractService
from ..mappers.abstract import AbstractAggregate, AbstractNodeObject

# *** constants

# ** constant: abstracts_group_path
ABSTRACTS_GROUP_PATH = '/lit_review/abstracts'

# *** repos

# ** repo: abstract_h5_repository
class AbstractH5Repository(AbstractService, H5Repository):
    '''
    HDF5 node-based repository for Abstract aggregates. One HDF5 group per
    abstract, at ABSTRACTS_GROUP_PATH/<abstract_id>, with abstract fields
    and owned theme joins stored as node attributes.
    '''

    # * init
    def __init__(self, h5_file: str, mode: str = 'a') -> None:
        '''
        Initialize the abstract H5 repository.

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
        Check whether an abstract with the given ID exists.

        :param id: The abstract identifier.
        :type id: str
        :return: True if the abstract exists, otherwise False.
        :rtype: bool
        '''

        # Check for the abstract's group node.
        with self.client() as h5:
            return h5.node_exists(f'{ABSTRACTS_GROUP_PATH}/{id}')

    # * method: get
    def get(self, id: str) -> Optional[AbstractAggregate]:
        '''
        Retrieve an Abstract by its ID, including owned theme joins.

        :param id: The abstract identifier.
        :type id: str
        :return: The abstract aggregate, or None if not found.
        :rtype: Optional[AbstractAggregate]
        '''

        # Read the abstract's node attributes, guarding against a missing node.
        path = f'{ABSTRACTS_GROUP_PATH}/{id}'
        with self.client() as h5:
            if not h5.node_exists(path):
                return None
            attrs = h5.get_node_attrs(path)

        # Map the attributes to an abstract aggregate, restoring owned joins.
        return AbstractNodeObject.from_attrs(attrs).map(AbstractAggregate)

    # * method: list
    def list(self,
            name: Optional[str] = None,
            theme_id: Optional[str] = None,
        ) -> List[AbstractAggregate]:
        '''
        List abstracts, optionally filtered by name or included theme.

        :param name: Optional abstract name to match exactly.
        :type name: Optional[str]
        :param theme_id: Optional theme identifier included in the abstract.
        :type theme_id: Optional[str]
        :return: The matching abstract aggregates.
        :rtype: List[AbstractAggregate]
        '''

        # Iterate the child groups of the abstracts group, if it exists.
        with self.client() as h5:
            if not h5.node_exists(ABSTRACTS_GROUP_PATH):
                return []
            group = h5.get_group(ABSTRACTS_GROUP_PATH)
            abstracts = [
                AbstractNodeObject.from_attrs(
                    h5.get_node_attrs(f'{ABSTRACTS_GROUP_PATH}/{child_name}')
                ).map(AbstractAggregate)
                for child_name in group._v_children
            ]

        # Apply the optional exact-name filter.
        if name is not None:
            abstracts = [
                abstract for abstract in abstracts if abstract.name == name
            ]

        # Apply the optional included-theme filter.
        if theme_id is not None:
            abstracts = [
                abstract for abstract in abstracts
                if any(theme.theme_id == theme_id for theme in abstract.themes)
            ]

        # Return the mapped abstract aggregates.
        return abstracts

    # * method: save
    def save(self, abstract: AbstractAggregate) -> None:
        '''
        Persist an Abstract aggregate, including its owned theme joins.

        :param abstract: The abstract aggregate to persist.
        :type abstract: AbstractAggregate
        '''

        # Serialize the abstract to node attributes.
        path = f'{ABSTRACTS_GROUP_PATH}/{abstract.id}'
        attrs = AbstractNodeObject.from_model(abstract).to_attrs()

        # Ensure the group exists, then write each attribute.
        with self.client() as h5:
            if not h5.node_exists(path):
                h5.create_group(path)
            for name, value in attrs.items():
                h5.set_node_attr(path, name, value)

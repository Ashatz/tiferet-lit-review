"""Lit Review Source H5 Repository"""

# *** imports

# ** core
from typing import List, Optional

# ** infra
from tiferet_h5 import H5Repository

# ** app
from ..interfaces.source import SourceService
from ..mappers.source import SourceAggregate, SourceNodeObject

# *** constants

# ** constant: sources_group_path
SOURCES_GROUP_PATH = '/lit_review/sources'

# *** repos

# ** repo: source_h5_repository
class SourceH5Repository(SourceService, H5Repository):
    '''
    HDF5 node-based repository for Source domain objects. One HDF5 group per
    source, at SOURCES_GROUP_PATH/<source_id>, with bibliographic fields
    stored as node attributes.
    '''

    # * init
    def __init__(self, h5_file: str, mode: str = 'a') -> None:
        '''
        Initialize the source H5 repository.

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
        Check whether a source with the given ID exists.

        :param id: The source identifier.
        :type id: str
        :return: True if the source exists, otherwise False.
        :rtype: bool
        '''

        # Check for the source's group node.
        with self.client() as h5:
            return h5.node_exists(f'{SOURCES_GROUP_PATH}/{id}')

    # * method: get
    def get(self, id: str) -> Optional[SourceAggregate]:
        '''
        Retrieve a Source by its ID.

        :param id: The source identifier.
        :type id: str
        :return: The source aggregate, or None if not found.
        :rtype: Optional[SourceAggregate]
        '''

        # Read the source's node attributes, guarding against a missing node.
        path = f'{SOURCES_GROUP_PATH}/{id}'
        with self.client() as h5:
            if not h5.node_exists(path):
                return None
            attrs = h5.get_node_attrs(path)

        # Map the attributes to a source aggregate.
        return SourceNodeObject.from_attrs(attrs).map(SourceAggregate)

    # * method: list
    def list(self, **filters) -> List[SourceAggregate]:
        '''
        List all sources.

        :param filters: Unused; sources support no filters at v1.
        :type filters: dict
        :return: All source aggregates.
        :rtype: List[SourceAggregate]
        '''

        # Iterate the child groups of the sources group, if it exists.
        with self.client() as h5:
            if not h5.node_exists(SOURCES_GROUP_PATH):
                return []
            group = h5.get_group(SOURCES_GROUP_PATH)
            sources = [
                SourceNodeObject.from_attrs(
                    h5.get_node_attrs(f'{SOURCES_GROUP_PATH}/{child_name}')
                ).map(SourceAggregate)
                for child_name in group._v_children
            ]

        # Return the mapped source aggregates.
        return sources

    # * method: save
    def save(self, source: SourceAggregate) -> None:
        '''
        Persist a Source aggregate.

        :param source: The source aggregate to persist.
        :type source: SourceAggregate
        '''

        # Serialize the source to node attributes.
        path = f'{SOURCES_GROUP_PATH}/{source.id}'
        attrs = SourceNodeObject.from_model(source).to_attrs()

        # Ensure the group exists, then write each attribute.
        with self.client() as h5:
            if not h5.node_exists(path):
                h5.create_group(path)
            for name, value in attrs.items():
                h5.set_node_attr(path, name, value)

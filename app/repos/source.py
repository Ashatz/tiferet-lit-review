"""Lit Review Source H5 Repository"""

# *** imports

# ** core
from typing import List, Optional

# ** infra
import numpy as np
from tiferet_h5 import H5Repository

# ** app
from ..interfaces.source import SourceService
from ..mappers.source import SourceAggregate, SourceNodeObject

# *** constants

# ** constant: sources_group_path
SOURCES_GROUP_PATH = '/lit_review/sources'

# ** constant: source_document_node_name
SOURCE_DOCUMENT_NODE_NAME = 'document'

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

    # * method: _document_path
    def _document_path(self, source_id: str) -> str:
        '''
        Build the HDF5 path for a source's document array.

        :param source_id: The source identifier.
        :type source_id: str
        :return: The absolute HDF5 array path.
        :rtype: str
        '''

        # Document bytes live under the existing source group.
        return f'{SOURCES_GROUP_PATH}/{source_id}/{SOURCE_DOCUMENT_NODE_NAME}'

    # * method: has_document
    def has_document(self, source_id: str) -> bool:
        '''
        Check whether a source document array exists for the given source.

        :param source_id: The source identifier.
        :type source_id: str
        :return: True if the document array exists, otherwise False.
        :rtype: bool
        '''

        # Probe the array node without reading its contents.
        with self.client() as h5:
            return h5.node_exists(self._document_path(source_id))

    # * method: get_document
    def get_document(self, source_id: str) -> Optional[bytes]:
        '''
        Retrieve the attached source document bytes.

        :param source_id: The source identifier.
        :type source_id: str
        :return: The document bytes, or None if no array is attached.
        :rtype: Optional[bytes]
        '''

        # Return None when the source has no document array.
        path = self._document_path(source_id)
        with self.client() as h5:
            if not h5.node_exists(path):
                return None
            array = h5.get_array(path)
            data = array.read()

        # Normalize the stored uint8 sequence back to raw bytes.
        return np.asarray(data, dtype=np.uint8).tobytes()

    # * method: save_document
    def save_document(self, source_id: str, data: bytes) -> None:
        '''
        Write or replace the source document array for a source.

        :param source_id: The source identifier whose group already exists.
        :type source_id: str
        :param data: The raw document bytes.
        :type data: bytes
        '''

        # Replace-on-reattach: PyTables create_array cannot overwrite a node.
        path = self._document_path(source_id)
        array_data = np.frombuffer(data, dtype=np.uint8)
        with self.client() as h5:
            if h5.node_exists(path):
                h5.h5file.remove_node(path)
            h5.create_array(path, array_data)

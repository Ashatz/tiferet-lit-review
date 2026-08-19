"""Lit Review Paper H5 Repository"""

# *** imports

# ** core
from typing import List, Optional

# ** infra
from tiferet_h5 import H5Repository

# ** app
from ..interfaces.paper import PaperService
from ..mappers.paper import PaperAggregate, PaperNodeObject

# *** constants

# ** constant: papers_group_path
PAPERS_GROUP_PATH = '/lit_review/papers'

# *** repos

# ** repo: paper_h5_repository
class PaperH5Repository(PaperService, H5Repository):
    '''
    HDF5 node-based repository for Paper aggregates. One HDF5 group per
    paper, at PAPERS_GROUP_PATH/<paper_id>, with paper fields and owned
    children stored as node attributes.
    '''

    # * init
    def __init__(self, h5_file: str, mode: str = 'a') -> None:
        '''
        Initialize the paper H5 repository.

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
        Check whether a paper with the given ID exists.

        :param id: The paper identifier.
        :type id: str
        :return: True if the paper exists, otherwise False.
        :rtype: bool
        '''

        # Check for the paper's group node.
        with self.client() as h5:
            return h5.node_exists(f'{PAPERS_GROUP_PATH}/{id}')

    # * method: get
    def get(self, id: str) -> Optional[PaperAggregate]:
        '''
        Retrieve a Paper by its ID, including owned children.

        :param id: The paper identifier.
        :type id: str
        :return: The paper aggregate, or None if not found.
        :rtype: Optional[PaperAggregate]
        '''

        # Read the paper's node attributes, guarding against a missing node.
        path = f'{PAPERS_GROUP_PATH}/{id}'
        with self.client() as h5:
            if not h5.node_exists(path):
                return None
            attrs = h5.get_node_attrs(path)

        # Map the attributes to a paper aggregate, restoring owned children.
        return PaperNodeObject.from_attrs(attrs).map(PaperAggregate)

    # * method: list
    def list(self,
            title: Optional[str] = None,
            outline_id: Optional[str] = None,
        ) -> List[PaperAggregate]:
        '''
        List papers, optionally filtered by title or origin outline.

        :param title: Optional paper title to match exactly.
        :type title: Optional[str]
        :param outline_id: Optional origin outline identifier.
        :type outline_id: Optional[str]
        :return: The matching paper aggregates.
        :rtype: List[PaperAggregate]
        '''

        # Iterate the child groups of the papers group, if it exists.
        with self.client() as h5:
            if not h5.node_exists(PAPERS_GROUP_PATH):
                return []
            group = h5.get_group(PAPERS_GROUP_PATH)
            papers = [
                PaperNodeObject.from_attrs(
                    h5.get_node_attrs(f'{PAPERS_GROUP_PATH}/{child_name}')
                ).map(PaperAggregate)
                for child_name in group._v_children
            ]

        # Apply the optional exact-title filter.
        if title is not None:
            papers = [paper for paper in papers if paper.title == title]

        # Apply the optional origin-outline filter.
        if outline_id is not None:
            papers = [
                paper for paper in papers if paper.outline_id == outline_id
            ]

        # Return the mapped paper aggregates.
        return papers

    # * method: save
    def save(self, paper: PaperAggregate) -> None:
        '''
        Persist a Paper aggregate, including its owned children.

        :param paper: The paper aggregate to persist.
        :type paper: PaperAggregate
        '''

        # Serialize the paper to node attributes.
        path = f'{PAPERS_GROUP_PATH}/{paper.id}'
        attrs = PaperNodeObject.from_model(paper).to_attrs()

        # Ensure the group exists, then write each attribute.
        with self.client() as h5:
            if not h5.node_exists(path):
                h5.create_group(path)
            for name, value in attrs.items():
                h5.set_node_attr(path, name, value)

"""Lit Review Citation H5 Repository"""

# *** imports

# ** core
from typing import List, Optional

# ** infra
from tiferet_h5 import H5Repository

# ** app
from ..interfaces.citation import CitationService
from ..mappers.citation import CitationAggregate, CitationTableObject

# *** constants

# ** constant: citations_table_path
CITATIONS_TABLE_PATH = '/lit_review/citations'

# *** repos

# ** repo: citation_h5_repository
class CitationH5Repository(CitationService, H5Repository):
    '''
    HDF5 table-based repository for Citation domain objects. One PyTables row
    per citation, in a single table at CITATIONS_TABLE_PATH.

    Filtering (by id or source_id) is done in-memory over read_rows results.
    Acceptable at v1 scale (a single researcher's working set); revisit if the
    citations table grows large enough to warrant an in-kernel query.

    ``save`` is an id-based upsert: an existing row with the same id is
    overwritten in place; otherwise a new row is appended.
    '''

    # * init
    def __init__(self, h5_file: str, mode: str = 'a') -> None:
        '''
        Initialize the citation H5 repository.

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
        Check whether a citation with the given ID exists.

        :param id: The citation identifier.
        :type id: str
        :return: True if the citation exists, otherwise False.
        :rtype: bool
        '''

        # Delegate to get and check for None.
        return self.get(id) is not None

    # * method: get
    def get(self, id: str) -> Optional[CitationAggregate]:
        '''
        Retrieve a Citation by its ID.

        :param id: The citation identifier.
        :type id: str
        :return: The citation aggregate, or None if not found.
        :rtype: Optional[CitationAggregate]
        '''

        # Read all rows and find the matching one in-memory.
        with self.client() as h5:
            if not h5.node_exists(CITATIONS_TABLE_PATH):
                return None
            rows = h5.read_rows(CITATIONS_TABLE_PATH)

        # Find the matching row by id.
        match = next((row for row in rows if row.get('id') == id), None)
        if match is None:
            return None

        # Map the matching row to a citation aggregate.
        return CitationTableObject.from_row(match).map(CitationAggregate)

    # * method: list
    def list(self, **filters) -> List[CitationAggregate]:
        '''
        List citations, optionally filtered by source_id.

        :param filters: Accepts an optional source_id filter.
        :type filters: dict
        :return: The matching citation aggregates, in insertion order.
        :rtype: List[CitationAggregate]
        '''

        # Read all rows, guarding against a missing table.
        with self.client() as h5:
            if not h5.node_exists(CITATIONS_TABLE_PATH):
                return []
            rows = h5.read_rows(CITATIONS_TABLE_PATH)

        # Apply the optional source_id filter in-memory.
        source_id = filters.get('source_id')
        if source_id is not None:
            rows = [row for row in rows if row.get('source_id') == source_id]

        # Map each row to a citation aggregate, preserving insertion order.
        return [CitationTableObject.from_row(row).map(CitationAggregate) for row in rows]

    # * method: save
    def save(self, citation: CitationAggregate) -> None:
        '''
        Persist a Citation aggregate as an id-based upsert.

        When a row with the same id already exists it is overwritten in place
        via indexed column assignment; otherwise a new row is appended.

        :param citation: The citation aggregate to persist.
        :type citation: CitationAggregate
        '''

        # Serialize the citation to a table object and a plain field dict.
        table_object = CitationTableObject.from_model(citation)
        data = table_object.model_dump(by_alias=True)

        # Get or create the table, then update-or-append by id.
        with self.client() as h5:
            table = h5.get_or_create_table(
                CITATIONS_TABLE_PATH,
                CitationTableObject.get_description(),
            )

            # Compare against the encoded id so StringCol bytes match.
            target_id = CitationTableObject.encode_value(
                citation.id,
                CitationTableObject._H5_TYPES['id'],
            )

            # Prefer indexed column writes; Row.update() during iterrows is
            # not reliably persisted by PyTables for this path.
            for index in range(table.nrows):
                if table.cols.id[index] != target_id:
                    continue
                for name, col in CitationTableObject._H5_TYPES.items():
                    getattr(table.cols, name)[index] = (
                        CitationTableObject.encode_value(data.get(name), col)
                    )
                table.flush()
                return

            # No existing row — append a new one.
            table_object.to_row(table)
            table.flush()

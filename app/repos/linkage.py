"""Lit Review Linkage H5 Repository"""

# *** imports

# ** core
from typing import List, Optional

# ** infra
from tiferet_h5 import H5Repository

# ** app
from ..interfaces.linkage import LinkageService
from ..mappers.linkage import LinkageAggregate, LinkageTableObject

# *** constants

# ** constant: linkages_table_path
LINKAGES_TABLE_PATH = '/lit_review/linkages'

# *** repos

# ** repo: linkage_h5_repository
class LinkageH5Repository(LinkageService, H5Repository):
    '''
    HDF5 table-based repository for Linkage domain objects. One PyTables row
    per linkage, in a single table at LINKAGES_TABLE_PATH.

    Filtering (by id, theme_id, or citation_id) is done in-memory over
    read_rows results. Acceptable at v1 scale.

    ``save`` is an id-based upsert: an existing row with the same id is
    overwritten in place; otherwise a new row is appended.
    '''

    # * init
    def __init__(self, h5_file: str, mode: str = 'a') -> None:
        '''
        Initialize the linkage H5 repository.

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
        Check whether a linkage with the given ID exists.

        :param id: The linkage identifier.
        :type id: str
        :return: True if the linkage exists, otherwise False.
        :rtype: bool
        '''

        # Delegate to get and check for None.
        return self.get(id) is not None

    # * method: get
    def get(self, id: str) -> Optional[LinkageAggregate]:
        '''
        Retrieve a Linkage by its ID.

        :param id: The linkage identifier.
        :type id: str
        :return: The linkage aggregate, or None if not found.
        :rtype: Optional[LinkageAggregate]
        '''

        # Read all rows and find the matching one in-memory.
        with self.client() as h5:
            if not h5.node_exists(LINKAGES_TABLE_PATH):
                return None
            rows = h5.read_rows(LINKAGES_TABLE_PATH)

        # Find the matching row by id.
        match = next((row for row in rows if row.get('id') == id), None)
        if match is None:
            return None

        # Map the matching row to a linkage aggregate.
        return LinkageTableObject.from_row(match).map(LinkageAggregate)

    # * method: list
    def list(self,
            theme_id: Optional[str] = None,
            citation_id: Optional[str] = None,
        ) -> List[LinkageAggregate]:
        '''
        List linkages, optionally filtered by theme and/or citation.

        :param theme_id: Optional theme identifier to match.
        :type theme_id: Optional[str]
        :param citation_id: Optional citation identifier to match.
        :type citation_id: Optional[str]
        :return: The matching linkage aggregates, in insertion order.
        :rtype: List[LinkageAggregate]
        '''

        # Read all rows, guarding against a missing table.
        with self.client() as h5:
            if not h5.node_exists(LINKAGES_TABLE_PATH):
                return []
            rows = h5.read_rows(LINKAGES_TABLE_PATH)

        # Apply the optional theme and citation filters in-memory.
        if theme_id is not None:
            rows = [row for row in rows if row.get('theme_id') == theme_id]
        if citation_id is not None:
            rows = [row for row in rows if row.get('citation_id') == citation_id]

        # Map each row to a linkage aggregate, preserving insertion order.
        return [LinkageTableObject.from_row(row).map(LinkageAggregate) for row in rows]

    # * method: save
    def save(self, linkage: LinkageAggregate) -> None:
        '''
        Persist a Linkage aggregate as an id-based upsert.

        When a row with the same id already exists it is overwritten in place
        via indexed column assignment; otherwise a new row is appended.

        :param linkage: The linkage aggregate to persist.
        :type linkage: LinkageAggregate
        '''

        # Serialize the linkage to a table object and a plain field dict.
        table_object = LinkageTableObject.from_model(linkage)
        data = table_object.model_dump(by_alias=True)

        # Get or create the table, then update-or-append by id.
        with self.client() as h5:
            table = h5.get_or_create_table(
                LINKAGES_TABLE_PATH,
                LinkageTableObject.get_description(),
            )

            # Migrate a table predating the RFP-7 retirement columns so
            # writes to an older store do not fail against a stale schema.
            table = self._migrate_schema(h5, table)

            # Compare against the encoded id so StringCol bytes match.
            target_id = LinkageTableObject.encode_value(
                linkage.id,
                LinkageTableObject._H5_TYPES['id'],
            )

            # Prefer indexed column writes; Row.update() during iterrows is
            # not reliably persisted by PyTables for this path.
            for index in range(table.nrows):
                if table.cols.id[index] != target_id:
                    continue
                for name, col in LinkageTableObject._H5_TYPES.items():
                    getattr(table.cols, name)[index] = (
                        LinkageTableObject.encode_value(data.get(name), col)
                    )
                table.flush()
                return

            # No existing row — append a new one.
            table_object.to_row(table)
            table.flush()

    # * method: _migrate_schema
    def _migrate_schema(self, h5, table):
        '''
        Recreate the linkages table under the current schema when an older
        on-disk table is missing a newly declared column.

        Existing rows are re-appended through LinkageTableObject, so any
        column absent from the old schema falls back to its Linkage domain
        default (e.g. retired_at defaults to None, i.e. active) -- every
        pre-RFP-7 linkage was made as live evidence.

        :param h5: The open H5Client for this operation.
        :type h5: H5Client
        :param table: The current linkages table (old or current schema).
        :type table: Any
        :return: The table under the current schema.
        :rtype: Any
        '''

        # No migration needed once the schema already matches.
        if not LinkageTableObject.verify_schema(table):
            return table

        # Preserve existing rows, then drop and recreate the table.
        existing_rows = h5.read_rows(LINKAGES_TABLE_PATH)
        h5.h5file.remove_node(LINKAGES_TABLE_PATH)
        table = h5.create_table(LINKAGES_TABLE_PATH, LinkageTableObject.get_description())

        # Re-append each row; columns absent from the old schema fall back
        # to Linkage domain defaults during from_row's model_validate.
        for row in existing_rows:
            LinkageTableObject.from_row(row).to_row(table)
        table.flush()

        return table

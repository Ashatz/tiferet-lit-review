"""Lit Review Citation H5 Repository"""

# *** imports

# ** core
from typing import Any, Dict, List, Optional

# ** infra
from tiferet_h5 import H5Repository

# ** app
from ..interfaces.citation import CitationService
from ..mappers.citation import CitationAggregate, CitationTableObject

# *** constants

# ** constant: citations_group_path
CITATIONS_GROUP_PATH = '/lit_review'

# ** constant: citations_table_leaf
CITATIONS_TABLE_LEAF = 'citations'

# ** constant: citations_table_path
CITATIONS_TABLE_PATH = f'{CITATIONS_GROUP_PATH}/{CITATIONS_TABLE_LEAF}'

# ** constant: citations_staging_leaf
CITATIONS_STAGING_LEAF = 'citations_upgrade_staging'

# ** constant: citations_staging_path
CITATIONS_STAGING_PATH = f'{CITATIONS_GROUP_PATH}/{CITATIONS_STAGING_LEAF}'

# ** constant: citations_backup_leaf
CITATIONS_BACKUP_LEAF = 'citations_upgrade_backup'

# ** constant: citations_backup_path
CITATIONS_BACKUP_PATH = f'{CITATIONS_GROUP_PATH}/{CITATIONS_BACKUP_LEAF}'

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
            # A save is the only path that requires the current schema (get
            # and list tolerate a missing column via the Citation field
            # default), so the upgrade is checked here rather than on read.
            self._ensure_current_schema(h5)

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

    # * method: _ensure_current_schema
    def _ensure_current_schema(self, h5: Any) -> None:
        '''
        Guarantee the live citations table matches the current schema.

        Runs any pending recovery from an interrupted prior upgrade first,
        discards a stale staging table left by an upgrade that never reached
        the backup-rename step, then upgrades a legacy (title-less) table.
        Recovery and rollback can themselves leave the live table on the old
        schema, so the schema check always runs last.

        :param h5: The open H5Client for this operation.
        :type h5: Any
        '''

        # Finish or roll back a prior upgrade that did not reach completion.
        if h5.node_exists(CITATIONS_BACKUP_PATH):
            self._recover_from_interrupted_upgrade(h5)
        elif h5.node_exists(CITATIONS_STAGING_PATH):
            h5.h5file.remove_node(CITATIONS_STAGING_PATH)

        # No live table yet — get_or_create_table builds one on the current
        # schema directly, so there is nothing to upgrade.
        if not h5.node_exists(CITATIONS_TABLE_PATH):
            return

        # Upgrade in place when the live table predates a declared column.
        table = h5.get_table(CITATIONS_TABLE_PATH)
        if CitationTableObject.verify_schema(table):
            self._upgrade_legacy_table(h5)

    # * method: _recover_from_interrupted_upgrade
    def _recover_from_interrupted_upgrade(self, h5: Any) -> None:
        '''
        Resume or roll back an upgrade that was interrupted mid-flight.

        A backup node's presence means a prior upgrade renamed the legacy
        table aside and did not finish. Three states are distinguishable:
        promotion already completed (the live table exists again -- verify
        and drop the backup); promotion never happened but a valid staging
        table survives (finish promoting it); or staging is missing or does
        not match the backup (discard it and restore the legacy table).

        :param h5: The open H5Client for this operation.
        :type h5: Any
        '''

        # Snapshot the backup's rows; every branch below compares against them.
        backup_rows = h5.read_rows(CITATIONS_BACKUP_PATH)

        # The live table already exists: a prior run promoted staging but was
        # interrupted before cleaning up the backup. Verify, then clean up.
        if h5.node_exists(CITATIONS_TABLE_PATH):
            self._assert_row_parity(
                h5.read_rows(CITATIONS_TABLE_PATH),
                backup_rows,
                context='recovery: promoted table vs. backup',
            )
            h5.h5file.remove_node(CITATIONS_BACKUP_PATH)
            return

        # The live table is missing: promotion was interrupted before or
        # during the staging-to-live rename. Finish it when staging is intact.
        if h5.node_exists(CITATIONS_STAGING_PATH):
            staging_rows = h5.read_rows(CITATIONS_STAGING_PATH)
            if self._row_ids(staging_rows) == self._row_ids(backup_rows) and \
                    len(staging_rows) == len(backup_rows):
                h5.h5file.rename_node(CITATIONS_STAGING_PATH, CITATIONS_TABLE_LEAF)
                h5.h5file.remove_node(CITATIONS_BACKUP_PATH)
                return

            # Staging is present but does not match the backup; it cannot be
            # trusted, so discard it and fall through to the restore below.
            h5.h5file.remove_node(CITATIONS_STAGING_PATH)

        # No usable staging table — restore the legacy table from the backup
        # so the caller's schema check retries the upgrade from a clean state.
        h5.h5file.rename_node(CITATIONS_BACKUP_PATH, CITATIONS_TABLE_LEAF)

    # * method: _upgrade_legacy_table
    def _upgrade_legacy_table(self, h5: Any) -> None:
        '''
        Upgrade the live citations table to the current schema in place.

        Every legacy row is copied into a staging table built on the current
        schema and verified there before the legacy table is displaced. The
        legacy table is kept as a recoverable backup until the promoted
        table is verified a second time, so an interruption at any point
        leaves either the untouched legacy table, a discardable staging
        table, or a recoverable backup -- never a silent loss.

        :param h5: The open H5Client for this operation.
        :type h5: Any
        :raises RuntimeError: If the copied or promoted table does not carry
            every legacy row exactly once.
        '''

        # Snapshot every legacy row before the schema changes at all.
        legacy_rows = h5.read_rows(CITATIONS_TABLE_PATH)

        # Build the staging table on the current (title-aware) schema. A
        # column absent from a legacy row falls back to its Citation domain
        # default (title=None) during from_row's model_validate.
        staging_table = h5.create_table(
            CITATIONS_STAGING_PATH,
            CitationTableObject.get_description(),
        )
        for row in legacy_rows:
            CitationTableObject.from_row(row).to_row(staging_table)
        staging_table.flush()

        # Verify staging carries every legacy row before touching the legacy
        # table; a mismatch here leaves the legacy table completely untouched.
        self._assert_row_parity(
            h5.read_rows(CITATIONS_STAGING_PATH),
            legacy_rows,
            context='upgrade: staging vs. legacy',
        )

        # Displace the legacy table into a recoverable backup, then promote
        # the verified staging table into the live path.
        h5.h5file.rename_node(CITATIONS_TABLE_PATH, CITATIONS_BACKUP_LEAF)
        h5.h5file.rename_node(CITATIONS_STAGING_PATH, CITATIONS_TABLE_LEAF)

        # Verify the promoted table once more before discarding the backup.
        self._assert_row_parity(
            h5.read_rows(CITATIONS_TABLE_PATH),
            legacy_rows,
            context='upgrade: promoted vs. legacy',
        )
        h5.h5file.remove_node(CITATIONS_BACKUP_PATH)

    # * method: _row_ids (static)
    @staticmethod
    def _row_ids(rows: List[Dict[str, Any]]) -> set:
        '''
        Extract the set of citation ids from a list of raw row dicts.

        :param rows: Row dicts as returned by ``H5Client.read_rows``.
        :type rows: List[Dict[str, Any]]
        :return: The set of ``id`` values across the given rows.
        :rtype: set
        '''

        # Collect the id column from each row.
        return {row.get('id') for row in rows}

    # * method: _assert_row_parity
    def _assert_row_parity(self,
            actual_rows: List[Dict[str, Any]],
            expected_rows: List[Dict[str, Any]],
            *,
            context: str,
        ) -> None:
        '''
        Verify two row sets carry the same citations, by id and count.

        :param actual_rows: The rows read back after a copy or promotion.
        :type actual_rows: List[Dict[str, Any]]
        :param expected_rows: The rows expected to be present.
        :type expected_rows: List[Dict[str, Any]]
        :param context: A short label identifying the check, for the error message.
        :type context: str
        :raises RuntimeError: If the row count or id set does not match.
        '''

        # A mismatched count or id set means a row was dropped or duplicated.
        if len(actual_rows) != len(expected_rows) or \
                self._row_ids(actual_rows) != self._row_ids(expected_rows):
            raise RuntimeError(
                f'Citation table schema upgrade failed parity check ({context}): '
                f'expected {len(expected_rows)} row(s), found {len(actual_rows)}.'
            )

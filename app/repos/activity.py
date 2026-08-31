"""Lit Review Activity H5 Repository"""

# *** imports

# ** core
from typing import List, Optional

# ** infra
from tiferet_h5 import H5Repository

# ** app
from ..interfaces.activity import ActivityService
from ..mappers.activity import ActivityAggregate, ActivityTableObject

# *** constants

# ** constant: activities_table_path
ACTIVITIES_TABLE_PATH = '/lit_review/activities'

# *** repos

# ** repo: activity_h5_repository
class ActivityH5Repository(ActivityService, H5Repository):
    '''
    HDF5 table-based repository for ActivityEntry aggregates. One PyTables
    row per entry, in a single table at ACTIVITIES_TABLE_PATH.

    Append-only: record() always appends a new row and never overwrites or
    removes one. The table is created lazily on the first record() call, so
    an existing store without this table rehydrates and reads normally
    before any activity is ever written.
    '''

    # * init
    def __init__(self, h5_file: str, mode: str = 'a') -> None:
        '''
        Initialize the activity H5 repository.

        :param h5_file: Path to the shared lit_review HDF5 file.
        :type h5_file: str
        :param mode: Default PyTables open mode.
        :type mode: str
        '''

        # Initialize the H5 repository base.
        H5Repository.__init__(self, h5_file=h5_file, mode=mode)

    # * method: record
    def record(self, entry: ActivityAggregate) -> None:
        '''
        Append a new activity entry as a new row. Never overwrites a row.

        :param entry: The activity entry to append.
        :type entry: ActivityAggregate
        '''

        # Serialize the entry, then get-or-create the table and append.
        table_object = ActivityTableObject.from_model(entry)
        with self.client() as h5:
            table = h5.get_or_create_table(
                ACTIVITIES_TABLE_PATH,
                ActivityTableObject.get_description(),
            )
            table_object.to_row(table)
            table.flush()

    # * method: list
    def list(self,
            action: Optional[str] = None,
            subject_type: Optional[str] = None,
            subject_id: Optional[str] = None,
            related_id: Optional[str] = None,
        ) -> List[ActivityAggregate]:
        '''
        List activity entries, newest first, with optional filters.

        :param action: Optional action token to match exactly.
        :type action: Optional[str]
        :param subject_type: Optional subject type to match exactly.
        :type subject_type: Optional[str]
        :param subject_id: Optional subject identifier to match exactly.
        :type subject_id: Optional[str]
        :param related_id: Optional related identifier to match exactly.
        :type related_id: Optional[str]
        :return: The matching activity entries, newest-insertion-first.
        :rtype: List[ActivityAggregate]
        '''

        # Read all rows, guarding against a store with no activity yet.
        with self.client() as h5:
            if not h5.node_exists(ACTIVITIES_TABLE_PATH):
                return []
            rows = h5.read_rows(ACTIVITIES_TABLE_PATH)

        # Apply the optional filters in-memory.
        if action is not None:
            rows = [row for row in rows if row.get('action') == action]
        if subject_type is not None:
            rows = [row for row in rows if row.get('subject_type') == subject_type]
        if subject_id is not None:
            rows = [row for row in rows if row.get('subject_id') == subject_id]
        if related_id is not None:
            rows = [row for row in rows if row.get('related_id') == related_id]

        # Map each row to an aggregate, newest-insertion-first.
        entries = [
            ActivityTableObject.from_row(row).map(ActivityAggregate)
            for row in rows
        ]
        return list(reversed(entries))

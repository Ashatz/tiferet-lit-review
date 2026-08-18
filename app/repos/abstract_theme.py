"""Lit Review AbstractTheme H5 Repository"""

# *** imports

# ** core
from typing import List, Optional

# ** infra
from tiferet_h5 import H5Repository

# ** app
from ..interfaces.abstract_theme import AbstractThemeService
from ..mappers.abstract_theme import AbstractThemeAggregate, AbstractThemeTableObject

# *** constants

# ** constant: abstract_themes_table_path
ABSTRACT_THEMES_TABLE_PATH = '/lit_review/abstract_themes'

# *** repos

# ** repo: abstract_theme_h5_repository
class AbstractThemeH5Repository(AbstractThemeService, H5Repository):
    '''
    HDF5 table-based repository for AbstractTheme domain objects. One
    PyTables row per join, in a single table at ABSTRACT_THEMES_TABLE_PATH.

    Filtering (by id, abstract_id, or theme_id) is done in-memory over
    read_rows results. Acceptable at v1 scale.

    ``save`` is an id-based upsert: an existing row with the same id is
    overwritten in place; otherwise a new row is appended.
    '''

    # * init
    def __init__(self, h5_file: str, mode: str = 'a') -> None:
        '''
        Initialize the abstract-theme H5 repository.

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
        Check whether a join with the given ID exists.

        :param id: The join identifier.
        :type id: str
        :return: True if the join exists, otherwise False.
        :rtype: bool
        '''

        # Delegate to get and check for None.
        return self.get(id) is not None

    # * method: get
    def get(self, id: str) -> Optional[AbstractThemeAggregate]:
        '''
        Retrieve an AbstractTheme by its ID.

        :param id: The join identifier.
        :type id: str
        :return: The join aggregate, or None if not found.
        :rtype: Optional[AbstractThemeAggregate]
        '''

        # Read all rows and find the matching one in-memory.
        with self.client() as h5:
            if not h5.node_exists(ABSTRACT_THEMES_TABLE_PATH):
                return None
            rows = h5.read_rows(ABSTRACT_THEMES_TABLE_PATH)

        # Find the matching row by id.
        match = next((row for row in rows if row.get('id') == id), None)
        if match is None:
            return None

        # Map the matching row to a join aggregate.
        return AbstractThemeTableObject.from_row(match).map(AbstractThemeAggregate)

    # * method: list
    def list(self,
            abstract_id: Optional[str] = None,
            theme_id: Optional[str] = None,
        ) -> List[AbstractThemeAggregate]:
        '''
        List joins, optionally filtered by abstract and/or theme.

        :param abstract_id: Optional abstract identifier to match.
        :type abstract_id: Optional[str]
        :param theme_id: Optional theme identifier to match.
        :type theme_id: Optional[str]
        :return: The matching join aggregates, in insertion order.
        :rtype: List[AbstractThemeAggregate]
        '''

        # Read all rows, guarding against a missing table.
        with self.client() as h5:
            if not h5.node_exists(ABSTRACT_THEMES_TABLE_PATH):
                return []
            rows = h5.read_rows(ABSTRACT_THEMES_TABLE_PATH)

        # Apply the optional abstract and theme filters in-memory.
        if abstract_id is not None:
            rows = [row for row in rows if row.get('abstract_id') == abstract_id]
        if theme_id is not None:
            rows = [row for row in rows if row.get('theme_id') == theme_id]

        # Map each row to a join aggregate, preserving insertion order.
        return [
            AbstractThemeTableObject.from_row(row).map(AbstractThemeAggregate)
            for row in rows
        ]

    # * method: save
    def save(self, abstract_theme: AbstractThemeAggregate) -> None:
        '''
        Persist an AbstractTheme aggregate as an id-based upsert.

        When a row with the same id already exists it is overwritten in place
        via indexed column assignment; otherwise a new row is appended.

        :param abstract_theme: The join aggregate to persist.
        :type abstract_theme: AbstractThemeAggregate
        '''

        # Serialize the join to a table object and a plain field dict.
        table_object = AbstractThemeTableObject.from_model(abstract_theme)
        data = table_object.model_dump(by_alias=True)

        # Get or create the table, then update-or-append by id.
        with self.client() as h5:
            table = h5.get_or_create_table(
                ABSTRACT_THEMES_TABLE_PATH,
                AbstractThemeTableObject.get_description(),
            )

            # Compare against the encoded id so StringCol bytes match.
            target_id = AbstractThemeTableObject.encode_value(
                abstract_theme.id,
                AbstractThemeTableObject._H5_TYPES['id'],
            )

            # Prefer indexed column writes; Row.update() during iterrows is
            # not reliably persisted by PyTables for this path.
            for index in range(table.nrows):
                if table.cols.id[index] != target_id:
                    continue
                for name, col in AbstractThemeTableObject._H5_TYPES.items():
                    getattr(table.cols, name)[index] = (
                        AbstractThemeTableObject.encode_value(data.get(name), col)
                    )
                table.flush()
                return

            # No existing row — append a new one.
            table_object.to_row(table)
            table.flush()

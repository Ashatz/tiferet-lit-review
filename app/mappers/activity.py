"""Lit Review Activity Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict

# ** infra
import tables
from pydantic import model_validator
from tiferet_h5 import TableObject

# ** app
from tiferet.mappers.core import Aggregate

from ..domain.activity import ActivityEntry

# *** constants

# ** constant: changed_fields_delimiter
CHANGED_FIELDS_DELIMITER = ','

# *** mappers

# ** mapper: activity_aggregate
class ActivityAggregate(ActivityEntry, Aggregate):
    '''
    Aggregate for the ActivityEntry domain object.

    Carries no mutation methods: an activity entry is immutable once
    recorded, so nothing about it is ever updated after creation.
    '''


# ** mapper: activity_table_object
class ActivityTableObject(ActivityEntry, TableObject):
    '''
    HDF5 table mapper for ActivityEntry: one append-only PyTables row per
    entry, stored in a single table at /lit_review/activities.

    changed_fields is a list of field names, but PyTables StringCol has no
    native list column. It is joined with CHANGED_FIELDS_DELIMITER for
    storage in to_row and split back into a list before construction so
    every in-memory ActivityTableObject still carries a real list.
    '''

    # * attribute: _H5_TYPES
    _H5_TYPES: ClassVar[Dict[str, Any]] = {
        'id': tables.StringCol(64),
        'occurred_at': tables.Int64Col(),
        'action': tables.StringCol(64),
        'subject_type': tables.StringCol(32),
        'subject_id': tables.StringCol(64),
        'related_type': tables.StringCol(32),
        'related_id': tables.StringCol(64),
        'changed_fields': tables.StringCol(2000),
    }

    # * method: to_row
    def to_row(self, table: tables.Table) -> None:
        '''
        Append this entry as a new row, joining changed_fields for storage.

        :param table: The open PyTables Table to append to.
        :type table: tables.Table
        '''

        # Serialize using aliases, then join the list field for column storage.
        row = table.row
        data = self.model_dump(by_alias=True)
        data['changed_fields'] = CHANGED_FIELDS_DELIMITER.join(self.changed_fields or [])

        # Write each declared H5 column to the row buffer.
        for col_name, col_def in type(self)._H5_TYPES.items():
            row[col_name] = self.encode_value(data.get(col_name), col_def)

        # Commit the row buffer to the table; every call is a pure append.
        row.append()

    # * method: _split_changed_fields (model validator)
    @model_validator(mode='before')
    @classmethod
    def _split_changed_fields(cls, data: Any) -> Any:
        '''
        Split a stored, delimited changed_fields string back into a list.

        Runs ahead of field validation so a row read back from storage (a
        joined string) and a value already built as a list (from_model)
        both construct correctly.

        :param data: The raw input to model_validate.
        :type data: Any
        :return: The updated input, with changed_fields normalized to a list.
        :rtype: Any
        '''

        # Only a plain dict with a string changed_fields needs splitting.
        if not isinstance(data, dict):
            return data
        value = data.get('changed_fields')
        if not isinstance(value, str):
            return data

        # Copy before mutating, then split on the storage delimiter.
        data = dict(data)
        data['changed_fields'] = [
            name for name in value.split(CHANGED_FIELDS_DELIMITER) if name
        ]
        return data

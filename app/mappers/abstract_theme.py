"""Lit Review AbstractTheme Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict

# ** infra
import tables
from tiferet_h5 import TableObject

# ** app
from tiferet.mappers.core import Aggregate

from ..domain.abstract_theme import AbstractTheme

# *** mappers

# ** mapper: abstract_theme_aggregate
class AbstractThemeAggregate(AbstractTheme, Aggregate):
    '''
    Mutable aggregate for the AbstractTheme domain object.

    Joins are add-only at v1; no field mutators are required beyond
    construction and save.
    '''


# ** mapper: abstract_theme_table_object
class AbstractThemeTableObject(AbstractTheme, TableObject):
    '''
    HDF5 table mapper for AbstractTheme: one PyTables row per join, stored
    in a single table at /lit_review/abstract_themes.
    '''

    # * attribute: _H5_TYPES
    _H5_TYPES: ClassVar[Dict[str, Any]] = {
        'id': tables.StringCol(64),
        'abstract_id': tables.StringCol(64),
        'theme_id': tables.StringCol(64),
        'created_at': tables.Int64Col(),
    }

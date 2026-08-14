"""Lit Review Linkage Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict

# ** infra
import tables
from tiferet_h5 import TableObject

# ** app
from tiferet.mappers.core import Aggregate

from ..domain.linkage import Linkage

# *** mappers

# ** mapper: linkage_aggregate
class LinkageAggregate(Linkage, Aggregate):
    '''
    Mutable aggregate for the Linkage domain object.

    Linkages are add-only at v1; no field mutators are required beyond
    construction and save.
    '''


# ** mapper: linkage_table_object
class LinkageTableObject(Linkage, TableObject):
    '''
    HDF5 table mapper for Linkage: one PyTables row per linkage, stored in
    a single table at /lit_review/linkages.
    '''

    # * attribute: _H5_TYPES
    _H5_TYPES: ClassVar[Dict[str, Any]] = {
        'id': tables.StringCol(64),
        'citation_id': tables.StringCol(64),
        'theme_id': tables.StringCol(64),
        'created_at': tables.Int64Col(),
    }

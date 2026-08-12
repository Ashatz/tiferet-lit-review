"""Lit Review Citation Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict

# ** infra
import tables
from tiferet_h5 import TableObject

# ** app
from tiferet.mappers.core import Aggregate

from ..domain.citation import Citation

# *** mappers

# ** mapper: citation_aggregate
class CitationAggregate(Citation, Aggregate):
    '''
    An aggregate representation of a Citation domain object.

    Citations are add-only at v1: no mutation methods are defined, per the
    domain docs (no update behavior specified for citations).
    '''


# ** mapper: citation_table_object
class CitationTableObject(Citation, TableObject):
    '''
    HDF5 table mapper for Citation: one PyTables row per citation, stored in
    a single table at /lit_review/citations.
    '''

    # * attribute: _H5_TYPES
    _H5_TYPES: ClassVar[Dict[str, Any]] = {
        'id': tables.StringCol(64),
        'source_id': tables.StringCol(64),
        'locator': tables.StringCol(64),
        'excerpt': tables.StringCol(4000),
        'context_note': tables.StringCol(4000),
        'created_at': tables.StringCol(40),
    }

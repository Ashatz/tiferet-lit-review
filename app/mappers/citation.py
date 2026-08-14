"""Lit Review Citation Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict, Optional

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
    Mutable aggregate for the Citation domain object.
    '''

    # * method: update_locator
    def update_locator(self, locator: str) -> None:
        '''
        Update the citation locator.

        :param locator: The new locator value.
        :type locator: str
        '''

        # Assign the new locator; validate_assignment re-validates.
        self.locator = locator

    # * method: update_excerpt
    def update_excerpt(self, excerpt: str) -> None:
        '''
        Update the citation excerpt.

        :param excerpt: The new excerpt text.
        :type excerpt: str
        '''

        # Assign the new excerpt; validate_assignment re-validates.
        self.excerpt = excerpt

    # * method: update_context_note
    def update_context_note(self,
            context_note: Optional[str] = None,
            *,
            clear: bool = False,
        ) -> None:
        '''
        Update or clear the citation context note.

        :param context_note: The new context note, if provided.
        :type context_note: Optional[str]
        :param clear: When True, set context_note to None.
        :type clear: bool
        '''

        # Apply an explicit clear or a provided note value.
        if clear:
            self.context_note = None
        elif context_note is not None:
            self.context_note = context_note


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
        'created_at': tables.Int64Col(),
    }

"""Lit Review Citation Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict, Optional

# ** infra
import tables
from pydantic import Field
from tiferet_h5 import TableObject

# ** app
from tiferet.mappers.core import Aggregate, TransferObject

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

    # * method: update_title
    def update_title(self,
            title: Optional[str] = None,
            *,
            clear: bool = False,
        ) -> None:
        '''
        Update or clear the citation title.

        A blank or whitespace-only title is treated as absent. Normalized
        here (rather than left to assignment-time validation) because a
        single-field assignment does not re-run the whole-model "before"
        validator's value substitution -- only its raise path.

        :param title: The new title, if provided.
        :type title: Optional[str]
        :param clear: When True, set title to None.
        :type clear: bool
        '''

        # Apply an explicit clear or a provided, normalized title value.
        if clear:
            self.title = None
        elif title is not None:
            self.title = title if title.strip() else None


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
        'title': tables.StringCol(256),
        'created_at': tables.Int64Col(),
    }


# ** mapper: citation_response
class CitationResponse(Citation, TransferObject):
    '''
    Transfer object for citation render responses.

    Extends Citation so the excerpt and locator serialize natively; adds the
    on-demand in-text and reference-list renderings.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_data': {
            'exclude': {'created_at'},
        },
    }

    # * attribute: formatted_reference
    formatted_reference: str = Field(
        default='',
        description='The reference-list rendering for the requested style.',
    )

    # * attribute: in_text_citation
    in_text_citation: str = Field(
        default='',
        description='The in-text rendering for the requested style.',
    )

    # * method: from_aggregate (static)
    @staticmethod
    def from_aggregate(
            citation: Citation,
            formatted_reference: str,
            in_text_citation: str,
        ) -> 'CitationResponse':
        '''
        Map a Citation into a CitationResponse.

        :param citation: The citation to map.
        :type citation: Citation
        :param formatted_reference: The reference-list rendering.
        :type formatted_reference: str
        :param in_text_citation: The in-text rendering.
        :type in_text_citation: str
        :return: The citation response transfer object.
        :rtype: CitationResponse
        '''

        # Delegate to TransferObject.from_model, attaching the renderings.
        return CitationResponse.from_model(
            citation,
            formatted_reference=formatted_reference,
            in_text_citation=in_text_citation,
        )

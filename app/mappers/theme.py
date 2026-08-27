"""Lit Review Theme Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict, List, Optional

# ** infra
from pydantic import Field
from tiferet_h5 import NodeObject

# ** app
from tiferet.mappers.core import Aggregate, TransferObject

from ..domain.citation import Citation
from ..domain.linkage import Linkage
from ..domain.theme import Theme

# *** mappers

# ** mapper: theme_aggregate
class ThemeAggregate(Theme, Aggregate):
    '''
    Mutable aggregate for the Theme domain object.
    '''

    # * method: update_synthesis
    def update_synthesis(self, synthesized_description: str, linkage_count: int) -> None:
        '''
        Update the theme's synthesized description and denormalized linkage count.

        :param synthesized_description: The new synthesis text.
        :type synthesized_description: str
        :param linkage_count: The updated number of linkages on this theme.
        :type linkage_count: int
        '''

        # Apply both synthesis fields through validated mutation.
        self.set_attribute('synthesized_description', synthesized_description)
        self.set_attribute('linkage_count', linkage_count)


# ** mapper: theme_node_object
class ThemeNodeObject(Theme, NodeObject):
    '''
    HDF5 node mapper for Theme: one HDF5 group per theme, with theme fields
    stored as node attributes.
    '''


# ** mapper: retired_citation_view
class RetiredCitationView(Citation, TransferObject):
    '''
    Presentation view of a retired linkage: the resolved citation plus its
    retirement timestamp and reason. Shown only via
    ``theme show --include-retired``; a retired linkage still resolves to a
    real citation, so provenance is never lost.
    '''

    # * attribute: retired_at
    retired_at: int = Field(
        ...,
        description='The unix timestamp when this linkage was retired.',
    )

    # * attribute: retirement_reason
    retirement_reason: Optional[str] = Field(
        default=None,
        description='The optional reason recorded when this linkage was retired.',
    )

    # * method: from_citation_and_linkage (static)
    @staticmethod
    def from_citation_and_linkage(citation: Citation, linkage: Linkage) -> 'RetiredCitationView':
        '''
        Build a RetiredCitationView from a resolved citation and its linkage.

        :param citation: The citation the retired linkage points to.
        :type citation: Citation
        :param linkage: The retired linkage carrying the retirement provenance.
        :type linkage: Linkage
        :return: The constructed retired-citation view.
        :rtype: RetiredCitationView
        '''

        # Delegate to TransferObject.from_model, attaching retirement fields.
        return RetiredCitationView.from_model(
            citation,
            retired_at=linkage.retired_at,
            retirement_reason=linkage.retirement_reason,
        )


# ** mapper: theme_response
class ThemeResponse(Theme, TransferObject):
    '''
    Transfer object for theme CLI/API responses.

    Extends Theme so the synthesis fields serialize natively; adds the linked
    citations when a show/display needs more than the theme itself.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_data': {
            'exclude': {'created_at'},
        },
    }

    # * attribute: citations
    citations: List[Citation] = Field(
        default_factory=list,
        description='Active linked citations included on show/display responses.',
    )

    # * attribute: retired_citations
    retired_citations: Optional[List[RetiredCitationView]] = Field(
        default=None,
        description='Retired linked citations; populated only with --include-retired.',
    )

    # * method: from_aggregate (static)
    @staticmethod
    def from_aggregate(
            theme: ThemeAggregate,
            citations: Optional[List[Citation]] = None,
            retired_citations: Optional[List[RetiredCitationView]] = None,
        ) -> 'ThemeResponse':
        '''
        Map a ThemeAggregate into a ThemeResponse.

        :param theme: The theme aggregate to map.
        :type theme: ThemeAggregate
        :param citations: Optional active linked citations to include.
        :type citations: Optional[List[Citation]]
        :param retired_citations: Optional retired citation views to include;
            left unset unless --include-retired was requested.
        :type retired_citations: Optional[List[RetiredCitationView]]
        :return: The theme response transfer object.
        :rtype: ThemeResponse
        '''

        # Delegate to TransferObject.from_model, attaching citations when given.
        return ThemeResponse.from_model(
            theme,
            citations=citations or [],
            retired_citations=retired_citations,
        )

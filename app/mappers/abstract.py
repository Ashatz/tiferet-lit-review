"""Lit Review Abstract Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict, List, Optional

# ** infra
from pydantic import Field
from tiferet_h5 import NodeObject

# ** app
from tiferet.mappers.core import Aggregate, TransferObject

from ..domain.abstract import Abstract
from ..domain.theme import Theme

# *** mappers

# ** mapper: abstract_aggregate
class AbstractAggregate(Abstract, Aggregate):
    '''
    Mutable aggregate for the Abstract domain object.
    '''


# ** mapper: abstract_node_object
class AbstractNodeObject(Abstract, NodeObject):
    '''
    HDF5 node mapper for Abstract: one HDF5 group per abstract, with abstract
    fields stored as node attributes.
    '''


# ** mapper: abstract_response
class AbstractResponse(Abstract, TransferObject):
    '''
    Transfer object for abstract CLI/API responses.

    Extends Abstract so the brief fields serialize natively; adds the joined
    themes when a show/display needs more than the abstract itself.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_data': {
            'exclude': {'created_at'},
        },
    }

    # * attribute: themes
    themes: List[Theme] = Field(
        default_factory=list,
        description='Joined themes included on show/display responses.',
    )

    # * method: from_aggregate (static)
    @staticmethod
    def from_aggregate(
            abstract: AbstractAggregate,
            themes: Optional[List[Theme]] = None,
        ) -> 'AbstractResponse':
        '''
        Map an AbstractAggregate into an AbstractResponse.

        :param abstract: The abstract aggregate to map.
        :type abstract: AbstractAggregate
        :param themes: Optional joined themes to include on the response.
        :type themes: Optional[List[Theme]]
        :return: The abstract response transfer object.
        :rtype: AbstractResponse
        '''

        # Delegate to TransferObject.from_model, attaching themes when given.
        return AbstractResponse.from_model(
            abstract,
            themes=themes or [],
        )

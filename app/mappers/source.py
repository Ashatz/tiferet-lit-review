"""Lit Review Source Mappers"""

# *** imports

# ** infra
from tiferet_h5 import NodeObject

# ** app
from tiferet.mappers.core import Aggregate

from ..domain.source import Source

# *** mappers

# ** mapper: source_aggregate
class SourceAggregate(Source, Aggregate):
    '''
    An aggregate representation of a Source domain object.

    Sources are add-only at v1: no mutation methods are defined, per the
    domain docs (no update behavior specified for sources).
    '''


# ** mapper: source_node_object
class SourceNodeObject(Source, NodeObject):
    '''
    HDF5 node mapper for Source: one HDF5 group per source, with the
    bibliographic fields stored as node attributes.
    '''

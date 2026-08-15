"""Lit Review Source Mappers"""

# *** imports

# ** core
from typing import Any, Dict, List, Optional

# ** infra
from tiferet_h5 import NodeObject

# ** app
from tiferet.mappers.core import Aggregate

from ..domain.source import Source, SourceAuthor

# *** mappers

# ** mapper: source_aggregate
class SourceAggregate(Source, Aggregate):
    '''
    Mutable aggregate for the Source domain object.
    '''

    # * method: update_record
    def update_record(self,
            authors: Optional[List[str]] = None,
            year: Optional[int] = None,
            title: Optional[str] = None,
            container_title: Optional[str] = None,
            publisher: Optional[str] = None,
            *,
            clear_container_title: bool = False,
            clear_publisher: bool = False,
        ) -> None:
        '''
        Update mutable bibliographic fields on the source.

        Identity fields (id, medium, locator_convention, created_at) are not
        mutable through this method. Optional clears for nullable fields are
        explicit so ``None`` defaults never wipe existing values accidentally.

        :param authors: The updated author list, if provided.
        :type authors: Optional[List]
        :param year: The updated publication year, if provided.
        :type year: Optional[int]
        :param title: The updated title, if provided.
        :type title: Optional[str]
        :param container_title: The updated container title, if provided.
        :type container_title: Optional[str]
        :param publisher: The updated publisher, if provided.
        :type publisher: Optional[str]
        :param clear_container_title: When True, set container_title to None.
        :type clear_container_title: bool
        :param clear_publisher: When True, set publisher to None.
        :type clear_publisher: bool
        '''

        # Apply each provided required bibliographic field.
        if authors is not None:
            self.authors = [SourceAuthor.from_value(author) for author in authors]
        if year is not None:
            self.year = year
        if title is not None:
            self.title = title

        # Apply optional field updates or explicit clears.
        if clear_container_title:
            self.container_title = None
        elif container_title is not None:
            self.container_title = container_title
        if clear_publisher:
            self.publisher = None
        elif publisher is not None:
            self.publisher = publisher


# ** mapper: source_node_object
class SourceNodeObject(Source, NodeObject):
    '''
    HDF5 node mapper for Source: one HDF5 group per source, with the
    bibliographic fields stored as node attributes.
    '''

    # * method: to_attrs
    def to_attrs(self, role: str = 'to_h5.attrs', **overrides) -> Dict[str, Any]:
        '''
        Serialize source attributes, storing authors as display-name strings.

        :param role: Serialization role forwarded to ``to_primitive``.
        :type role: str
        :param overrides: Additional key-value pairs merged into the result.
        :type overrides: dict
        :return: A flat dict of attribute name to value pairs.
        :rtype: Dict[str, Any]
        '''

        # Serialize through the node-object base, then flatten authors.
        attrs = super().to_attrs(role=role, **overrides)
        attrs['authors'] = [author.display_name for author in self.authors]
        return attrs

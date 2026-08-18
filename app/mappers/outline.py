"""Lit Review Outline Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict, List, Optional

# ** infra
from pydantic import Field
from tiferet_h5 import NodeObject

# ** app
from tiferet.mappers.core import Aggregate, TransferObject

from ..domain.citation import Citation
from ..domain.outline import Outline, OutlineSlot
from ..domain.theme import Theme

# *** mappers

# ** mapper: outline_aggregate
class OutlineAggregate(Outline, Aggregate):
    '''
    Mutable aggregate for the Outline domain object.
    '''

    # * method: add_slot
    def add_slot(self, theme_id: str) -> bool:
        '''
        Place a theme into the next outline slot.

        Unique on theme_id: an already-slotted theme is left unchanged.

        :param theme_id: The theme identifier to arrange.
        :type theme_id: str
        :return: True when a new slot was added, otherwise False.
        :rtype: bool
        '''

        # Leave an existing slot unchanged.
        if any(slot.theme_id == theme_id for slot in self.slots):
            return False

        # Create the value object as part of this outline's lifecycle.
        slot = OutlineSlot(
            theme_id=theme_id,
            position=self.slot_count,
        )

        # Append through validated mutation so the parent owns the collection.
        self.set_attribute('slots', [*self.slots, slot])
        self.set_attribute('slot_count', self.slot_count + 1)

        # Report that a new slot was formed.
        return True


# ** mapper: outline_node_object
class OutlineNodeObject(Outline, NodeObject):
    '''
    HDF5 node mapper for Outline: one HDF5 group per outline, with outline
    fields stored as node attributes. Owned slots are stored as theme
    identifier strings in assembly order.
    '''

    # * method: to_attrs
    def to_attrs(self, role: str = 'to_h5.attrs', **overrides) -> Dict[str, Any]:
        '''
        Serialize outline attributes, storing slots as theme-id strings.

        :param role: Serialization role forwarded to ``to_primitive``.
        :type role: str
        :param overrides: Additional key-value pairs merged into the result.
        :type overrides: dict
        :return: A flat dict of attribute name to value pairs.
        :rtype: Dict[str, Any]
        '''

        # Serialize through the node-object base, then flatten owned slots.
        attrs = super().to_attrs(role=role, **overrides)
        attrs['slots'] = [slot.theme_id for slot in self.slots]
        return attrs

    # * method: from_attrs (static)
    @classmethod
    def from_attrs(cls, attrs: Dict[str, Any], **overrides) -> 'OutlineNodeObject':
        '''
        Reconstruct an outline node object, mapping stored ids to OutlineSlot.

        :param attrs: HDF5 node attribute name-value pairs.
        :type attrs: Dict[str, Any]
        :param overrides: Additional key-value pairs that take priority.
        :type overrides: dict
        :return: The outline node object.
        :rtype: OutlineNodeObject
        '''

        # Map stored theme-id strings onto the value-object field shape.
        data = dict(attrs)
        slots = data.get('slots', [])
        if hasattr(slots, 'tolist'):
            slots = slots.tolist()
        mapped: List[Any] = []
        for position, theme in enumerate(slots or []):
            if isinstance(theme, bytes):
                theme = theme.decode('utf-8')
            elif hasattr(theme, 'item'):
                theme = theme.item()
                if isinstance(theme, bytes):
                    theme = theme.decode('utf-8')
            mapped.append({
                'theme_id': str(theme),
                'position': position,
            })
        data['slots'] = mapped

        # Delegate bytes and numpy-scalar normalization to the node-object base.
        return super().from_attrs(data, **overrides)

    # * method: map
    def map(self, target: type, **overrides) -> OutlineAggregate:
        '''
        Map this node object onto an outline aggregate via add_slot.

        :param target: The aggregate class to construct.
        :type target: type
        :param overrides: Additional keyword arguments merged into the data.
        :type overrides: dict
        :return: The rehydrated outline aggregate.
        :rtype: OutlineAggregate
        '''

        # Build the aggregate without slots, then restore each owned theme.
        slots = list(self.slots)
        outline = super().map(target, slots=[], slot_count=0, **overrides)
        for slot in slots:
            outline.add_slot(slot.theme_id)

        # Return the rehydrated aggregate.
        return outline


# ** mapper: outline_response
class OutlineResponse(Outline, TransferObject):
    '''
    Transfer object for outline CLI/API responses.

    Extends Outline so the title and owned slots serialize natively; adds
    the resolved Theme objects when a show/display needs more than the
    slot identifiers, and optional live citation previews.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_data': {
            'exclude': {'created_at'},
        },
    }

    # * attribute: linked_themes
    linked_themes: List[Theme] = Field(
        default_factory=list,
        description='Resolved Theme objects in slot order on show/display.',
    )

    # * attribute: citation_previews
    citation_previews: List[Citation] = Field(
        default_factory=list,
        description='Optional live citation renderings when a style is supplied.',
    )

    # * method: from_aggregate (static)
    @staticmethod
    def from_aggregate(
            outline: OutlineAggregate,
            themes: Optional[List[Theme]] = None,
            citation_previews: Optional[List[Citation]] = None,
        ) -> 'OutlineResponse':
        '''
        Map an OutlineAggregate into an OutlineResponse.

        :param outline: The outline aggregate to map.
        :type outline: OutlineAggregate
        :param themes: Optional resolved themes to include on the response.
        :type themes: Optional[List[Theme]]
        :param citation_previews: Optional rendered citations for preview.
        :type citation_previews: Optional[List[Citation]]
        :return: The outline response transfer object.
        :rtype: OutlineResponse
        '''

        # Delegate to TransferObject.from_model, attaching show payload when given.
        return OutlineResponse.from_model(
            outline,
            linked_themes=themes or [],
            citation_previews=citation_previews or [],
        )

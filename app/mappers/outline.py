"""Lit Review Outline Mappers"""

# *** imports

# ** core
import json
from typing import Any, ClassVar, Dict, List, Optional

# ** infra
from pydantic import Field
from tiferet_h5 import NodeObject

# ** app
from tiferet.mappers.core import Aggregate, TransferObject

from ..domain.citation import Citation
from ..domain.outline import Outline, OutlineSlot, OutlineSlotTheme
from ..domain.theme import Theme

# *** mappers

# ** mapper: outline_aggregate
class OutlineAggregate(Outline, Aggregate):
    '''
    Mutable aggregate for the Outline domain object.
    '''

    # * method: add_slot
    def add_slot(
            self,
            title: str,
            theme_ids: Optional[List[str]] = None,
            id: Optional[str] = None,
        ) -> OutlineSlot:
        '''
        Append a named slot to this outline.

        Themes are optional at create and may be added later. An explicit
        id is accepted so persistence can restore the same slot identity.

        :param title: The human heading for this grouping.
        :type title: str
        :param theme_ids: Optional theme identifiers to include at create.
        :type theme_ids: Optional[List[str]]
        :param id: Optional slot identifier to restore.
        :type id: Optional[str]
        :return: The newly owned slot.
        :rtype: OutlineSlot
        '''

        # Create the named slot as part of this outline's lifecycle.
        kwargs: Dict[str, Any] = {
            'title': title,
            'position': self.slot_count,
        }
        if id is not None:
            kwargs['id'] = id
        slot = OutlineSlot(**kwargs)

        # Append through validated mutation so the parent owns the collection.
        self.set_attribute('slots', [*self.slots, slot])
        self.set_attribute('slot_count', self.slot_count + 1)

        # Include any initial themes through the same join lifecycle.
        for theme_id in theme_ids or []:
            self.add_theme(slot.id, theme_id)

        # Return the owned slot, including any themes just joined.
        return self.get_slot(slot.id)

    # * method: add_theme
    def add_theme(self, slot_id: str, theme_id: str) -> bool:
        '''
        Include a theme in an owned slot.

        Idempotent per slot: an already-joined theme_id is left unchanged.
        A missing slot is left unchanged and reported as False.

        :param slot_id: The slot identifier to join the theme to.
        :type slot_id: str
        :param theme_id: The theme identifier to include.
        :type theme_id: str
        :return: True when a new join was added, otherwise False.
        :rtype: bool
        '''

        # Leave a missing slot unchanged.
        slot = self.get_slot(slot_id)
        if slot is None:
            return False

        # Leave an existing join unchanged.
        if slot.has_theme(theme_id):
            return False

        # Replace the owned slot with one that includes the new join.
        join = OutlineSlotTheme(theme_id=theme_id)
        updated = OutlineSlot(
            id=slot.id,
            title=slot.title,
            themes=[*slot.themes, join],
            theme_count=slot.theme_count + 1,
            position=slot.position,
            created_at=slot.created_at,
        )
        self.set_attribute('slots', [
            updated if item.id == slot_id else item for item in self.slots
        ])

        # Report that a new join was formed.
        return True

    # * method: remove_theme
    def remove_theme(self, slot_id: str, theme_id: str) -> bool:
        '''
        Remove a theme from an owned slot.

        Idempotent per slot: a theme that is not joined is left unchanged.
        A missing slot is left unchanged and reported as False.

        :param slot_id: The slot identifier to remove the theme from.
        :type slot_id: str
        :param theme_id: The theme identifier to remove.
        :type theme_id: str
        :return: True when a join was removed, otherwise False.
        :rtype: bool
        '''

        # Leave a missing slot unchanged.
        slot = self.get_slot(slot_id)
        if slot is None:
            return False

        # Leave a missing join unchanged.
        if not slot.has_theme(theme_id):
            return False

        # Replace the owned slot with one that drops the join.
        remaining = [
            theme for theme in slot.themes if theme.theme_id != theme_id
        ]
        updated = OutlineSlot(
            id=slot.id,
            title=slot.title,
            themes=remaining,
            theme_count=len(remaining),
            position=slot.position,
            created_at=slot.created_at,
        )
        self.set_attribute('slots', [
            updated if item.id == slot_id else item for item in self.slots
        ])

        # Report that a join was removed.
        return True


# ** mapper: outline_node_object
class OutlineNodeObject(Outline, NodeObject):
    '''
    HDF5 node mapper for Outline: one HDF5 group per outline, with outline
    fields stored as node attributes. Owned slots are stored as JSON
    records so each slot keeps its id, title, and theme joins.
    '''

    # * method: to_attrs
    def to_attrs(self, role: str = 'to_h5.attrs', **overrides) -> Dict[str, Any]:
        '''
        Serialize outline attributes, storing slots as JSON records.

        :param role: Serialization role forwarded to ``to_primitive``.
        :type role: str
        :param overrides: Additional key-value pairs merged into the result.
        :type overrides: dict
        :return: A flat dict of attribute name to value pairs.
        :rtype: Dict[str, Any]
        '''

        # Serialize through the node-object base, then flatten owned slots.
        attrs = super().to_attrs(role=role, **overrides)
        attrs['slots'] = [
            json.dumps({
                'id': slot.id,
                'title': slot.title,
                'theme_ids': [theme.theme_id for theme in slot.themes],
            })
            for slot in self.slots
        ]
        return attrs

    # * method: from_attrs (static)
    @classmethod
    def from_attrs(cls, attrs: Dict[str, Any], **overrides) -> 'OutlineNodeObject':
        '''
        Reconstruct an outline node object, mapping stored records to slots.

        :param attrs: HDF5 node attribute name-value pairs.
        :type attrs: Dict[str, Any]
        :param overrides: Additional key-value pairs that take priority.
        :type overrides: dict
        :return: The outline node object.
        :rtype: OutlineNodeObject
        '''

        # Map stored JSON slot records onto the value-object field shape.
        data = dict(attrs)
        slots = data.get('slots', [])
        if hasattr(slots, 'tolist'):
            slots = slots.tolist()
        mapped: List[Any] = []
        for position, record in enumerate(slots or []):
            if isinstance(record, bytes):
                record = record.decode('utf-8')
            elif hasattr(record, 'item'):
                record = record.item()
                if isinstance(record, bytes):
                    record = record.decode('utf-8')
            payload = json.loads(str(record))
            theme_ids = payload.get('theme_ids', [])
            mapped.append({
                'id': payload['id'],
                'title': payload['title'],
                'themes': [{'theme_id': theme_id} for theme_id in theme_ids],
                'theme_count': len(theme_ids),
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

        # Build the aggregate without slots, then restore each owned grouping.
        slots = list(self.slots)
        outline = super().map(target, slots=[], slot_count=0, **overrides)
        for slot in slots:
            outline.add_slot(
                slot.title,
                theme_ids=[theme.theme_id for theme in slot.themes],
                id=slot.id,
            )

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

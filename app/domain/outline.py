"""Lit Review Outline Domain Model"""

# *** imports

# ** core
from time import time
from typing import List, Optional
from uuid import uuid4

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: outline_slot_theme
class OutlineSlotTheme(DomainObject):
    '''
    A theme included in an OutlineSlot. This is not a Theme entity: it
    carries no lifecycle of its own and exists only as a join owned by
    the slot.
    '''

    # * attribute: theme_id
    theme_id: str = Field(
        ...,
        description='The identifier of the included theme.',
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )


# ** model: outline_slot
class OutlineSlot(DomainObject):
    '''
    A named grouping of optional themes on an Outline. This is the
    outline form of a section: a heading plus the themes that will
    justify the later Paper Section. It has no drafted prose and no
    lifecycle off the outline that owns it.
    '''

    # * attribute: id
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='The unique slot identifier, generated if absent.',
    )

    # * attribute: title
    title: str = Field(
        ...,
        description='The human heading for this grouping.',
    )

    # * attribute: themes
    themes: List[OutlineSlotTheme] = Field(
        default_factory=list,
        description='Owned theme joins, in insertion order.',
    )

    # * attribute: theme_count
    theme_count: int = Field(
        default=0,
        description='Denormalized count of themes joined to this slot.',
    )

    # * attribute: position
    position: int = Field(
        ...,
        description='The zero-based order of this slot in the outline.',
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )

    # * method: has_theme
    def has_theme(self, theme_id: str) -> bool:
        '''
        Report whether this slot already includes the given theme.

        :param theme_id: The theme identifier to look up.
        :type theme_id: str
        :return: True when the theme is joined to this slot.
        :rtype: bool
        '''

        # Match against the owned join identifiers.
        return any(theme.theme_id == theme_id for theme in self.themes)


# ** model: outline
class Outline(DomainObject):
    '''
    An ordered set of named slots. It is the arrangement of an argument,
    not the manuscript.
    '''

    # * attribute: id
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='The unique outline identifier, generated if absent.',
    )

    # * attribute: title
    title: str = Field(
        ...,
        description='The short label for this arrangement.',
    )

    # * attribute: slots
    slots: List[OutlineSlot] = Field(
        default_factory=list,
        description='Owned named slots, in assembly order.',
    )

    # * attribute: slot_count
    slot_count: int = Field(
        default=0,
        description='Denormalized count of slots on this outline.',
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )

    # * method: get_slot
    def get_slot(self, slot_id: str) -> Optional[OutlineSlot]:
        '''
        Retrieve an owned slot by its identifier.

        :param slot_id: The slot identifier to look up.
        :type slot_id: str
        :return: The matching slot, or None if this outline does not own it.
        :rtype: Optional[OutlineSlot]
        '''

        # Return the first owned slot with this id.
        return next((slot for slot in self.slots if slot.id == slot_id), None)

    # * method: has_slot
    def has_slot(self, slot_id: str) -> bool:
        '''
        Report whether this outline owns the given slot.

        :param slot_id: The slot identifier to look up.
        :type slot_id: str
        :return: True when the slot belongs to this outline.
        :rtype: bool
        '''

        # Delegate to the owned-slot lookup.
        return self.get_slot(slot_id) is not None

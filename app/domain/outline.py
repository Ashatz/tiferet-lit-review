"""Lit Review Outline Domain Model"""

# *** imports

# ** core
from time import time
from typing import List
from uuid import uuid4

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: outline_slot
class OutlineSlot(DomainObject):
    '''
    A theme placed in an Outline. This is not a Theme entity: it carries
    no lifecycle of its own and exists only as an ordered join owned by
    the outline.
    '''

    # * attribute: theme_id
    theme_id: str = Field(
        ...,
        description='The identifier of the arranged theme.',
    )

    # * attribute: position
    position: int = Field(
        ...,
        description='The zero-based slot order of this theme in the outline.',
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )


# ** model: outline
class Outline(DomainObject):
    '''
    An ordered set of theme slots. It is the arrangement of an argument,
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
        description='Owned theme slots, in assembly order.',
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

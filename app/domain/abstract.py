"""Lit Review Abstract Domain Model"""

# *** imports

# ** core
from time import time
from uuid import uuid4

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: abstract
class Abstract(DomainObject):
    '''
    A standing brief of one argument, composed from a chosen set of themes.
    '''

    # * attribute: id
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='The unique abstract identifier, generated if absent.',
    )

    # * attribute: name
    name: str = Field(
        ...,
        description='The short label for this argument brief.',
    )

    # * attribute: body
    body: str = Field(
        default='',
        description='The current brief text; empty until an editorial write or synthesis.',
    )

    # * attribute: theme_count
    theme_count: int = Field(
        default=0,
        description='Denormalized count of themes joined to this abstract.',
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )

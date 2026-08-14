"""Lit Review Linkage Domain Model"""

# *** imports

# ** core
from time import time
from uuid import uuid4

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: linkage
class Linkage(DomainObject):
    '''
    The relationship connecting a citation to a theme. Forming a linkage is
    the event that causes the theme's synthesized description to be
    reconsidered against its full linkage set.
    '''

    # * attribute: id
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='The unique linkage identifier, generated if absent.',
    )

    # * attribute: citation_id
    citation_id: str = Field(
        ...,
        description='The identifier of the linked citation.',
    )

    # * attribute: theme_id
    theme_id: str = Field(
        ...,
        description='The identifier of the linked theme.',
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )

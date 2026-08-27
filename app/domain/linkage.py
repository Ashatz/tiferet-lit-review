"""Lit Review Linkage Domain Model"""

# *** imports

# ** core
from time import time
from typing import Optional
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
    a structural fact; synthesis is an explicit later act against the full
    linkage set. A linkage may later be retired -- excluded from synthesis
    and the default evidence view without being deleted -- and reinstated,
    per RFP-7.
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

    # * attribute: retired_at
    retired_at: Optional[int] = Field(
        default=None,
        description='The unix retirement timestamp; None means the linkage is active.',
    )

    # * attribute: retirement_reason
    retirement_reason: Optional[str] = Field(
        default=None,
        description='An optional free-text reason recorded when the linkage was retired.',
    )

    # * method: is_active
    def is_active(self) -> bool:
        '''
        Whether this linkage is currently active (not retired).

        :return: True when retired_at is None, otherwise False.
        :rtype: bool
        '''

        # A linkage is active exactly when it has never been retired.
        return self.retired_at is None

"""Lit Review AbstractTheme Domain Model"""

# *** imports

# ** core
from time import time
from uuid import uuid4

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: abstract_theme
class AbstractTheme(DomainObject):
    '''
    The unidirectional join from an abstract to a theme. Forming it includes
    a theme in that argument and does not rewrite the abstract's body.
    '''

    # * attribute: id
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='The unique join identifier, generated if absent.',
    )

    # * attribute: abstract_id
    abstract_id: str = Field(
        ...,
        description='The identifier of the abstract that includes the theme.',
    )

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

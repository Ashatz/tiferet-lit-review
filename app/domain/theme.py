"""Lit Review Theme Domain Model"""

# *** imports

# ** core
from time import time
from uuid import uuid4
import re

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** functions

# ** function: slugify_theme_name
def slugify_theme_name(name: str) -> str:
    '''
    Derive a URL-safe slug from a theme name.

    Non-alphanumeric runs become a single hyphen; leading/trailing hyphens are
    stripped. An empty result falls back to a UUID so id generation never
    yields an empty string.

    :param name: The theme name to slugify.
    :type name: str
    :return: A lowercase hyphenated slug, or a UUID if nothing remains.
    :rtype: str
    '''

    # Normalize separators and strip non-alphanumeric characters.
    slug = re.sub(r'[^a-z0-9]+', '-', name.strip().lower()).strip('-')

    # Fall back to a UUID when the name yields no usable characters.
    return slug or str(uuid4())

# *** models

# ** model: theme
class Theme(DomainObject):
    '''
    A strand of meaning that gathers citations from any source and holds a
    synthesized description of what those citations currently say together.
    '''

    # * attribute: id
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='The unique theme identifier (name slug, or UUID on collision).',
    )

    # * attribute: name
    name: str = Field(
        ...,
        description='The short label for this theme.',
    )

    # * attribute: synthesized_description
    synthesized_description: str = Field(
        default='',
        description='The current synthesis of all linked citations; empty until the first linkage.',
    )

    # * attribute: linkage_count
    linkage_count: int = Field(
        default=0,
        description='Denormalized count of linkages attached to this theme.',
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )

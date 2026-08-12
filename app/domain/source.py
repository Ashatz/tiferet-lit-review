"""Lit Review Source Domain Model"""

# *** imports

# ** core
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4
import re

# ** infra
from pydantic import Field, model_validator

# ** app
from tiferet.domain.core import DomainObject

# *** constants

# ** constant: page_range_locator_convention
PAGE_RANGE_LOCATOR_CONVENTION = 'page_range'

# ** constant: source_medium_locator_conventions
SOURCE_MEDIUM_LOCATOR_CONVENTIONS: Dict[str, str] = {
    'pdf': PAGE_RANGE_LOCATOR_CONVENTION,
    'book': PAGE_RANGE_LOCATOR_CONVENTION,
}

# ** constant: locator_convention_patterns
LOCATOR_CONVENTION_PATTERNS: Dict[str, str] = {
    PAGE_RANGE_LOCATOR_CONVENTION: r'^\d+-\d+$',
}

# *** functions

# ** function: is_valid_locator
def is_valid_locator(locator_convention: str, locator: str) -> bool:
    '''
    Check whether a locator's shape matches a given locator convention.

    Adding a new medium only requires a new entry in
    SOURCE_MEDIUM_LOCATOR_CONVENTIONS and, if its locator shape is new, a new
    entry in LOCATOR_CONVENTION_PATTERNS -- never a branch here.

    :param locator_convention: The locator convention name (e.g. "page_range").
    :type locator_convention: str
    :param locator: The locator value to validate.
    :type locator: str
    :return: True if the locator matches the convention's expected shape.
    :rtype: bool
    '''

    # Look up the pattern for the given convention; unknown conventions never validate.
    pattern = LOCATOR_CONVENTION_PATTERNS.get(locator_convention)
    if pattern is None:
        return False

    # Match the locator against the convention's pattern.
    return bool(re.match(pattern, locator))

# *** models

# ** model: source
class Source(DomainObject):
    '''
    A work being read: a PDF, a book, or another medium added later, together
    with the bibliographic record needed to cite it correctly.
    '''

    # * attribute: id
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='The unique source identifier, generated if absent.',
    )

    # * attribute: medium
    medium: str = Field(
        ...,
        description='The source medium (e.g. "pdf", "book"), validated against a declared, extensible set.',
    )

    # * attribute: authors
    authors: List[str] = Field(
        ...,
        min_length=1,
        description='The source authors; at least one is required.',
    )

    # * attribute: year
    year: int = Field(
        ...,
        description='The source publication year.',
    )

    # * attribute: title
    title: str = Field(
        ...,
        description='The source title.',
    )

    # * attribute: container_title
    container_title: Optional[str] = Field(
        default=None,
        description='The journal or collection title, where applicable.',
    )

    # * attribute: publisher
    publisher: Optional[str] = Field(
        default=None,
        description='The source publisher, where applicable.',
    )

    # * attribute: locator_convention
    locator_convention: str = Field(
        default='',
        description='The locator shape convention, derived from medium at creation time.',
    )

    # * attribute: created_at
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description='The ISO 8601 creation timestamp.',
    )

    # * method: _derive_locator_convention (validator)
    @model_validator(mode='before')
    @classmethod
    def _derive_locator_convention(cls, values: dict) -> dict:
        '''
        Validate the medium and derive locator_convention from it when absent.

        :param values: The raw field values before construction.
        :type values: dict
        :return: The updated field values dict.
        :rtype: dict
        '''

        # Verify the medium is one of the declared, supported mediums.
        medium = values.get('medium')
        if medium not in SOURCE_MEDIUM_LOCATOR_CONVENTIONS:
            raise ValueError(
                f'Unsupported source medium {medium!r}; must be one of '
                f'{sorted(SOURCE_MEDIUM_LOCATOR_CONVENTIONS)}.'
            )

        # Derive the locator convention from the medium when not explicitly provided.
        if not values.get('locator_convention'):
            values['locator_convention'] = SOURCE_MEDIUM_LOCATOR_CONVENTIONS[medium]

        # Return the updated values.
        return values

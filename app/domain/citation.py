"""Lit Review Citation Domain Model"""

# *** imports

# ** core
from time import time
from typing import Optional
from uuid import uuid4
import re

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** constants

# ** constant: page_range_locator_pattern
PAGE_RANGE_LOCATOR_PATTERN = re.compile(r'^(\d+)-(\d+)$')

# *** models

# ** model: citation
class Citation(DomainObject):
    '''
    An excerpt or paraphrase pulled from a source, together with its locator
    and enough surrounding context to be understood on its own. The atomic
    unit of evidence in this domain.
    '''

    # * attribute: id
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='The unique citation identifier, generated if absent.',
    )

    # * attribute: source_id
    source_id: str = Field(
        ...,
        description='The identifier of the source this citation was pulled from.',
    )

    # * attribute: locator
    locator: str = Field(
        ...,
        description='The precise locator of the excerpt within its source (e.g. a page range).',
    )

    # * attribute: excerpt
    excerpt: str = Field(
        ...,
        description='The quoted or paraphrased text pulled from the source.',
    )

    # * attribute: context_note
    context_note: Optional[str] = Field(
        default=None,
        description="An optional note describing the excerpt's surrounding context.",
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )

    # * method: normalize_locator
    def normalize_locator(self) -> str:
        '''
        Collapse a same-page page-range locator to a single page number.

        :return: The display locator.
        :rtype: str
        '''

        # Collapse equal start/end page-range pairs; leave everything else.
        match = PAGE_RANGE_LOCATOR_PATTERN.match(self.locator)
        if match and match.group(1) == match.group(2):
            return match.group(1)
        return self.locator

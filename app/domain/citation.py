"""Lit Review Citation Domain Model"""

# *** imports

# ** core
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

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
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description='The ISO 8601 creation timestamp.',
    )

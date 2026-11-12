"""Lit Review Linkage Domain Model"""

# *** imports

# ** core
from time import time
from typing import Optional
from uuid import uuid4

# ** infra
from pydantic import Field, field_validator

# ** app
from tiferet.domain.core import DomainObject

# *** constants

# ** constant: min_relevancy_weight
MIN_RELEVANCY_WEIGHT = 1

# ** constant: max_relevancy_weight
MAX_RELEVANCY_WEIGHT = 100

# *** functions

# ** function: is_relevancy_weight
def is_relevancy_weight(value: object) -> bool:
    '''
    Whether a value is a judged relevancy weight.

    A judged weight is an integer from 1 to 100 inclusive. Absent is not
    judged. ``True`` is rejected here so it cannot coerce to ``1``.

    :param value: The candidate weight.
    :type value: object
    :return: True when the value is an integer from 1 to 100.
    :rtype: bool
    '''

    # Bool is an int subclass; reject it before the range check.
    if isinstance(value, bool) or not isinstance(value, int):
        return False

    # A judged weight is inclusive of both ends of the scale.
    return MIN_RELEVANCY_WEIGHT <= value <= MAX_RELEVANCY_WEIGHT

# *** models

# ** model: linkage
class Linkage(DomainObject):
    '''
    The relationship connecting a citation to a theme. Forming a linkage is
    a structural fact; synthesis is an explicit later act against the full
    linkage set. A linkage may later be retired -- excluded from synthesis
    and the default evidence view without being deleted -- and reinstated,
    per RFP-7. It may also carry a researcher-confirmed relevancy weight for
    this mapping alone. Absent means unjudged, not a low score.
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

    # * attribute: relevancy_weight
    relevancy_weight: Optional[int] = Field(
        default=None,
        description=(
            'Researcher-confirmed thematic novelty of this mapping, an integer '
            'from 1 to 100. None means unjudged, not a low score.'
        ),
    )

    # * method: _validate_relevancy_weight (field validator)
    @field_validator('relevancy_weight', mode='before')
    @classmethod
    def _validate_relevancy_weight(cls, value: object) -> Optional[int]:
        '''
        Accept an absent or 1-100 weight; reject 0, out of range, and bools.

        :param value: The raw relevancy weight.
        :type value: object
        :return: None, or an integer from 1 to 100.
        :rtype: Optional[int]
        '''

        # Absent is unjudged. It is not weight 0.
        if value is None:
            return None

        # Reject 0, negatives, values above 100, non-integers, and bools.
        if not is_relevancy_weight(value):
            raise ValueError(
                'Relevancy weight must be an integer from 1 to 100, or absent.'
            )

        # Return the judged weight.
        return value

    # * method: is_active
    def is_active(self) -> bool:
        '''
        Whether this linkage is currently active (not retired).

        :return: True when retired_at is None, otherwise False.
        :rtype: bool
        '''

        # A linkage is active exactly when it has never been retired.
        return self.retired_at is None

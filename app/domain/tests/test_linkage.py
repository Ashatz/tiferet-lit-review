"""Lit Review Linkage Domain Tests"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from app.domain.citation import Citation
from app.domain.linkage import Linkage
from app.domain.theme import Theme
from app.mappers.linkage import LinkageAggregate

# *** tests

# ** test: test_linkage_accepts_absent_and_boundary_weights
@pytest.mark.parametrize('weight', [None, 1, 100])
def test_linkage_accepts_absent_and_boundary_weights(weight):
    '''
    A linkage accepts an unjudged weight and the inclusive 1-100 bounds.

    :param weight: The candidate relevancy weight.
    :type weight: int | None
    '''

    # Construct a linkage with the candidate weight.
    linkage = Linkage(
        citation_id='citation-1',
        theme_id='theme-1',
        relevancy_weight=weight,
    )

    # The stored judgment is exactly the supplied value, never coerced to 0.
    assert linkage.relevancy_weight == weight
    assert linkage.relevancy_weight != 0 or weight == 0

# ** test: test_linkage_rejects_invalid_weights
@pytest.mark.parametrize('weight', [0, 101, -1, True, 1.5, '42'])
def test_linkage_rejects_invalid_weights(weight):
    '''
    A linkage rejects 0, out of range, non-integers, and bools.

    :param weight: The rejected candidate.
    :type weight: object
    '''

    # True must not become 1, and 0 must not be a judged weight.
    with pytest.raises(ValidationError):
        Linkage(
            citation_id='citation-1',
            theme_id='theme-1',
            relevancy_weight=weight,
        )

# ** test: test_set_and_clear_relevancy_weight_are_idempotent
def test_set_and_clear_relevancy_weight_are_idempotent():
    '''
    Set and clear change the weight only, and do nothing when already there.
    '''

    # A new linkage is unjudged and active.
    linkage = LinkageAggregate(citation_id='citation-1', theme_id='theme-1')
    assert linkage.relevancy_weight is None
    assert linkage.is_active() is True

    # Setting a weight does not retire the linkage.
    assert linkage.set_relevancy_weight(42) is True
    assert linkage.relevancy_weight == 42
    assert linkage.retired_at is None
    assert linkage.set_relevancy_weight(42) is False

    # Clearing returns it to unjudged without touching retirement.
    assert linkage.clear_relevancy_weight() is True
    assert linkage.relevancy_weight is None
    assert linkage.clear_relevancy_weight() is False
    assert linkage.is_active() is True

# ** test: test_retire_and_reinstate_keep_relevancy_weight
def test_retire_and_reinstate_keep_relevancy_weight():
    '''
    Retirement and reinstatement do not clear a recorded weight.
    '''

    # Judge the mapping, then retire and reinstate it.
    linkage = LinkageAggregate(citation_id='citation-1', theme_id='theme-1')
    linkage.set_relevancy_weight(15)
    linkage.retire(reason='Displaced.')
    assert linkage.relevancy_weight == 15
    linkage.reinstate()

    # The weight survives both editorial acts.
    assert linkage.is_active() is True
    assert linkage.relevancy_weight == 15
    assert linkage.retirement_reason is None

# ** test: test_citation_and_theme_do_not_carry_relevancy_weight
def test_citation_and_theme_do_not_carry_relevancy_weight():
    '''
    The weight lives on the linkage only.
    '''

    # Neither noun gains the mapping's judgment.
    assert 'relevancy_weight' not in Citation.model_fields
    assert 'relevancy_weight' not in Theme.model_fields

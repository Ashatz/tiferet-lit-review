"""Lit Review Activity H5 Repository Integration Tests"""

# *** imports

# ** infra
import pytest

# ** app
from app.domain.activity import (
    LINKAGE_CREATED_ACTION,
    SOURCE_ADDED_ACTION,
    SOURCE_SUBJECT_TYPE,
    THEME_SUBJECT_TYPE,
    THEME_SYNTHESIZED_ACTION,
)
from app.mappers.activity import ActivityAggregate
from app.repos.activity import ACTIVITIES_TABLE_PATH, ActivityH5Repository

# *** constants

# ** constant: source_id
SOURCE_ID = '4cfaeea5-869a-444a-8a51-7680812c118d'

# ** constant: theme_id
THEME_ID = 'universal-ir-abstractions'

# ** constant: citation_id
CITATION_ID = '02a49f90-0ff1-48cb-916a-fbc92f9712dd'

# *** fixtures

# ** fixture: repo
@pytest.fixture
def repo(tmp_path) -> ActivityH5Repository:
    '''
    Build an activity repository against a temporary HDF5 file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: An activity H5 repository.
    :rtype: ActivityH5Repository
    '''

    # Return a repository pointing at an isolated temp file.
    return ActivityH5Repository(h5_file=str(tmp_path / 'lit_review.h5'))

# *** tests

# ** test_int: test_list_against_missing_table_returns_empty
def test_list_against_missing_table_returns_empty(repo):
    '''
    Listing against a store with no activities table yet returns [] and
    does not create the table (AC #8).

    :param repo: The temporary activity repository.
    :type repo: ActivityH5Repository
    '''

    # No record() call has happened yet; the table does not exist.
    assert repo.list() == []
    with repo.client() as h5:
        assert h5.node_exists(ACTIVITIES_TABLE_PATH) is False

# ** test_int: test_record_creates_table_lazily_on_first_call
def test_record_creates_table_lazily_on_first_call(repo):
    '''
    The first record() call creates the activities table (AC #8).

    :param repo: The temporary activity repository.
    :type repo: ActivityH5Repository
    '''

    # Append a single entry.
    repo.record(ActivityAggregate(
        action=SOURCE_ADDED_ACTION,
        subject_type=SOURCE_SUBJECT_TYPE,
        subject_id=SOURCE_ID,
    ))

    # The table now exists and holds exactly the one appended row.
    with repo.client() as h5:
        assert h5.node_exists(ACTIVITIES_TABLE_PATH) is True
    entries = repo.list()
    assert len(entries) == 1
    assert entries[0].action == SOURCE_ADDED_ACTION

# ** test_int: test_record_is_append_only_and_list_is_newest_first
def test_record_is_append_only_and_list_is_newest_first(repo):
    '''
    Every record() call appends a new row; list() returns newest-first (AC #7).

    :param repo: The temporary activity repository.
    :type repo: ActivityH5Repository
    '''

    # Append three entries in a known order.
    first = ActivityAggregate(
        action=SOURCE_ADDED_ACTION,
        subject_type=SOURCE_SUBJECT_TYPE,
        subject_id='source-1',
    )
    second = ActivityAggregate(
        action=SOURCE_ADDED_ACTION,
        subject_type=SOURCE_SUBJECT_TYPE,
        subject_id='source-2',
    )
    third = ActivityAggregate(
        action=LINKAGE_CREATED_ACTION,
        subject_type=THEME_SUBJECT_TYPE,
        subject_id=THEME_ID,
        related_type=SOURCE_SUBJECT_TYPE,
        related_id=CITATION_ID,
    )
    repo.record(first)
    repo.record(second)
    repo.record(third)

    # No row is ever overwritten; three rows persist, newest-insertion-first.
    entries = repo.list()
    assert [entry.subject_id for entry in entries] == [
        THEME_ID,
        'source-2',
        'source-1',
    ]

# ** test_int: test_list_filters_by_action_subject_type_subject_id_and_related_id
def test_list_filters_by_action_subject_type_subject_id_and_related_id(repo):
    '''
    Each optional filter narrows the result set independently (AC #7).

    :param repo: The temporary activity repository.
    :type repo: ActivityH5Repository
    '''

    # Append a mix of source-added and linkage-created entries.
    repo.record(ActivityAggregate(
        action=SOURCE_ADDED_ACTION,
        subject_type=SOURCE_SUBJECT_TYPE,
        subject_id=SOURCE_ID,
    ))
    repo.record(ActivityAggregate(
        action=LINKAGE_CREATED_ACTION,
        subject_type=THEME_SUBJECT_TYPE,
        subject_id=THEME_ID,
        related_type=SOURCE_SUBJECT_TYPE,
        related_id=CITATION_ID,
    ))
    repo.record(ActivityAggregate(
        action=THEME_SYNTHESIZED_ACTION,
        subject_type=THEME_SUBJECT_TYPE,
        subject_id=THEME_ID,
    ))

    # Each filter narrows the set to just the matching entries.
    assert [e.action for e in repo.list(action=SOURCE_ADDED_ACTION)] == [SOURCE_ADDED_ACTION]
    assert len(repo.list(subject_type=THEME_SUBJECT_TYPE)) == 2
    assert len(repo.list(subject_id=SOURCE_ID)) == 1
    assert [e.action for e in repo.list(related_id=CITATION_ID)] == [LINKAGE_CREATED_ACTION]

# ** test_int: test_record_round_trips_changed_fields_list
def test_record_round_trips_changed_fields_list(repo):
    '''
    changed_fields round-trips as a list of field names, not a joined string.

    :param repo: The temporary activity repository.
    :type repo: ActivityH5Repository
    '''

    # Append an entry with multiple changed field names.
    repo.record(ActivityAggregate(
        action=SOURCE_ADDED_ACTION,
        subject_type=SOURCE_SUBJECT_TYPE,
        subject_id=SOURCE_ID,
        changed_fields=['title', 'year', 'overview_note'],
    ))

    # The reloaded entry carries the exact same list, in order.
    entries = repo.list()
    assert entries[0].changed_fields == ['title', 'year', 'overview_note']

# ** test_int: test_record_with_no_changed_fields_round_trips_empty_list
def test_record_with_no_changed_fields_round_trips_empty_list(repo):
    '''
    An entry with no changed fields round-trips as an empty list, not [''].

    :param repo: The temporary activity repository.
    :type repo: ActivityH5Repository
    '''

    # Append an entry with the default, empty changed_fields.
    repo.record(ActivityAggregate(
        action=SOURCE_ADDED_ACTION,
        subject_type=SOURCE_SUBJECT_TYPE,
        subject_id=SOURCE_ID,
    ))

    # The reloaded entry's changed_fields is empty, not a list with one blank.
    entries = repo.list()
    assert entries[0].changed_fields == []

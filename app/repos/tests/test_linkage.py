"""Lit Review Linkage H5 Repository Integration Tests"""

# *** imports

# ** core
from pathlib import Path

# ** infra
import pytest
import tables

# ** app
from app.mappers.linkage import LinkageAggregate
from app.repos.linkage import LINKAGES_TABLE_PATH, LinkageH5Repository

# *** constants

# ** constant: citation_id
CITATION_ID = '02a49f90-0ff1-48cb-916a-fbc92f9712dd'

# ** constant: theme_id
THEME_ID = 'universal-ir-abstractions'

# *** fixtures

# ** fixture: repo
@pytest.fixture
def repo(tmp_path) -> LinkageH5Repository:
    '''
    Build a linkage repository against a temporary HDF5 file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: A linkage H5 repository.
    :rtype: LinkageH5Repository
    '''

    # Return a repository pointing at an isolated temp file.
    return LinkageH5Repository(h5_file=str(tmp_path / 'lit_review.h5'))

# ** fixture: linkage
@pytest.fixture
def linkage() -> LinkageAggregate:
    '''
    Build a linkage aggregate to persist.

    :return: A linkage for the sample citation and theme.
    :rtype: LinkageAggregate
    '''

    # Return the structural pair used by the round-trip tests.
    return LinkageAggregate(citation_id=CITATION_ID, theme_id=THEME_ID)

# *** tests

# ** test_int: test_save_and_get_loads_new_linkage_as_active
def test_save_and_get_loads_new_linkage_as_active(repo, linkage):
    '''
    A freshly saved linkage rehydrates as active (retired_at is None), not
    at the HDF5 zero-timestamp sentinel.

    :param repo: The temporary linkage repository.
    :type repo: LinkageH5Repository
    :param linkage: The linkage fixture.
    :type linkage: LinkageAggregate
    '''

    # Persist and reload the linkage.
    repo.save(linkage)
    loaded = repo.get(linkage.id)

    # The active sentinel (retired_at == 0 on disk) is restored to None.
    assert loaded is not None
    assert loaded.is_active() is True
    assert loaded.retired_at is None

# ** test_int: test_retire_and_reinstate_round_trip
def test_retire_and_reinstate_round_trip(repo, linkage):
    '''
    Retiring and reinstating a linkage persists and reloads correctly.

    :param repo: The temporary linkage repository.
    :type repo: LinkageH5Repository
    :param linkage: The linkage fixture.
    :type linkage: LinkageAggregate
    '''

    # Save the active linkage, then retire and re-save it.
    repo.save(linkage)
    linkage.retire(reason='Superseded by stronger corroboration.')
    repo.save(linkage)

    # The reloaded linkage is retired with its timestamp and reason intact.
    retired = repo.get(linkage.id)
    assert retired.is_active() is False
    assert retired.retired_at == linkage.retired_at
    assert retired.retirement_reason == 'Superseded by stronger corroboration.'

    # Reinstating and re-saving restores the active sentinel on reload.
    retired.reinstate()
    repo.save(retired)
    reinstated = repo.get(linkage.id)
    assert reinstated.is_active() is True
    assert reinstated.retired_at is None

    # StringCol has no null either; a cleared reason round-trips as ''
    # rather than None, matching the existing context_note convention.
    assert not reinstated.retirement_reason

# ** test_int: test_save_migrates_pre_rfp7_schema
def test_save_migrates_pre_rfp7_schema(repo, linkage):
    '''
    Saving against a table predating the retirement columns migrates the
    schema, preserving the pre-existing row as active.

    :param repo: The temporary linkage repository.
    :type repo: LinkageH5Repository
    :param linkage: The linkage fixture.
    :type linkage: LinkageAggregate
    '''

    # Build the old (pre-RFP-7) four-column schema by hand.
    class OldLinkageDescription(tables.IsDescription):
        id = tables.StringCol(64)
        citation_id = tables.StringCol(64)
        theme_id = tables.StringCol(64)
        created_at = tables.Int64Col()

    with repo.client() as h5:
        parent = h5.create_group('/lit_review')
        table = h5.h5file.create_table(parent, 'linkages', OldLinkageDescription)
        row = table.row
        row['id'] = linkage.id.encode('utf-8')
        row['citation_id'] = CITATION_ID.encode('utf-8')
        row['theme_id'] = THEME_ID.encode('utf-8')
        row['created_at'] = linkage.created_at
        row.append()
        table.flush()

    # Reading the old-schema row already loads it as active (missing
    # columns fall back to Linkage domain defaults).
    preexisting = repo.get(linkage.id)
    assert preexisting is not None
    assert preexisting.is_active() is True

    # Saving a new linkage against the stale schema must not fail, and
    # migration must preserve the pre-existing row.
    other = LinkageAggregate(citation_id='other-citation', theme_id=THEME_ID)
    repo.save(other)

    migrated_existing = repo.get(linkage.id)
    migrated_other = repo.get(other.id)
    assert migrated_existing is not None
    assert migrated_existing.is_active() is True
    assert migrated_other is not None
    assert migrated_other.is_active() is True

    with repo.client() as h5:
        table = h5.get_table(LINKAGES_TABLE_PATH)
        assert 'retired_at' in table.colnames
        assert 'retirement_reason' in table.colnames
        assert 'relevancy_weight' in table.colnames
    assert migrated_existing.relevancy_weight is None
    assert migrated_other.relevancy_weight is None

# ** test_int: test_relevancy_weight_round_trips_absent_and_judged
def test_relevancy_weight_round_trips_absent_and_judged(repo, linkage):
    '''
    Absent weight stores as 0 and restores to None; 42 round-trips.

    :param repo: The temporary linkage repository.
    :type repo: LinkageH5Repository
    :param linkage: The linkage fixture.
    :type linkage: LinkageAggregate
    '''

    # An unjudged linkage encodes None as the stored sentinel.
    repo.save(linkage)
    with repo.client() as h5:
        stored = h5.read_rows(LINKAGES_TABLE_PATH)[0]
    assert int(stored['relevancy_weight']) == 0

    # A stored 0 must never surface as weight 0.
    loaded = repo.get(linkage.id)
    assert loaded.relevancy_weight is None
    assert loaded.retired_at is None
    assert loaded.relevancy_weight is None or 1 <= loaded.relevancy_weight <= 100

    # A judged weight and retirement fields survive together.
    linkage.set_relevancy_weight(42)
    linkage.retire(reason='Keep the judgment.')
    retired_at = linkage.retired_at
    repo.save(linkage)
    reloaded = repo.get(linkage.id)
    assert reloaded.relevancy_weight == 42
    assert reloaded.retired_at == retired_at
    assert reloaded.retirement_reason == 'Keep the judgment.'
    assert 1 <= reloaded.relevancy_weight <= 100

# ** test_int: test_pre_weight_table_reads_without_rewrite_then_migrates
def test_pre_weight_table_reads_without_rewrite_then_migrates(repo, linkage):
    '''
    A current table reads as absent weight until the next linkage write.

    :param repo: The temporary linkage repository.
    :type repo: LinkageH5Repository
    :param linkage: The linkage fixture.
    :type linkage: LinkageAggregate
    '''

    # Build the pre-weight schema and a sibling group in the same file.
    class PreWeightLinkageDescription(tables.IsDescription):
        id = tables.StringCol(64)
        citation_id = tables.StringCol(64)
        theme_id = tables.StringCol(64)
        created_at = tables.Int64Col()
        retired_at = tables.Int64Col()
        retirement_reason = tables.StringCol(1000)

    with repo.client() as h5:
        parent = h5.create_group('/lit_review')
        table = h5.h5file.create_table(parent, 'linkages', PreWeightLinkageDescription)
        row = table.row
        row['id'] = linkage.id.encode('utf-8')
        row['citation_id'] = CITATION_ID.encode('utf-8')
        row['theme_id'] = THEME_ID.encode('utf-8')
        row['created_at'] = linkage.created_at
        row['retired_at'] = 0
        row['retirement_reason'] = b''
        row.append()
        table.flush()
        sibling = h5.h5file.create_group('/lit_review', 'sibling')
        sibling._v_attrs.marker = 'untouched'

    # Get and list must not rewrite a pre-weight table.
    path = Path(repo.h5_file)
    before = path.read_bytes()
    reader = LinkageH5Repository(h5_file=repo.h5_file, mode='r')
    loaded = reader.get(linkage.id)
    listed = reader.list(theme_id=THEME_ID)
    assert loaded.relevancy_weight is None
    assert listed[0].relevancy_weight is None
    assert loaded.relevancy_weight is None or 1 <= loaded.relevancy_weight <= 100
    assert path.read_bytes() == before
    with reader.client() as h5:
        assert 'relevancy_weight' not in h5.get_table(LINKAGES_TABLE_PATH).colnames

    # The next save adds the column, keeps the row, and leaves the sibling.
    other = LinkageAggregate(citation_id='other-citation', theme_id=THEME_ID)
    other.set_relevancy_weight(11)
    repo.save(other)
    kept = repo.get(linkage.id)
    added = repo.get(other.id)
    assert kept is not None
    assert kept.citation_id == CITATION_ID
    assert kept.relevancy_weight is None
    assert kept.is_active() is True
    assert added.relevancy_weight == 11
    with repo.client() as h5:
        table = h5.get_table(LINKAGES_TABLE_PATH)
        assert 'relevancy_weight' in table.colnames
        assert table.nrows == 2
        sibling = h5.h5file.get_node('/lit_review/sibling')
        assert sibling._v_attrs.marker == 'untouched'

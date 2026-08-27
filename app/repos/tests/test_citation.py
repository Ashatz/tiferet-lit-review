"""Lit Review Citation H5 Repository Integration Tests"""

# *** imports

# ** infra
import pytest
import tables

# ** app
from app.mappers.citation import CitationAggregate, CitationTableObject
from app.repos.citation import (
    CITATIONS_BACKUP_LEAF,
    CITATIONS_BACKUP_PATH,
    CITATIONS_STAGING_LEAF,
    CITATIONS_STAGING_PATH,
    CITATIONS_TABLE_LEAF,
    CITATIONS_TABLE_PATH,
    CitationH5Repository,
)

# *** constants

# ** constant: legacy_row_one
LEGACY_ROW_ONE = {
    'id': 'legacy-citation-1',
    'source_id': 'source-1',
    'locator': '4-4',
    'excerpt': 'Operations are the unit.',
    'context_note': 'From the introduction.',
    'created_at': 1700000000,
}

# ** constant: legacy_row_two
LEGACY_ROW_TWO = {
    'id': 'legacy-citation-2',
    'source_id': 'source-1',
    'locator': '9-9',
    'excerpt': 'A second, unrelated excerpt.',
    'context_note': '',
    'created_at': 1700000100,
}

# *** functions

# ** function: old_citation_description
def old_citation_description() -> type:
    '''
    Build the pre-RFP-8 five-column citation table schema by hand.

    :return: A tables.IsDescription subclass without a title column.
    :rtype: type
    '''

    # Return a fresh class each call so PyTables never sees a shared type.
    class OldCitationDescription(tables.IsDescription):
        id = tables.StringCol(64)
        source_id = tables.StringCol(64)
        locator = tables.StringCol(64)
        excerpt = tables.StringCol(4000)
        context_note = tables.StringCol(4000)
        created_at = tables.Int64Col()

    return OldCitationDescription

# ** function: pre_rfp9_citation_description
def pre_rfp9_citation_description() -> type:
    '''
    Build the post-RFP-8 / pre-RFP-9 six-column citation table schema.

    Carries the title column already but still at the old 4,000-byte
    excerpt / context_note width, so column presence alone cannot detect
    that this table needs an upgrade.

    :return: A tables.IsDescription subclass with a narrow excerpt/context_note.
    :rtype: type
    '''

    # Return a fresh class each call so PyTables never sees a shared type.
    class PreRfp9CitationDescription(tables.IsDescription):
        id = tables.StringCol(64)
        source_id = tables.StringCol(64)
        locator = tables.StringCol(64)
        excerpt = tables.StringCol(4000)
        context_note = tables.StringCol(4000)
        title = tables.StringCol(256)
        created_at = tables.Int64Col()

    return PreRfp9CitationDescription

# ** function: write_pre_rfp9_table
def write_pre_rfp9_table(repo: CitationH5Repository, rows: list) -> None:
    '''
    Create a title-aware but narrow-text citations table with the given rows.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    :param rows: Plain field dicts matching the pre-RFP-9 schema.
    :type rows: list
    '''

    # Build the group and pre-RFP-9-schema table directly through PyTables.
    with repo.client() as h5:
        parent = h5.create_group('/lit_review')
        table = h5.h5file.create_table(parent, CITATIONS_TABLE_LEAF, pre_rfp9_citation_description())
        for data in rows:
            row = table.row
            row['id'] = data['id'].encode('utf-8')
            row['source_id'] = data['source_id'].encode('utf-8')
            row['locator'] = data['locator'].encode('utf-8')
            row['excerpt'] = data['excerpt'].encode('utf-8')
            row['context_note'] = data['context_note'].encode('utf-8')
            row['title'] = data.get('title', '').encode('utf-8')
            row['created_at'] = data['created_at']
            row.append()
        table.flush()

# ** function: write_legacy_table
def write_legacy_table(repo: CitationH5Repository, rows: list) -> None:
    '''
    Create the legacy (title-less) citations table with the given rows.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    :param rows: Plain field dicts matching the pre-RFP-8 schema.
    :type rows: list
    '''

    # Build the group and old-schema table directly through PyTables.
    with repo.client() as h5:
        parent = h5.create_group('/lit_review')
        table = h5.h5file.create_table(parent, CITATIONS_TABLE_LEAF, old_citation_description())
        for data in rows:
            row = table.row
            row['id'] = data['id'].encode('utf-8')
            row['source_id'] = data['source_id'].encode('utf-8')
            row['locator'] = data['locator'].encode('utf-8')
            row['excerpt'] = data['excerpt'].encode('utf-8')
            row['context_note'] = data['context_note'].encode('utf-8')
            row['created_at'] = data['created_at']
            row.append()
        table.flush()

# *** fixtures

# ** fixture: repo
@pytest.fixture
def repo(tmp_path) -> CitationH5Repository:
    '''
    Build a citation repository against a temporary HDF5 file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: A citation H5 repository.
    :rtype: CitationH5Repository
    '''

    # Return a repository pointing at an isolated temp file.
    return CitationH5Repository(h5_file=str(tmp_path / 'lit_review.h5'))

# *** tests

# ** test_int: test_save_and_get_round_trip_with_and_without_title
def test_save_and_get_round_trip_with_and_without_title(repo):
    '''
    A fresh store persists both a titled and a title-less citation.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Save one citation with a title and one without.
    titled = CitationAggregate(
        id='titled-citation',
        source_id='source-1',
        locator='1-1',
        excerpt='An excerpt.',
        title='A researcher-authored label',
    )
    untitled = CitationAggregate(
        id='untitled-citation',
        source_id='source-1',
        locator='2-2',
        excerpt='Another excerpt.',
    )
    repo.save(titled)
    repo.save(untitled)

    # Each reloads with its title exactly as saved.
    assert repo.get('titled-citation').title == 'A researcher-authored label'
    assert repo.get('untitled-citation').title is None

# ** test_int: test_get_and_list_resolve_legacy_table_without_upgrading
def test_get_and_list_resolve_legacy_table_without_upgrading(repo):
    '''
    Reading a legacy table resolves title-less citations without upgrading
    the on-disk schema; only a save triggers the upgrade.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Build a legacy table with two rows and no title column.
    write_legacy_table(repo, [LEGACY_ROW_ONE, LEGACY_ROW_TWO])

    # Both get and list resolve every field, with title defaulting to None.
    fetched = repo.get(LEGACY_ROW_ONE['id'])
    listed = repo.list()
    assert fetched is not None
    assert fetched.title is None
    assert fetched.excerpt == LEGACY_ROW_ONE['excerpt']
    assert {c.id for c in listed} == {LEGACY_ROW_ONE['id'], LEGACY_ROW_TWO['id']}
    assert all(c.title is None for c in listed)

    # Reads alone must not touch the on-disk schema.
    with repo.client() as h5:
        table = h5.get_table(CITATIONS_TABLE_PATH)
        assert 'title' not in table.colnames

# ** test_int: test_save_upgrades_legacy_table_preserving_existing_rows
def test_save_upgrades_legacy_table_preserving_existing_rows(repo):
    '''
    Saving a new citation against a legacy table upgrades the schema in
    place, preserving every pre-existing field exactly (AC #6).

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Build a legacy table with two pre-existing rows.
    write_legacy_table(repo, [LEGACY_ROW_ONE, LEGACY_ROW_TWO])

    # Save a brand-new, titled citation against the stale schema.
    new_citation = CitationAggregate(
        id='new-citation',
        source_id='source-1',
        locator='7-7',
        excerpt='A freshly captured excerpt.',
        title='New evidence',
    )
    repo.save(new_citation)

    # The table now carries the title column and all three rows.
    with repo.client() as h5:
        table = h5.get_table(CITATIONS_TABLE_PATH)
        assert 'title' in table.colnames
        assert table.nrows == 3
        assert not h5.node_exists(CITATIONS_STAGING_PATH)
        assert not h5.node_exists(CITATIONS_BACKUP_PATH)

    # Every pre-existing field is preserved exactly; legacy rows are title-less.
    first = repo.get(LEGACY_ROW_ONE['id'])
    second = repo.get(LEGACY_ROW_TWO['id'])
    third = repo.get('new-citation')
    for loaded, expected in ((first, LEGACY_ROW_ONE), (second, LEGACY_ROW_TWO)):
        assert loaded.source_id == expected['source_id']
        assert loaded.locator == expected['locator']
        assert loaded.excerpt == expected['excerpt']
        assert loaded.created_at == expected['created_at']
        assert loaded.title is None
    assert third.title == 'New evidence'

# ** test_int: test_save_recovers_by_promoting_valid_staging
def test_save_recovers_by_promoting_valid_staging(repo):
    '''
    A save recovers a promoted-but-uncleaned upgrade by verifying and
    dropping the leftover backup (AC #7 recovery path).

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Build a legacy table, then hand-simulate an upgrade interrupted after
    # promotion but before the backup was removed.
    write_legacy_table(repo, [LEGACY_ROW_ONE, LEGACY_ROW_TWO])
    with repo.client() as h5:
        legacy_rows = h5.read_rows(CITATIONS_TABLE_PATH)
        staging_table = h5.create_table(CITATIONS_STAGING_PATH, CitationTableObject.get_description())
        for row in legacy_rows:
            CitationTableObject.from_row(row).to_row(staging_table)
        staging_table.flush()
        h5.h5file.rename_node(CITATIONS_TABLE_PATH, CITATIONS_BACKUP_LEAF)
        h5.h5file.rename_node(CITATIONS_STAGING_PATH, CITATIONS_TABLE_LEAF)
        # Interruption happens here, before the backup is removed.

    # A subsequent save must finish cleanup rather than fail or duplicate rows.
    new_citation = CitationAggregate(
        id='new-citation',
        source_id='source-1',
        locator='7-7',
        excerpt='A freshly captured excerpt.',
    )
    repo.save(new_citation)

    with repo.client() as h5:
        assert not h5.node_exists(CITATIONS_BACKUP_PATH)
        assert not h5.node_exists(CITATIONS_STAGING_PATH)
        table = h5.get_table(CITATIONS_TABLE_PATH)
        assert table.nrows == 3
        assert 'title' in table.colnames
    assert {c.id for c in repo.list()} == {
        LEGACY_ROW_ONE['id'], LEGACY_ROW_TWO['id'], 'new-citation',
    }

# ** test_int: test_fresh_store_creates_16384_byte_text_columns
def test_fresh_store_creates_16384_byte_text_columns(repo):
    '''
    A fresh store creates excerpt/context_note columns at the current
    16,384-byte capacity (AC #1).

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Save a citation to materialize the table on the current schema.
    repo.save(CitationAggregate(
        id='fresh-citation',
        source_id='source-1',
        locator='1-1',
        excerpt='An excerpt.',
    ))

    # Both text columns are declared at the current 16,384-byte capacity.
    with repo.client() as h5:
        table = h5.get_table(CITATIONS_TABLE_PATH)
        assert table.coldtypes['excerpt'].itemsize == 16384
        assert table.coldtypes['context_note'].itemsize == 16384

# ** test_int: test_save_round_trips_exact_capacity_boundary
def test_save_round_trips_exact_capacity_boundary(repo):
    '''
    Excerpt and context note text exactly at the 16,384-byte cap round-trip
    byte for byte (AC #2).

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Build multi-byte UTF-8 text landing exactly at the byte cap.
    exact_excerpt = ('é' * 8192)  # 2 bytes each == 16384 bytes.
    exact_note = 'x' * 16384
    citation = CitationAggregate(
        id='boundary-citation',
        source_id='source-1',
        locator='1-1',
        excerpt=exact_excerpt,
        context_note=exact_note,
    )
    repo.save(citation)

    # The reloaded citation carries both fields exactly as saved.
    reloaded = repo.get('boundary-citation')
    assert reloaded.excerpt == exact_excerpt
    assert reloaded.context_note == exact_note

# ** test_int: test_save_upgrades_table_with_undersized_text_columns
def test_save_upgrades_table_with_undersized_text_columns(repo):
    '''
    A save against a table that already has the title column but still
    carries 4,000-byte text columns triggers the width-aware upgrade, even
    though every declared column name is present (AC #4).

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Build a pre-RFP-9 table: title present, text columns still narrow.
    write_pre_rfp9_table(repo, [LEGACY_ROW_ONE, LEGACY_ROW_TWO])

    # Save a new citation against the stale-width schema.
    new_citation = CitationAggregate(
        id='new-citation',
        source_id='source-1',
        locator='7-7',
        excerpt='A freshly captured excerpt.',
    )
    repo.save(new_citation)

    # The table is upgraded to the current width; all rows are preserved.
    with repo.client() as h5:
        table = h5.get_table(CITATIONS_TABLE_PATH)
        assert table.coldtypes['excerpt'].itemsize == 16384
        assert table.coldtypes['context_note'].itemsize == 16384
        assert table.nrows == 3
        assert not h5.node_exists(CITATIONS_STAGING_PATH)
        assert not h5.node_exists(CITATIONS_BACKUP_PATH)
    first = repo.get(LEGACY_ROW_ONE['id'])
    second = repo.get(LEGACY_ROW_TWO['id'])
    assert first.excerpt == LEGACY_ROW_ONE['excerpt']
    assert first.context_note == LEGACY_ROW_ONE['context_note']
    assert second.excerpt == LEGACY_ROW_TWO['excerpt']

# ** test_int: test_save_recovers_by_rolling_back_when_staging_missing
def test_save_recovers_by_rolling_back_when_staging_missing(repo):
    '''
    A save recovers an upgrade interrupted before staging existed by
    rolling back to the backup, then completing the upgrade fresh.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Build a legacy table, then hand-simulate an upgrade interrupted right
    # after the legacy table was displaced but before staging was built.
    write_legacy_table(repo, [LEGACY_ROW_ONE, LEGACY_ROW_TWO])
    with repo.client() as h5:
        h5.h5file.rename_node(CITATIONS_TABLE_PATH, CITATIONS_BACKUP_LEAF)

    # A subsequent save must roll back and retry, never losing a row.
    new_citation = CitationAggregate(
        id='new-citation',
        source_id='source-1',
        locator='7-7',
        excerpt='A freshly captured excerpt.',
    )
    repo.save(new_citation)

    with repo.client() as h5:
        assert not h5.node_exists(CITATIONS_BACKUP_PATH)
        assert not h5.node_exists(CITATIONS_STAGING_PATH)
        table = h5.get_table(CITATIONS_TABLE_PATH)
        assert table.nrows == 3
        assert 'title' in table.colnames
    assert {c.id for c in repo.list()} == {
        LEGACY_ROW_ONE['id'], LEGACY_ROW_TWO['id'], 'new-citation',
    }

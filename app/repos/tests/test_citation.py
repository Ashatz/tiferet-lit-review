"""Lit Review Citation H5 Repository Integration Tests"""

# *** imports

# ** infra
import pytest
import tables
from pydantic import ValidationError

# ** app
from app.domain.citation import MAX_CONTEXT_NOTE_BYTES, MAX_EXCERPT_BYTES
from app.mappers.citation import CitationAggregate, CitationTableObject
from app.repos.citation import (
    CITATIONS_BACKUP_LEAF,
    CITATIONS_BACKUP_PATH,
    CITATIONS_STAGING_LEAF,
    CITATIONS_STAGING_PATH,
    CITATIONS_TABLE_FILTERS,
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

# ** constant: rfp9_text_column_bytes
RFP9_TEXT_COLUMN_BYTES = 16384

# ** constant: rfp9_row_one
RFP9_ROW_ONE = {
    'id': 'rfp9-citation-1',
    'source_id': 'source-alpha',
    'locator': '12-14',
    'excerpt': 'Keep this excerpt exactly.',
    'context_note': 'Keep this note exactly.',
    'title': 'Exact title one',
    'created_at': 1700000001,
}

# ** constant: rfp9_row_two
RFP9_ROW_TWO = {
    'id': 'rfp9-citation-2',
    'source_id': 'source-beta',
    'locator': '3-3',
    'excerpt': 'Second excerpt, different source.',
    'context_note': 'Second note, preserved as stored.',
    'title': 'Exact title two',
    'created_at': 1700000002,
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

# ** function: rfp9_citation_description
def rfp9_citation_description() -> type:
    '''
    Build the post-RFP-9 / pre-RFP-14 six-column citation table schema.

    Carries title and the 16,384-byte excerpt / context_note widths that were
    current before this capacity increase.

    :return: A tables.IsDescription subclass at the RFP-9 text widths.
    :rtype: type
    '''

    # Return a fresh class each call so PyTables never sees a shared type.
    class Rfp9CitationDescription(tables.IsDescription):
        id = tables.StringCol(64)
        source_id = tables.StringCol(64)
        locator = tables.StringCol(64)
        excerpt = tables.StringCol(RFP9_TEXT_COLUMN_BYTES)
        context_note = tables.StringCol(RFP9_TEXT_COLUMN_BYTES)
        title = tables.StringCol(256)
        created_at = tables.Int64Col()

    return Rfp9CitationDescription

# ** function: write_rfp9_table
def write_rfp9_table(repo: CitationH5Repository, rows: list) -> None:
    '''
    Create a 16,384-byte text-width citations table with the given rows.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    :param rows: Plain field dicts matching the RFP-9 schema.
    :type rows: list
    '''

    # Build the group and RFP-9-schema table directly through PyTables.
    with repo.client() as h5:
        parent = h5.create_group('/lit_review')
        table = h5.h5file.create_table(parent, CITATIONS_TABLE_LEAF, rfp9_citation_description())
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

# ** function: assert_current_compressed_schema
def assert_current_compressed_schema(table) -> None:
    '''
    Assert the live table has 10,000,000-byte text columns and zlib complevel 5.

    :param table: The open PyTables citations table.
    :type table: Any
    '''

    # Widths and compression are the current on-disk contract.
    assert table.coldtypes['excerpt'].itemsize == MAX_EXCERPT_BYTES
    assert table.coldtypes['context_note'].itemsize == MAX_CONTEXT_NOTE_BYTES
    assert table.filters.complib == 'zlib'
    assert table.filters.complevel == 5

# ** function: assert_stored_fields
def assert_stored_fields(loaded: CitationAggregate, expected: dict) -> None:
    '''
    Assert every pre-existing stored field on a loaded citation matches.

    :param loaded: The citation returned by get or list.
    :type loaded: CitationAggregate
    :param expected: The field dict originally written to the table.
    :type expected: dict
    '''

    # Compare each stored field the expected row actually carried.
    assert loaded.id == expected['id']
    assert loaded.source_id == expected['source_id']
    assert loaded.locator == expected['locator']
    assert loaded.excerpt == expected['excerpt']
    assert loaded.context_note == expected['context_note']
    assert loaded.created_at == expected['created_at']
    if 'title' in expected:
        expected_title = expected['title'] or None
        assert loaded.title == expected_title

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

    # The table now carries the current compressed schema and all three rows.
    with repo.client() as h5:
        table = h5.get_table(CITATIONS_TABLE_PATH)
        assert 'title' in table.colnames
        assert table.nrows == 3
        assert_current_compressed_schema(table)
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
        staging_table = h5.create_table(
            CITATIONS_STAGING_PATH,
            CitationTableObject.get_description(),
            filters=CITATIONS_TABLE_FILTERS,
        )
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

# ** test_int: test_fresh_store_creates_compressed_10_000_000_byte_text_columns
def test_fresh_store_creates_compressed_10_000_000_byte_text_columns(repo):
    '''
    A fresh store creates excerpt/context_note columns at 10,000,000 bytes
    with zlib complevel 5 (AC #1).

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

    # Both text columns are declared at the current compressed capacity.
    with repo.client() as h5:
        table = h5.get_table(CITATIONS_TABLE_PATH)
        assert_current_compressed_schema(table)

# ** test_int: test_save_round_trips_exact_capacity_boundary
def test_save_round_trips_exact_capacity_boundary(repo):
    '''
    ASCII and multi-byte UTF-8 text exactly at the 10,000,000-byte cap
    round-trip byte for byte; get/list return the full Citation (AC #2, #6).

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # ASCII excerpt and multi-byte UTF-8 note, each exactly at the byte cap.
    exact_excerpt = 'x' * MAX_EXCERPT_BYTES
    exact_note = 'é' * (MAX_CONTEXT_NOTE_BYTES // 2)
    assert len(exact_excerpt.encode('utf-8')) == MAX_EXCERPT_BYTES
    assert len(exact_note.encode('utf-8')) == MAX_CONTEXT_NOTE_BYTES
    citation = CitationAggregate(
        id='boundary-citation',
        source_id='source-1',
        locator='1-1',
        excerpt=exact_excerpt,
        context_note=exact_note,
        title='Full citation',
    )
    repo.save(citation)

    # get and list both return the full Citation, byte for byte.
    reloaded = repo.get('boundary-citation')
    listed = repo.list()
    assert isinstance(reloaded, CitationAggregate)
    assert reloaded.excerpt == exact_excerpt
    assert reloaded.context_note == exact_note
    assert reloaded.title == 'Full citation'
    assert len(listed) == 1
    assert listed[0].excerpt == exact_excerpt
    assert listed[0].context_note == exact_note

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

    # The table is upgraded to the current compressed width; all rows are preserved.
    with repo.client() as h5:
        table = h5.get_table(CITATIONS_TABLE_PATH)
        assert_current_compressed_schema(table)
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
        assert_current_compressed_schema(table)
    assert {c.id for c in repo.list()} == {
        LEGACY_ROW_ONE['id'], LEGACY_ROW_TWO['id'], 'new-citation',
    }

# ** test_int: test_oversize_text_rejected_before_row_changes
def test_oversize_text_rejected_before_row_changes(repo):
    '''
    10,000,001 UTF-8 bytes is rejected before any citation row changes (AC #2).

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Persist a valid citation that must remain untouched.
    original = CitationAggregate(
        id='kept-citation',
        source_id='source-1',
        locator='1-1',
        excerpt='Keep this excerpt.',
        context_note='Keep this note.',
    )
    repo.save(original)

    # ASCII and multi-byte values one byte over the cap cannot be constructed.
    with pytest.raises(ValidationError):
        CitationAggregate(
            id='oversize-ascii',
            source_id='source-1',
            locator='2-2',
            excerpt='x' * (MAX_EXCERPT_BYTES + 1),
        )
    with pytest.raises(ValidationError):
        CitationAggregate(
            id='oversize-utf8',
            source_id='source-1',
            locator='3-3',
            excerpt='Keep this excerpt.',
            context_note=('é' * (MAX_CONTEXT_NOTE_BYTES // 2) + 'y'),
        )

    # The live table still has only the original row, untruncated.
    with repo.client() as h5:
        table = h5.get_table(CITATIONS_TABLE_PATH)
        assert table.nrows == 1
    kept = repo.get('kept-citation')
    assert kept.excerpt == 'Keep this excerpt.'
    assert kept.context_note == 'Keep this note.'
    assert repo.get('oversize-ascii') is None
    assert repo.get('oversize-utf8') is None

# ** test_int: test_save_migrates_16384_byte_table_preserving_every_field
def test_save_migrates_16384_byte_table_preserving_every_field(repo):
    '''
    A 16,384-byte table migrates without lost, duplicated, reordered, or
    modified stored rows; the live table has zlib complevel 5 and the new
    widths. get/list return the full Citation (AC #3, #5, #6).

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Build a synthetic RFP-9 table with two fully populated rows.
    write_rfp9_table(repo, [RFP9_ROW_ONE, RFP9_ROW_TWO])

    # Save a new citation to trigger the width-aware copy-on-write upgrade.
    new_citation = CitationAggregate(
        id='new-citation',
        source_id='source-gamma',
        locator='8-8',
        excerpt='A freshly captured excerpt.',
        title='New evidence',
    )
    repo.save(new_citation)

    # The live table is compressed at the new widths; upgrade debris is gone.
    with repo.client() as h5:
        table = h5.get_table(CITATIONS_TABLE_PATH)
        assert_current_compressed_schema(table)
        assert table.nrows == 3
        assert not h5.node_exists(CITATIONS_STAGING_PATH)
        assert not h5.node_exists(CITATIONS_BACKUP_PATH)

    # Insertion order and every pre-existing field are preserved exactly.
    listed = repo.list()
    assert [citation.id for citation in listed] == [
        RFP9_ROW_ONE['id'],
        RFP9_ROW_TWO['id'],
        'new-citation',
    ]
    assert isinstance(listed[0], CitationAggregate)
    assert_stored_fields(listed[0], RFP9_ROW_ONE)
    assert_stored_fields(listed[1], RFP9_ROW_TWO)
    assert_stored_fields(repo.get(RFP9_ROW_ONE['id']), RFP9_ROW_ONE)
    assert_stored_fields(repo.get(RFP9_ROW_TWO['id']), RFP9_ROW_TWO)
    third = repo.get('new-citation')
    assert third.title == 'New evidence'
    assert third.excerpt == 'A freshly captured excerpt.'

# ** test_int: test_interruption_before_promotion_leaves_16384_table_readable
def test_interruption_before_promotion_leaves_16384_table_readable(repo):
    '''
    A forced interruption before promotion leaves the original 16,384-byte
    table readable via get and list (AC #4).

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Build a 16,384-byte table, then hand-simulate an upgrade interrupted
    # after staging was written but before the live table was displaced.
    write_rfp9_table(repo, [RFP9_ROW_ONE, RFP9_ROW_TWO])
    with repo.client() as h5:
        legacy_rows = h5.read_rows(CITATIONS_TABLE_PATH)
        staging_table = h5.create_table(
            CITATIONS_STAGING_PATH,
            CitationTableObject.get_description(),
            filters=CITATIONS_TABLE_FILTERS,
        )
        for row in legacy_rows:
            CitationTableObject.from_row(row).to_row(staging_table)
        staging_table.flush()

    # Reads must still resolve the original table at its original widths.
    fetched = repo.get(RFP9_ROW_ONE['id'])
    listed = repo.list()
    assert_stored_fields(fetched, RFP9_ROW_ONE)
    assert [citation.id for citation in listed] == [
        RFP9_ROW_ONE['id'],
        RFP9_ROW_TWO['id'],
    ]
    assert_stored_fields(listed[1], RFP9_ROW_TWO)
    with repo.client() as h5:
        table = h5.get_table(CITATIONS_TABLE_PATH)
        assert table.coldtypes['excerpt'].itemsize == RFP9_TEXT_COLUMN_BYTES
        assert table.coldtypes['context_note'].itemsize == RFP9_TEXT_COLUMN_BYTES
        assert h5.node_exists(CITATIONS_STAGING_PATH)
        assert not h5.node_exists(CITATIONS_BACKUP_PATH)


# ** test_int: test_remove_for_transfer_drops_only_the_citation_row
def test_remove_for_transfer_drops_only_the_citation_row(repo):
    '''
    Origin-only transfer remove drops the matching citation row and leaves others.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Persist two citations, then remove one for transfer.
    first = CitationAggregate(
        id='keep-citation',
        source_id='source-1',
        locator='1-1',
        excerpt='Keep this excerpt.',
    )
    second = CitationAggregate(
        id='move-citation',
        source_id='source-1',
        locator='2-2',
        excerpt='Move this excerpt.',
    )
    repo.save(first)
    repo.save(second)
    repo.remove_for_transfer('move-citation')

    # Only the transferred row is gone; the sibling row remains.
    assert repo.get('move-citation') is None
    kept = repo.get('keep-citation')
    assert kept is not None
    assert kept.excerpt == 'Keep this excerpt.'
    assert [citation.id for citation in repo.list()] == ['keep-citation']

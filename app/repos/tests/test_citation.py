"""Lit Review Citation H5 Repository Integration Tests"""

# *** imports

# ** core
from unittest import mock

# ** infra
import pytest
import tables
from pydantic import ValidationError
from tiferet_h5.utils import H5Client

# ** app
from app.domain.citation import (
    CITATION_TYPE_DEFAULT,
    CITATION_TYPE_LINK,
    MAX_CONTEXT_NOTE_BYTES,
    MAX_EXCERPT_BYTES,
)
from app.mappers.citation import CitationAggregate, CitationTableObject
from app.repos.citation import (
    CITATION_ORDER_ATTR,
    CITATION_TEXT_FILTERS,
    CITATIONS_NODE_PATH,
    CITATIONS_STAGING_PATH,
    CITATIONS_TABLE_BACKUP_PATH,
    CITATIONS_TABLE_LEAF,
    CITATIONS_TABLE_PATH,
    CONTEXT_NOTE_ARRAY_NAME,
    EXCERPT_ARRAY_NAME,
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

# ** constant: link_row
LINK_ROW = {
    'id': 'link-citation',
    'source_id': '',
    'locator': '',
    'excerpt': 'kabbalah:origin-citation',
    'context_note': 'Tiferet design note.',
    'title': 'Linked passage',
    'type': CITATION_TYPE_LINK,
    'created_at': 1700000200,
}

# *** functions

# ** function: old_citation_description
def old_citation_description() -> type:
    '''
    Build the pre-RFP-8 citation table schema by hand.

    :return: A tables.IsDescription subclass without a title or type column.
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


# ** function: narrow_current_description
def narrow_current_description() -> type:
    '''
    Build a current-column citation table with short text columns.

    :return: A tables.IsDescription subclass that can be updated in place.
    :rtype: type
    '''

    # Short columns prove save does not widen or convert the table.
    class NarrowCurrentDescription(tables.IsDescription):
        id = tables.StringCol(64)
        source_id = tables.StringCol(64)
        locator = tables.StringCol(64)
        excerpt = tables.StringCol(256)
        context_note = tables.StringCol(256)
        title = tables.StringCol(256)
        type = tables.StringCol(16)
        created_at = tables.Int64Col()

    return NarrowCurrentDescription


# ** function: write_table
def write_table(repo: CitationH5Repository, description: type, rows: list) -> None:
    '''
    Create a citations table with the given schema and rows.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    :param description: The PyTables description for the table.
    :type description: type
    :param rows: Plain field dicts to append.
    :type rows: list
    '''

    # Reuse the root group, and replace a table left by an earlier case.
    with repo.client() as h5:
        if h5.node_exists('/lit_review'):
            parent = h5.get_group('/lit_review')
        else:
            parent = h5.create_group('/lit_review')
        if h5.node_exists(CITATIONS_TABLE_PATH):
            h5.h5file.remove_node(CITATIONS_TABLE_PATH)
        table = h5.h5file.create_table(parent, CITATIONS_TABLE_LEAF, description)
        for data in rows:
            row = table.row
            for name in table.colnames:
                value = data.get(name, '' if name != 'created_at' else 0)
                if name == 'created_at':
                    row[name] = int(value or 0)
                else:
                    row[name] = str(value).encode('utf-8')
            row.append()
        table.flush()


# ** function: write_legacy_table
def write_legacy_table(repo: CitationH5Repository, rows: list) -> None:
    '''
    Create a title-less citations table with the given rows.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    :param rows: Plain field dicts matching the pre-RFP-8 schema.
    :type rows: list
    '''

    # Legacy rows have no title or type column.
    write_table(repo, old_citation_description(), rows)


# ** function: array_length
def array_length(repo: CitationH5Repository, citation_id: str, name: str) -> int:
    '''
    Return the stored byte length of one citation text array.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    :param citation_id: The citation whose array to measure.
    :type citation_id: str
    :param name: The array node name.
    :type name: str
    :return: The array length.
    :rtype: int
    '''

    # Length is the stored payload, not a fixed column width.
    path = f'{CITATIONS_NODE_PATH}/{citation_id}/{name}'
    with repo.client() as h5:
        return int(h5.get_array(path).shape[0])


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

# ** test_int: test_list_ids_on_unmigrated_table_reads_once
def test_list_ids_on_unmigrated_table_reads_once(repo):
    '''
    An unmigrated table still answers list without being converted.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Build a legacy table so missing title and type stay defaults.
    write_legacy_table(repo, [LEGACY_ROW_ONE, LEGACY_ROW_TWO])
    with mock.patch.object(
            H5Client,
            'read_rows',
            autospec=True,
            side_effect=H5Client.read_rows,
        ) as read_rows:
        listed = repo.list(ids=[LEGACY_ROW_TWO['id'], 'absent', LEGACY_ROW_ONE['id']])
        assert read_rows.call_count == 1
        assert read_rows.call_args.args[1] == CITATIONS_TABLE_PATH

    # Table order survives, and the node is still a table.
    assert [citation.id for citation in listed] == [
        LEGACY_ROW_ONE['id'],
        LEGACY_ROW_TWO['id'],
    ]
    assert listed[0].title is None
    assert listed[0].type == CITATION_TYPE_DEFAULT
    with repo.client() as h5:
        assert isinstance(h5.h5file.get_node(CITATIONS_TABLE_PATH), tables.Table)


# ** test_int: test_list_empty_ids_skips_store_access
@pytest.mark.parametrize('ids', [[], (), set()])
def test_list_empty_ids_skips_store_access(repo, ids):
    '''
    Empty ID selections return without opening or creating a store.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    :param ids: An empty ID collection.
    :type ids: list | tuple | set
    '''

    # An empty selection has no reason to acquire an HDF5 lock.
    with mock.patch.object(repo, 'client') as client:
        assert repo.list(ids=ids) == []
        client.assert_not_called()
    assert repo.file_exists() is False


# ** test_int: test_list_ids_missing_node
def test_list_ids_missing_node(repo):
    '''
    A missing citations node returns an empty selection.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Create an empty file without materializing citations.
    with repo.client():
        pass
    assert repo.list(ids=['absent']) == []


# ** test_int: test_get_legacy_table_does_not_migrate
def test_get_legacy_table_does_not_migrate(repo):
    '''
    Reading a legacy table does not convert it to groups.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Build a legacy table with two rows and no title column.
    write_legacy_table(repo, [LEGACY_ROW_ONE, LEGACY_ROW_TWO])
    fetched = repo.get(LEGACY_ROW_ONE['id'])
    assert fetched is not None
    assert fetched.excerpt == LEGACY_ROW_ONE['excerpt']
    assert fetched.title is None
    assert fetched.type == CITATION_TYPE_DEFAULT
    with repo.client() as h5:
        table = h5.get_table(CITATIONS_TABLE_PATH)
        assert 'title' not in table.colnames
        assert not h5.node_exists(CITATIONS_STAGING_PATH)


# ** test_int: test_save_does_not_migrate_a_table
def test_save_does_not_migrate_a_table(repo):
    '''
    Saving against a table does not convert it, and a stale table is not rewritten.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # A legacy table is missing columns. Save must refuse rather than migrate.
    write_legacy_table(repo, [LEGACY_ROW_ONE])
    with pytest.raises(RuntimeError, match='migrate_table_to_groups'):
        repo.save(CitationAggregate(
            id='new-citation',
            source_id='source-1',
            locator='7-7',
            excerpt='A freshly captured excerpt.',
        ))
    with repo.client() as h5:
        assert isinstance(h5.h5file.get_node(CITATIONS_TABLE_PATH), tables.Table)
        assert not h5.node_exists(CITATIONS_STAGING_PATH)
    assert repo.get(LEGACY_ROW_ONE['id']).excerpt == LEGACY_ROW_ONE['excerpt']

    # A current-column table can be updated in place and stays a table.
    write_table(repo, narrow_current_description(), [LEGACY_ROW_ONE])
    repo.save(CitationAggregate(
        id='new-citation',
        source_id='source-1',
        locator='7-7',
        excerpt='A freshly captured excerpt.',
        title='New evidence',
    ))
    with repo.client() as h5:
        table = h5.get_table(CITATIONS_TABLE_PATH)
        assert table.nrows == 2
        assert not h5.node_exists(CITATIONS_STAGING_PATH)
    assert repo.get('new-citation').title == 'New evidence'


# ** test_int: test_fresh_save_creates_sized_compressed_arrays
def test_fresh_save_creates_sized_compressed_arrays(repo):
    '''
    A fresh store stores text in arrays sized to the payload, not a 10 MB column.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Save a titled citation with a note, and one with neither.
    titled = CitationAggregate(
        id='z-citation',
        source_id='source-1',
        locator='1-1',
        excerpt='An excerpt.',
        context_note='A short note.',
        title='A researcher-authored label',
    )
    untitled = CitationAggregate(
        id='a-citation',
        source_id='source-1',
        locator='2-2',
        excerpt='Another excerpt.',
    )
    repo.save(titled)
    repo.save(untitled)

    # The citations node is a group. Absent title and note are absent nodes.
    with repo.client() as h5:
        assert isinstance(h5.h5file.get_node(CITATIONS_NODE_PATH), tables.Group)
        titled_attrs = h5.get_node_attrs(f'{CITATIONS_NODE_PATH}/z-citation')
        untitled_attrs = h5.get_node_attrs(f'{CITATIONS_NODE_PATH}/a-citation')
        excerpt = h5.get_array(f'{CITATIONS_NODE_PATH}/z-citation/{EXCERPT_ARRAY_NAME}')
        note = h5.get_array(f'{CITATIONS_NODE_PATH}/z-citation/{CONTEXT_NOTE_ARRAY_NAME}')
        assert titled_attrs['title'] == 'A researcher-authored label'
        assert 'title' not in untitled_attrs
        assert not h5.node_exists(
            f'{CITATIONS_NODE_PATH}/a-citation/{CONTEXT_NOTE_ARRAY_NAME}'
        )
        assert excerpt.shape[0] == len('An excerpt.'.encode('utf-8'))
        assert note.shape[0] == len('A short note.'.encode('utf-8'))
        assert excerpt.filters.complib == CITATION_TEXT_FILTERS.complib
        assert excerpt.filters.complevel == CITATION_TEXT_FILTERS.complevel
        assert excerpt.shape[0] != MAX_EXCERPT_BYTES

    # Round-trip and insertion order do not follow alphabetical ids.
    assert repo.get('z-citation').title == 'A researcher-authored label'
    assert repo.get('a-citation').title is None
    assert repo.get('a-citation').context_note is None
    assert [citation.id for citation in repo.list()] == ['z-citation', 'a-citation']


# ** test_int: test_link_pointer_round_trips_in_excerpt_array
def test_link_pointer_round_trips_in_excerpt_array(repo):
    '''
    A link citation keeps project_id:citation_id in the excerpt array.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Save a link whose excerpt is the pointer, not passage text.
    link = CitationAggregate(
        id='link-citation',
        excerpt='kabbalah:origin-citation',
        context_note='Tiferet design note.',
        title='Linked passage',
        type=CITATION_TYPE_LINK,
    )
    repo.save(link)
    reloaded = repo.get('link-citation')
    assert reloaded.type == CITATION_TYPE_LINK
    assert reloaded.excerpt == 'kabbalah:origin-citation'
    assert reloaded.context_note == 'Tiferet design note.'
    assert reloaded.source_id == ''
    assert reloaded.locator == ''
    with repo.client() as h5:
        stored = h5.get_array(
            f'{CITATIONS_NODE_PATH}/link-citation/{EXCERPT_ARRAY_NAME}'
        ).read()
        assert bytes(stored).decode('utf-8') == 'kabbalah:origin-citation'
    selected = repo.list(ids=['link-citation'])
    assert selected[0].model_dump() == reloaded.model_dump()


# ** test_int: test_get_does_not_read_another_citation_array
def test_get_does_not_read_another_citation_array(repo):
    '''
    get of one citation does not open another citation's text arrays.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Two citations, each with excerpt and note, so both have arrays.
    first = CitationAggregate(
        id='first-citation',
        source_id='source-1',
        locator='1-1',
        excerpt='First excerpt.',
        context_note='First note.',
    )
    second = CitationAggregate(
        id='second-citation',
        source_id='source-2',
        locator='2-2',
        excerpt='Second excerpt.',
        context_note='Second note.',
    )
    repo.save(first)
    repo.save(second)

    # Spy on array opens. The other citation's paths must not appear.
    with mock.patch.object(
            H5Client,
            'get_array',
            autospec=True,
            side_effect=H5Client.get_array,
        ) as get_array:
        loaded = repo.get('first-citation')
    paths = [call.args[1] for call in get_array.call_args_list]
    assert loaded.excerpt == 'First excerpt.'
    assert paths
    assert all('first-citation' in path for path in paths)
    assert not any('second-citation' in path for path in paths)


# ** test_int: test_list_ids_reads_arrays_only_for_selected_groups
def test_list_ids_reads_arrays_only_for_selected_groups(repo):
    '''
    list(ids=...) does not read an unselected citation's arrays.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Store two citations, then select only the second.
    repo.save(CitationAggregate(
        id='keep-closed',
        source_id='source-1',
        locator='1-1',
        excerpt='Do not read this.',
        context_note='Closed note.',
    ))
    repo.save(CitationAggregate(
        id='selected-citation',
        source_id='source-2',
        locator='2-2',
        excerpt='Read this.',
        context_note='Open note.',
    ))
    with mock.patch.object(
            H5Client,
            'get_array',
            autospec=True,
            side_effect=H5Client.get_array,
        ) as get_array:
        selected = repo.list(ids=['selected-citation'])
    paths = [call.args[1] for call in get_array.call_args_list]
    assert [citation.id for citation in selected] == ['selected-citation']
    assert paths
    assert all('selected-citation' in path for path in paths)
    assert not any('keep-closed' in path for path in paths)
    assert repo.list(ids=['selected-citation'], source_id='source-1') == []


# ** test_int: test_sized_text_is_not_a_fixed_column
def test_sized_text_is_not_a_fixed_column(repo):
    '''
    A multi-kilobyte excerpt is stored at its byte length, not 10,000,000.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Large enough to prove sizing, small enough not to allocate a wide row.
    excerpt = 'é' * 50_000
    note = 'n' * 1_000
    repo.save(CitationAggregate(
        id='sized-citation',
        source_id='source-1',
        locator='1-1',
        excerpt=excerpt,
        context_note=note,
    ))
    assert array_length(repo, 'sized-citation', EXCERPT_ARRAY_NAME) == len(excerpt.encode('utf-8'))
    assert array_length(repo, 'sized-citation', CONTEXT_NOTE_ARRAY_NAME) == len(note.encode('utf-8'))
    assert repo.get('sized-citation').excerpt == excerpt
    assert repo.get('sized-citation').context_note == note


# ** test_int: test_oversize_text_rejected_before_node_changes
def test_oversize_text_rejected_before_node_changes(repo):
    '''
    10,000,001 UTF-8 bytes is rejected before any citation node changes.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Persist a valid citation that must remain a short array.
    repo.save(CitationAggregate(
        id='kept-citation',
        source_id='source-1',
        locator='1-1',
        excerpt='Keep this excerpt.',
        context_note='Keep this note.',
    ))
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

    # No wide column was allocated, and the kept array is still the short text.
    with repo.client() as h5:
        assert isinstance(h5.h5file.get_node(CITATIONS_NODE_PATH), tables.Group)
        assert not h5.node_exists(f'{CITATIONS_NODE_PATH}/oversize-ascii')
    assert array_length(repo, 'kept-citation', EXCERPT_ARRAY_NAME) == len(
        'Keep this excerpt.'.encode('utf-8')
    )
    assert repo.get('oversize-ascii') is None


# ** test_int: test_migrate_table_copies_rows_and_leaves_siblings
def test_migrate_table_copies_rows_and_leaves_siblings(repo):
    '''
    Explicit migration copies every row, removes the table, and leaves siblings.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # A typed table holds a default row and a link pointer.
    rows = [LEGACY_ROW_ONE, LINK_ROW]
    write_table(repo, narrow_current_description(), rows)
    with repo.client() as h5:
        themes = h5.create_group('/lit_review/themes/keep-theme')
        h5.set_node_attr('/lit_review/themes/keep-theme', 'name', 'Keep me')
        h5.create_group('/lit_review/sources/keep-source')
        h5.set_node_attr('/lit_review/sources/keep-source', 'title', 'Sibling source')
        parent = h5.h5file.get_node('/lit_review')
        linkages = h5.h5file.create_table(parent, 'linkages', old_citation_description())
        linkages.row['id'] = b'linkage-1'
        linkages.row.append()
        linkages.flush()
        activities = h5.h5file.create_table(parent, 'activities', old_citation_description())
        activities.row['id'] = b'activity-1'
        activities.row.append()
        activities.flush()
        assert themes is not None

    # Migrate on purpose. Save is not this call.
    copied = repo.migrate_table_to_groups()
    assert copied == 2
    with repo.client() as h5:
        node = h5.h5file.get_node(CITATIONS_NODE_PATH)
        assert isinstance(node, tables.Group)
        assert not isinstance(node, tables.Table)
        assert not h5.node_exists(CITATIONS_STAGING_PATH)
        assert not h5.node_exists(CITATIONS_TABLE_BACKUP_PATH)
        assert h5.get_node_attrs('/lit_review/themes/keep-theme')['name'] == 'Keep me'
        assert h5.get_node_attrs('/lit_review/sources/keep-source')['title'] == 'Sibling source'
        assert h5.get_table('/lit_review/linkages').nrows == 1
        assert h5.get_table('/lit_review/activities').nrows == 1
        assert h5.get_node_attrs(CITATIONS_NODE_PATH)[CITATION_ORDER_ATTR] == [
            LEGACY_ROW_ONE['id'],
            LINK_ROW['id'],
        ]

    # Count, ids, locators, types, and text survived. A later save does not migrate.
    listed = repo.list()
    assert [citation.id for citation in listed] == [LEGACY_ROW_ONE['id'], LINK_ROW['id']]
    assert listed[0].locator == '4-4'
    assert listed[0].excerpt == LEGACY_ROW_ONE['excerpt']
    assert listed[0].context_note == LEGACY_ROW_ONE['context_note']
    assert listed[0].title is None
    assert listed[0].type == CITATION_TYPE_DEFAULT
    assert listed[1].type == CITATION_TYPE_LINK
    assert listed[1].excerpt == 'kabbalah:origin-citation'
    assert listed[1].title == 'Linked passage'
    with mock.patch.object(
            CitationH5Repository,
            'migrate_table_to_groups',
            autospec=True,
        ) as migrate:
        repo.save(CitationAggregate(
            id='after-migration',
            source_id='source-1',
            locator='8-8',
            excerpt='Added after migration.',
        ))
        migrate.assert_not_called()
    assert repo.get('after-migration').excerpt == 'Added after migration.'


# ** test_int: test_migrate_legacy_table_preserves_text_and_defaults
def test_migrate_legacy_table_preserves_text_and_defaults(repo):
    '''
    A title-less table migrates with default type and an empty note preserved.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Legacy rows have no title or type column.
    write_legacy_table(repo, [LEGACY_ROW_ONE, LEGACY_ROW_TWO])
    assert repo.migrate_table_to_groups() == 2
    second = repo.get(LEGACY_ROW_TWO['id'])
    assert second.excerpt == LEGACY_ROW_TWO['excerpt']
    assert second.context_note == ''
    assert second.title is None
    assert second.type == CITATION_TYPE_DEFAULT
    with repo.client() as h5:
        assert not h5.node_exists(
            f'{CITATIONS_NODE_PATH}/{LEGACY_ROW_TWO["id"]}/title'
        )
        assert h5.node_exists(
            f'{CITATIONS_NODE_PATH}/{LEGACY_ROW_TWO["id"]}/{CONTEXT_NOTE_ARRAY_NAME}'
        )
        assert isinstance(h5.h5file.get_node(CITATIONS_NODE_PATH), tables.Group)


# ** test_int: test_migration_failure_leaves_the_table
def test_migration_failure_leaves_the_table(repo, monkeypatch):
    '''
    A failed verification does not remove the citations table.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    :param monkeypatch: Pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    '''

    # Force the parity check to fail after the copy is staged.
    write_legacy_table(repo, [LEGACY_ROW_ONE, LEGACY_ROW_TWO])

    def fail_verify(self, h5, parent_path, expected):
        raise RuntimeError('forced parity failure')

    monkeypatch.setattr(CitationH5Repository, '_assert_groups_match', fail_verify)
    with pytest.raises(RuntimeError, match='forced parity failure'):
        repo.migrate_table_to_groups()

    # The table is still the citations node. Staging and the retired table are gone.
    with repo.client() as h5:
        assert isinstance(h5.h5file.get_node(CITATIONS_TABLE_PATH), tables.Table)
        assert h5.get_table(CITATIONS_TABLE_PATH).nrows == 2
        assert not h5.node_exists(CITATIONS_STAGING_PATH)
        assert not h5.node_exists(CITATIONS_TABLE_BACKUP_PATH)
    assert repo.get(LEGACY_ROW_ONE['id']).excerpt == LEGACY_ROW_ONE['excerpt']


# ** test_int: test_remove_for_transfer_drops_only_the_citation_group
def test_remove_for_transfer_drops_only_the_citation_group(repo):
    '''
    Origin-only transfer remove drops the matching citation group and leaves others.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # Persist two citations, then remove one for transfer.
    repo.save(CitationAggregate(
        id='keep-citation',
        source_id='source-1',
        locator='1-1',
        excerpt='Keep this excerpt.',
    ))
    repo.save(CitationAggregate(
        id='move-citation',
        source_id='source-1',
        locator='2-2',
        excerpt='Move this excerpt.',
    ))
    repo.remove_for_transfer('move-citation')
    assert repo.get('move-citation') is None
    assert repo.get('keep-citation').excerpt == 'Keep this excerpt.'
    assert [citation.id for citation in repo.list()] == ['keep-citation']


# ** test_int: test_unknown_citation_type_is_rejected
def test_unknown_citation_type_is_rejected():
    '''
    An unknown type value is rejected rather than persisted.
    '''

    # Constructing with an unknown type fails before any node changes.
    with pytest.raises(ValidationError):
        CitationAggregate(
            id='bad-type',
            source_id='source-1',
            locator='1-1',
            excerpt='An excerpt.',
            type='copy',
        )


# ** test_int: test_table_object_is_not_used_to_size_a_fresh_group
def test_table_object_is_not_used_to_size_a_fresh_group(repo):
    '''
    A fresh save does not create a StringCol at the validation ceiling.

    :param repo: The temporary citation repository.
    :type repo: CitationH5Repository
    '''

    # The mapper still declares the old column. The store must not materialize it.
    assert CitationTableObject._H5_TYPES['excerpt'].itemsize == MAX_EXCERPT_BYTES
    repo.save(CitationAggregate(
        id='fresh-citation',
        source_id='source-1',
        locator='1-1',
        excerpt='An excerpt.',
    ))
    with repo.client() as h5:
        assert not isinstance(h5.h5file.get_node(CITATIONS_NODE_PATH), tables.Table)

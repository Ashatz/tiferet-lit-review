"""Lit Review Cross-Project Transfer Event Tests"""

# *** imports

# ** infra
import pytest
from unittest import mock

# ** app
from tiferet import DomainEvent
from tiferet.assets import TiferetError

from app.domain.activity import (
    CITATION_COPIED_ACTION,
    PROJECT_RELATED_TYPE,
    SOURCE_COPIED_ACTION,
    SOURCE_MOVED_ACTION,
)
from app.events.source import SOURCE_NOT_FOUND_ID
from app.events.transfer import (
    CITATION_ALREADY_EXISTS_ID,
    SOURCE_ALREADY_EXISTS_ID,
    SOURCE_HAS_CITATIONS_ID,
    SOURCE_IDENTITY_CONFLICT_ID,
    TRANSFER_SAME_PROJECT_ID,
    CopyCitation,
    CopySource,
    MoveCitation,
    MoveSource,
)
from app.interfaces.activity import ActivityService
from app.interfaces.citation import CitationService
from app.interfaces.source import SourceService
from app.mappers.citation import CitationAggregate
from app.mappers.linkage import LinkageAggregate
from app.mappers.source import SourceAggregate
from app.mappers.theme import ThemeAggregate
from app.repos.abstract import AbstractH5Repository
from app.repos.activity import ActivityH5Repository
from app.repos.citation import CitationH5Repository
from app.repos.linkage import LinkageH5Repository
from app.repos.outline import OutlineH5Repository
from app.repos.paper import PaperH5Repository
from app.repos.source import SourceH5Repository
from app.repos.theme import ThemeH5Repository

# *** constants

# ** constant: source_id
SOURCE_ID = 'source-transfer-1'

# ** constant: citation_id
CITATION_ID = 'citation-transfer-1'

# ** constant: origin_project_id
ORIGIN_PROJECT_ID = 'alpha'

# ** constant: dest_project_id
DEST_PROJECT_ID = 'beta'

# ** constant: document_bytes
DOCUMENT_BYTES = b'%PDF-1.4 transferred-document'

# *** fixtures

# ** fixture: origin_source_repo
@pytest.fixture
def origin_source_repo(tmp_path) -> SourceH5Repository:
    '''
    Build an origin source repository against a temporary HDF5 file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: An origin source H5 repository.
    :rtype: SourceH5Repository
    '''

    # Return a repository pointing at an isolated origin store.
    return SourceH5Repository(h5_file=str(tmp_path / 'origin.h5'))


# ** fixture: dest_source_repo
@pytest.fixture
def dest_source_repo(tmp_path) -> SourceH5Repository:
    '''
    Build a destination source repository against a temporary HDF5 file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: A destination source H5 repository.
    :rtype: SourceH5Repository
    '''

    # Return a repository pointing at an isolated dest store.
    return SourceH5Repository(h5_file=str(tmp_path / 'dest.h5'))


# ** fixture: origin_citation_repo
@pytest.fixture
def origin_citation_repo(tmp_path) -> CitationH5Repository:
    '''
    Build an origin citation repository sharing the origin HDF5 file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: An origin citation H5 repository.
    :rtype: CitationH5Repository
    '''

    # Share the origin store path with the origin source repository.
    return CitationH5Repository(h5_file=str(tmp_path / 'origin.h5'))


# ** fixture: dest_citation_repo
@pytest.fixture
def dest_citation_repo(tmp_path) -> CitationH5Repository:
    '''
    Build a destination citation repository sharing the dest HDF5 file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: A destination citation H5 repository.
    :rtype: CitationH5Repository
    '''

    # Share the dest store path with the dest source repository.
    return CitationH5Repository(h5_file=str(tmp_path / 'dest.h5'))


# ** fixture: origin_activity_repo
@pytest.fixture
def origin_activity_repo(tmp_path) -> ActivityH5Repository:
    '''
    Build an origin activity repository sharing the origin HDF5 file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: An origin activity H5 repository.
    :rtype: ActivityH5Repository
    '''

    # Share the origin store path with the other origin repositories.
    return ActivityH5Repository(h5_file=str(tmp_path / 'origin.h5'))


# ** fixture: dest_activity_repo
@pytest.fixture
def dest_activity_repo(tmp_path) -> ActivityH5Repository:
    '''
    Build a destination activity repository sharing the dest HDF5 file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: A destination activity H5 repository.
    :rtype: ActivityH5Repository
    '''

    # Share the dest store path with the other dest repositories.
    return ActivityH5Repository(h5_file=str(tmp_path / 'dest.h5'))


# ** fixture: source
@pytest.fixture
def source() -> SourceAggregate:
    '''
    Build a bibliographic source with no attached document.

    :return: A source aggregate under SOURCE_ID.
    :rtype: SourceAggregate
    '''

    # Return a PDF source whose identity fields are stable across copies.
    result = SourceAggregate(
        id=SOURCE_ID,
        medium='pdf',
        year=2020,
        title='MLIR: A Compiler Infrastructure',
        container_title='CGO',
        publisher='ACM',
    )
    result.add_author('Lattner, C.')
    return result


# ** fixture: citation
@pytest.fixture
def citation() -> CitationAggregate:
    '''
    Build a citation belonging to SOURCE_ID.

    :return: A citation aggregate under CITATION_ID.
    :rtype: CitationAggregate
    '''

    # Return a citation whose row fields must round-trip under the same id.
    return CitationAggregate(
        id=CITATION_ID,
        source_id=SOURCE_ID,
        locator='4-4',
        excerpt='Operations are the unit.',
        context_note='From the introduction.',
        title='Operations as the unit',
    )

# *** functions

# ** function: copy_source
def copy_source(
        origin_source_repo,
        dest_source_repo,
        dest_activity_repo,
        source_id=SOURCE_ID,
    ):
    '''
    Execute CopySource against the given origin and dest repositories.

    :param origin_source_repo: The origin source repository.
    :param dest_source_repo: The destination source repository.
    :param dest_activity_repo: The destination activity repository.
    :param source_id: The source identifier to copy.
    :return: The dest source aggregate.
    '''

    # Invoke the copy event with real origin and dest stores.
    return DomainEvent.handle(
        CopySource,
        dependencies={
            'source_service': origin_source_repo,
            'activity_service': mock.Mock(spec=ActivityService),
        },
        id=source_id,
        dest_project_id=DEST_PROJECT_ID,
        project_id=ORIGIN_PROJECT_ID,
        dest_source_service=dest_source_repo,
        dest_activity_service=dest_activity_repo,
    )


# ** function: move_source
def move_source(
        origin_source_repo,
        origin_citation_repo,
        origin_activity_repo,
        dest_source_repo,
        dest_activity_repo,
        source_id=SOURCE_ID,
    ):
    '''
    Execute MoveSource against the given origin and dest repositories.

    :return: The dest source aggregate.
    '''

    # Invoke the move event with real origin and dest stores.
    return DomainEvent.handle(
        MoveSource,
        dependencies={
            'source_service': origin_source_repo,
            'citation_service': origin_citation_repo,
            'activity_service': origin_activity_repo,
        },
        id=source_id,
        dest_project_id=DEST_PROJECT_ID,
        project_id=ORIGIN_PROJECT_ID,
        dest_source_service=dest_source_repo,
        dest_activity_service=dest_activity_repo,
    )


# ** function: copy_citation
def copy_citation(
        origin_citation_repo,
        origin_source_repo,
        dest_citation_repo,
        dest_source_repo,
        dest_activity_repo,
        citation_id=CITATION_ID,
    ):
    '''
    Execute CopyCitation against the given origin and dest repositories.

    :return: The dest citation aggregate.
    '''

    # Invoke the copy event with real origin and dest stores.
    return DomainEvent.handle(
        CopyCitation,
        dependencies={
            'citation_service': origin_citation_repo,
            'source_service': origin_source_repo,
            'activity_service': mock.Mock(spec=ActivityService),
        },
        id=citation_id,
        dest_project_id=DEST_PROJECT_ID,
        project_id=ORIGIN_PROJECT_ID,
        dest_citation_service=dest_citation_repo,
        dest_source_service=dest_source_repo,
        dest_activity_service=dest_activity_repo,
    )


# ** function: move_citation
def move_citation(
        origin_citation_repo,
        origin_source_repo,
        origin_activity_repo,
        dest_citation_repo,
        dest_source_repo,
        dest_activity_repo,
        citation_id=CITATION_ID,
    ):
    '''
    Execute MoveCitation against the given origin and dest repositories.

    :return: The dest citation aggregate.
    '''

    # Invoke the move event with real origin and dest stores.
    return DomainEvent.handle(
        MoveCitation,
        dependencies={
            'citation_service': origin_citation_repo,
            'source_service': origin_source_repo,
            'activity_service': origin_activity_repo,
        },
        id=citation_id,
        dest_project_id=DEST_PROJECT_ID,
        project_id=ORIGIN_PROJECT_ID,
        dest_citation_service=dest_citation_repo,
        dest_source_service=dest_source_repo,
        dest_activity_service=dest_activity_repo,
    )

# *** tests

# ** test: test_copy_source_without_document_preserves_id_and_origin
def test_copy_source_without_document_preserves_id_and_origin(
        origin_source_repo,
        dest_source_repo,
        dest_activity_repo,
        source,
    ):
    '''
    Copying a source with no document writes dest attrs under the same id (AC #1).
    '''

    # Persist the origin source without a document array.
    origin_source_repo.save(source)

    # Copy the source into dest.
    result = copy_source(origin_source_repo, dest_source_repo, dest_activity_repo)

    # Dest has the same id and bibliographic attrs, and no document array.
    dest = dest_source_repo.get(SOURCE_ID)
    assert result.id == SOURCE_ID
    assert dest.id == SOURCE_ID
    assert dest.title == source.title
    assert dest.authors[0].display_name == 'Lattner, C.'
    assert dest.container_title == 'CGO'
    assert dest.publisher == 'ACM'
    assert dest.document_name is None
    assert dest_source_repo.has_document(SOURCE_ID) is False

    # Origin is unchanged.
    origin = origin_source_repo.get(SOURCE_ID)
    assert origin is not None
    assert origin.title == source.title
    assert origin_source_repo.has_document(SOURCE_ID) is False


# ** test: test_copy_source_with_document_matches_origin_bytes
def test_copy_source_with_document_matches_origin_bytes(
        origin_source_repo,
        dest_source_repo,
        dest_activity_repo,
        source,
    ):
    '''
    Copying a source with a document writes dest bytes and document_name (AC #2).
    '''

    # Attach a named document on origin, then copy.
    source.attach_document('lattner_2020_mlir.pdf')
    origin_source_repo.save(source)
    origin_source_repo.save_document(SOURCE_ID, DOCUMENT_BYTES)
    copy_source(origin_source_repo, dest_source_repo, dest_activity_repo)

    # Dest attrs, document_name, and bytes match origin.
    dest = dest_source_repo.get(SOURCE_ID)
    assert dest.document_name == 'lattner_2020_mlir.pdf'
    assert dest_source_repo.has_document(SOURCE_ID) is True
    assert dest_source_repo.get_document(SOURCE_ID) == DOCUMENT_BYTES
    assert origin_source_repo.get_document(SOURCE_ID) == DOCUMENT_BYTES


# ** test: test_copy_citation_auto_copies_missing_parent_source
def test_copy_citation_auto_copies_missing_parent_source(
        origin_source_repo,
        origin_citation_repo,
        dest_source_repo,
        dest_citation_repo,
        dest_activity_repo,
        source,
        citation,
    ):
    '''
    Citation copy auto-copies a missing parent source and document (AC #3).
    '''

    # Persist origin source, document, and citation.
    source.attach_document('lattner_2020_mlir.pdf')
    origin_source_repo.save(source)
    origin_source_repo.save_document(SOURCE_ID, DOCUMENT_BYTES)
    origin_citation_repo.save(citation)

    # Copy the citation into an empty dest store.
    result = copy_citation(
        origin_citation_repo,
        origin_source_repo,
        dest_citation_repo,
        dest_source_repo,
        dest_activity_repo,
    )

    # Dest has the citation and parent source under the same ids.
    assert result.id == CITATION_ID
    dest_citation = dest_citation_repo.get(CITATION_ID)
    dest_source = dest_source_repo.get(SOURCE_ID)
    assert dest_citation.source_id == SOURCE_ID
    assert dest_citation.excerpt == citation.excerpt
    assert dest_citation.title == citation.title
    assert dest_source.title == source.title
    assert dest_source.document_name == 'lattner_2020_mlir.pdf'
    assert dest_source_repo.get_document(SOURCE_ID) == DOCUMENT_BYTES


# ** test: test_dest_id_collision_fails_without_overwrite
def test_dest_id_collision_fails_without_overwrite(
        origin_source_repo,
        origin_citation_repo,
        dest_source_repo,
        dest_citation_repo,
        dest_activity_repo,
        source,
        citation,
    ):
    '''
    Dest occupancy fails copy, mints no new id, and overwrites nothing (AC #4).
    '''

    # Seed origin and a colliding dest source with different identity.
    origin_source_repo.save(source)
    origin_citation_repo.save(citation)
    colliding = SourceAggregate(
        id=SOURCE_ID,
        medium='book',
        year=1999,
        title='A Different Work',
    )
    colliding.add_author('Other, A.')
    dest_source_repo.save(colliding)

    # Source copy fails on dest occupancy.
    with pytest.raises(TiferetError) as source_exc:
        copy_source(origin_source_repo, dest_source_repo, dest_activity_repo)
    assert source_exc.value.error_code == SOURCE_ALREADY_EXISTS_ID
    assert dest_source_repo.get(SOURCE_ID).title == 'A Different Work'
    assert origin_source_repo.get(SOURCE_ID).title == source.title

    # Citation copy fails when dest already holds a different parent source.
    with pytest.raises(TiferetError) as identity_exc:
        copy_citation(
            origin_citation_repo,
            origin_source_repo,
            dest_citation_repo,
            dest_source_repo,
            dest_activity_repo,
        )
    assert identity_exc.value.error_code == SOURCE_IDENTITY_CONFLICT_ID
    assert dest_citation_repo.get(CITATION_ID) is None
    assert dest_source_repo.get(SOURCE_ID).title == 'A Different Work'

    # Citation copy also fails on dest citation occupancy.
    dest_citation_repo.save(CitationAggregate(
        id=CITATION_ID,
        source_id=SOURCE_ID,
        locator='1-1',
        excerpt='Already here.',
    ))
    matching_parent = SourceAggregate(
        id=SOURCE_ID,
        medium='pdf',
        year=2020,
        title='MLIR: A Compiler Infrastructure',
        container_title='CGO',
        publisher='ACM',
    )
    matching_parent.add_author('Lattner, C.')
    dest_source_repo.save(matching_parent)
    with pytest.raises(TiferetError) as citation_exc:
        copy_citation(
            origin_citation_repo,
            origin_source_repo,
            dest_citation_repo,
            dest_source_repo,
            dest_activity_repo,
        )
    assert citation_exc.value.error_code == CITATION_ALREADY_EXISTS_ID
    assert dest_citation_repo.get(CITATION_ID).excerpt == 'Already here.'


# ** test: test_copy_citation_reuses_matching_parent_without_rewrite
def test_copy_citation_reuses_matching_parent_without_rewrite(
        origin_source_repo,
        origin_citation_repo,
        dest_source_repo,
        dest_citation_repo,
        dest_activity_repo,
        source,
        citation,
    ):
    '''
    A matching dest parent source is reused and not rewritten.
    '''

    # Dest already has the parent with matching identity and its own document.
    origin_source_repo.save(source)
    origin_citation_repo.save(citation)
    dest_parent = SourceAggregate(
        id=SOURCE_ID,
        medium='pdf',
        year=2020,
        title='MLIR: A Compiler Infrastructure',
        container_title='CGO',
        publisher='ACM',
        document_name='dest-original.pdf',
        overview_note='Dest-only note.',
    )
    dest_parent.add_author('Lattner, C.')
    dest_source_repo.save(dest_parent)
    dest_source_repo.save_document(SOURCE_ID, b'dest-only-bytes')

    # Copy the citation; dest parent attrs and document stay put.
    copy_citation(
        origin_citation_repo,
        origin_source_repo,
        dest_citation_repo,
        dest_source_repo,
        dest_activity_repo,
    )
    reused = dest_source_repo.get(SOURCE_ID)
    assert reused.overview_note == 'Dest-only note.'
    assert reused.document_name == 'dest-original.pdf'
    assert dest_source_repo.get_document(SOURCE_ID) == b'dest-only-bytes'
    assert dest_citation_repo.get(CITATION_ID).id == CITATION_ID


# ** test: test_move_source_and_citation_remove_origin_only
def test_move_source_and_citation_remove_origin_only(
        origin_source_repo,
        origin_citation_repo,
        origin_activity_repo,
        dest_source_repo,
        dest_citation_repo,
        dest_activity_repo,
        source,
        citation,
    ):
    '''
    Move removes the transferred artifact from origin only (AC #5).
    '''

    # Move a document-bearing source after citations are gone.
    source.attach_document('lattner_2020_mlir.pdf')
    origin_source_repo.save(source)
    origin_source_repo.save_document(SOURCE_ID, DOCUMENT_BYTES)
    origin_citation_repo.save(citation)

    # Source move is refused while origin still has citations.
    with pytest.raises(TiferetError) as has_citations:
        move_source(
            origin_source_repo,
            origin_citation_repo,
            origin_activity_repo,
            dest_source_repo,
            dest_activity_repo,
        )
    assert has_citations.value.error_code == SOURCE_HAS_CITATIONS_ID
    assert origin_source_repo.get(SOURCE_ID) is not None

    # Citation move removes only the origin row; origin parent source stays.
    move_citation(
        origin_citation_repo,
        origin_source_repo,
        origin_activity_repo,
        dest_citation_repo,
        dest_source_repo,
        dest_activity_repo,
    )
    assert origin_citation_repo.get(CITATION_ID) is None
    assert origin_source_repo.get(SOURCE_ID) is not None
    assert dest_citation_repo.get(CITATION_ID).excerpt == citation.excerpt
    assert dest_source_repo.get(SOURCE_ID).title == source.title
    assert dest_source_repo.get_document(SOURCE_ID) == DOCUMENT_BYTES

    # Source move then removes the origin group, including its document.
    move_source(
        origin_source_repo,
        origin_citation_repo,
        origin_activity_repo,
        dest_source_repo,
        dest_activity_repo,
    )
    assert origin_source_repo.get(SOURCE_ID) is None
    assert origin_source_repo.has_document(SOURCE_ID) is False
    dest = dest_source_repo.get(SOURCE_ID)
    assert dest.document_name == 'lattner_2020_mlir.pdf'
    assert dest_source_repo.get_document(SOURCE_ID) == DOCUMENT_BYTES


# ** test: test_crash_after_dest_write_then_retried_move
def test_crash_after_dest_write_then_retried_move(
        origin_source_repo,
        origin_citation_repo,
        origin_activity_repo,
        dest_source_repo,
        dest_activity_repo,
        source,
    ):
    '''
    A crash after dest write leaves origin; a matching retry removes it (AC #6).
    '''

    # Persist the origin source, then crash after dest write.
    origin_source_repo.save(source)

    def crash(artifact_id):
        raise RuntimeError('simulated crash')

    origin_source_repo.remove_for_transfer = crash
    with pytest.raises(RuntimeError):
        move_source(
            origin_source_repo,
            origin_citation_repo,
            origin_activity_repo,
            dest_source_repo,
            dest_activity_repo,
        )

    # Dest is complete and origin is still present.
    assert dest_source_repo.get(SOURCE_ID) is not None
    assert origin_source_repo.get(SOURCE_ID) is not None

    # Restore origin remove and retry the matching move.
    del origin_source_repo.remove_for_transfer
    move_source(
        origin_source_repo,
        origin_citation_repo,
        origin_activity_repo,
        dest_source_repo,
        dest_activity_repo,
    )
    assert origin_source_repo.get(SOURCE_ID) is None
    assert dest_source_repo.get(SOURCE_ID).title == source.title


# ** test: test_dest_citation_is_unlinked_and_history_is_not_copied
def test_dest_citation_is_unlinked_and_history_is_not_copied(
        origin_source_repo,
        origin_citation_repo,
        dest_source_repo,
        dest_citation_repo,
        dest_activity_repo,
        source,
        citation,
        tmp_path,
    ):
    '''
    Dest citations are unlinked and non-source/citation rows are not copied (AC #7).
    '''

    # Persist origin source, citation, theme, linkage, and sibling aggregates.
    origin_h5 = str(tmp_path / 'origin.h5')
    dest_h5 = str(tmp_path / 'dest.h5')
    origin_source_repo.save(source)
    origin_citation_repo.save(citation)
    theme = ThemeAggregate(id='theme-1', name='IR abstractions')
    ThemeH5Repository(h5_file=origin_h5).save(theme)
    LinkageH5Repository(h5_file=origin_h5).save(
        LinkageAggregate(citation_id=CITATION_ID, theme_id='theme-1'),
    )
    from app.mappers.abstract import AbstractAggregate
    from app.mappers.outline import OutlineAggregate
    from app.mappers.paper import PaperAggregate
    AbstractH5Repository(h5_file=origin_h5).save(
        AbstractAggregate(id='abstract-1', name='Argument brief'),
    )
    OutlineH5Repository(h5_file=origin_h5).save(
        OutlineAggregate(id='outline-1', title='Arrangement'),
    )
    PaperH5Repository(h5_file=origin_h5).save(
        PaperAggregate(id='paper-1', title='Manuscript', outline_id='outline-1'),
    )

    # Copy the citation; dest must not inherit those other aggregates.
    copy_citation(
        origin_citation_repo,
        origin_source_repo,
        dest_citation_repo,
        dest_source_repo,
        dest_activity_repo,
    )
    assert dest_citation_repo.get(CITATION_ID) is not None
    assert ThemeH5Repository(h5_file=dest_h5).list() == []
    assert LinkageH5Repository(h5_file=dest_h5).list() == []
    assert AbstractH5Repository(h5_file=dest_h5).list() == []
    assert OutlineH5Repository(h5_file=dest_h5).list() == []
    assert PaperH5Repository(h5_file=dest_h5).list() == []
    dest_actions = [entry.action for entry in dest_activity_repo.list()]
    assert SOURCE_COPIED_ACTION in dest_actions
    assert CITATION_COPIED_ACTION in dest_actions
    assert dest_actions.count(SOURCE_COPIED_ACTION) == 1


# ** test: test_activity_failure_leaves_transfer_intact
def test_activity_failure_leaves_transfer_intact(
        origin_source_repo,
        origin_citation_repo,
        dest_source_repo,
        dest_activity_repo,
        source,
    ):
    '''
    A failed activity append leaves a successful copy or move intact (AC #8).
    '''

    # Persist origin, then fail dest activity on copy.
    origin_source_repo.save(source)
    failing_activity = mock.Mock(spec=ActivityService)
    failing_activity.record.side_effect = RuntimeError('storage unavailable')
    copy_source(origin_source_repo, dest_source_repo, failing_activity)
    assert dest_source_repo.get(SOURCE_ID) is not None
    assert origin_source_repo.get(SOURCE_ID) is not None

    # Fail origin activity on move; dest and origin-remove still succeed.
    failing_origin_activity = mock.Mock(spec=ActivityService)
    failing_origin_activity.record.side_effect = RuntimeError('storage unavailable')
    DomainEvent.handle(
        MoveSource,
        dependencies={
            'source_service': origin_source_repo,
            'citation_service': origin_citation_repo,
            'activity_service': failing_origin_activity,
        },
        id=SOURCE_ID,
        dest_project_id=DEST_PROJECT_ID,
        project_id=ORIGIN_PROJECT_ID,
        dest_source_service=dest_source_repo,
        dest_activity_service=dest_activity_repo,
    )
    assert origin_source_repo.get(SOURCE_ID) is None
    assert dest_source_repo.get(SOURCE_ID) is not None


# ** test: test_same_project_and_missing_origin_fail
def test_same_project_and_missing_origin_fail(
        origin_source_repo,
        dest_source_repo,
        dest_activity_repo,
        origin_citation_repo,
        dest_citation_repo,
    ):
    '''
    Origin equal to dest fails, and a missing origin artifact is not-found.
    '''

    # Same-project copy fails before any dest write.
    with pytest.raises(TiferetError) as same_project:
        DomainEvent.handle(
            CopySource,
            dependencies={
                'source_service': origin_source_repo,
                'activity_service': mock.Mock(spec=ActivityService),
            },
            id=SOURCE_ID,
            dest_project_id=ORIGIN_PROJECT_ID,
            project_id=ORIGIN_PROJECT_ID,
            dest_source_service=dest_source_repo,
            dest_activity_service=dest_activity_repo,
        )
    assert same_project.value.error_code == TRANSFER_SAME_PROJECT_ID

    # Missing origin source is not-found.
    with pytest.raises(TiferetError) as missing_source:
        copy_source(origin_source_repo, dest_source_repo, dest_activity_repo)
    assert missing_source.value.error_code == SOURCE_NOT_FOUND_ID

    # Missing origin citation is not-found.
    with pytest.raises(TiferetError) as missing_citation:
        copy_citation(
            origin_citation_repo,
            origin_source_repo,
            dest_citation_repo,
            dest_source_repo,
            dest_activity_repo,
        )
    assert missing_citation.value.error_code == 'CITATION_NOT_FOUND'


# ** test: test_retried_copy_still_fails_on_dest_occupancy
def test_retried_copy_still_fails_on_dest_occupancy(
        origin_source_repo,
        dest_source_repo,
        dest_activity_repo,
        source,
    ):
    '''
    A retried copy still fails on dest occupancy even when content matches.
    '''

    # Copy once, then copy again against the occupied dest.
    origin_source_repo.save(source)
    copy_source(origin_source_repo, dest_source_repo, dest_activity_repo)
    with pytest.raises(TiferetError) as occupied:
        copy_source(origin_source_repo, dest_source_repo, dest_activity_repo)
    assert occupied.value.error_code == SOURCE_ALREADY_EXISTS_ID
    assert origin_source_repo.get(SOURCE_ID) is not None


# ** test: test_copy_source_does_not_copy_citations
def test_copy_source_does_not_copy_citations(
        origin_source_repo,
        origin_citation_repo,
        dest_source_repo,
        dest_citation_repo,
        dest_activity_repo,
        source,
        citation,
    ):
    '''
    Source copy does not copy that source's citations.
    '''

    # Origin has a citation; dest must not receive it on source copy.
    origin_source_repo.save(source)
    origin_citation_repo.save(citation)
    copy_source(origin_source_repo, dest_source_repo, dest_activity_repo)
    assert dest_source_repo.get(SOURCE_ID) is not None
    assert dest_citation_repo.list(source_id=SOURCE_ID) == []


# ** test: test_transfer_activity_tokens_and_related_project
def test_transfer_activity_tokens_and_related_project(
        origin_source_repo,
        origin_citation_repo,
        origin_activity_repo,
        dest_source_repo,
        dest_activity_repo,
        source,
    ):
    '''
    Dest records copied and origin records moved with related_type project.
    '''

    # Move a source and inspect activity on both stores.
    origin_source_repo.save(source)
    move_source(
        origin_source_repo,
        origin_citation_repo,
        origin_activity_repo,
        dest_source_repo,
        dest_activity_repo,
    )
    dest_entry = dest_activity_repo.list(action=SOURCE_COPIED_ACTION)[0]
    origin_entry = origin_activity_repo.list(action=SOURCE_MOVED_ACTION)[0]
    assert dest_entry.subject_id == SOURCE_ID
    assert dest_entry.related_type == PROJECT_RELATED_TYPE
    assert dest_entry.related_id == ORIGIN_PROJECT_ID
    assert origin_entry.related_type == PROJECT_RELATED_TYPE
    assert origin_entry.related_id == DEST_PROJECT_ID


# ** test: test_interfaces_do_not_expose_delete
def test_interfaces_do_not_expose_delete():
    '''
    Origin remove is not a SourceService or CitationService API.
    '''

    # The public service contracts still have no delete/remove methods.
    assert not hasattr(SourceService, 'delete')
    assert not hasattr(CitationService, 'delete')
    assert 'remove_for_transfer' not in getattr(
        SourceService,
        '__abstractmethods__',
        set(),
    )
    assert 'remove_for_transfer' not in getattr(
        CitationService,
        '__abstractmethods__',
        set(),
    )

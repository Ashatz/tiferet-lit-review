"""Lit Review Source H5 Repository Integration Tests"""

# *** imports

# ** infra
import pytest

# ** app
from app.mappers.source import SourceAggregate
from app.repos.source import SOURCE_DOCUMENT_NODE_NAME, SourceH5Repository

# *** constants

# ** constant: source_id
SOURCE_ID = 'source-document-test'

# ** constant: first_bytes
FIRST_BYTES = b'first-pdf-bytes'

# ** constant: second_bytes
SECOND_BYTES = b'second-pdf-bytes-are-longer'

# *** fixtures

# ** fixture: repo
@pytest.fixture
def repo(tmp_path) -> SourceH5Repository:
    '''
    Build a source repository against a temporary HDF5 file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: A source H5 repository.
    :rtype: SourceH5Repository
    '''

    # Return a repository pointing at an isolated temp file.
    return SourceH5Repository(h5_file=str(tmp_path / 'lit_review.h5'))


# ** fixture: source
@pytest.fixture
def source() -> SourceAggregate:
    '''
    Build a source aggregate for document array tests.

    :return: A source with one author and an API name.
    :rtype: SourceAggregate
    '''

    # Return a source whose metadata can be saved independently of the array.
    source = SourceAggregate(
        id=SOURCE_ID,
        medium='pdf',
        year=2020,
        title='MLIR: A Compiler Infrastructure',
        document_name='lattner_2020_mlir.pdf',
    )
    source.add_author('Lattner, C.')
    return source


# *** tests

# ** test_int: test_save_document_does_not_load_on_get_or_list
def test_save_document_does_not_load_on_get_or_list(repo, source):
    '''
    Ordinary get and list return metadata without requiring the array.

    :param repo: The temporary source repository.
    :type repo: SourceH5Repository
    :param source: The source fixture.
    :type source: SourceAggregate
    '''

    # Persist metadata and the document array separately.
    repo.save(source)
    repo.save_document(SOURCE_ID, FIRST_BYTES)

    # Metadata reads still see the API name and never need the array body.
    loaded = repo.get(SOURCE_ID)
    listed = repo.list()
    assert loaded is not None
    assert loaded.document_name == 'lattner_2020_mlir.pdf'
    assert listed[0].id == SOURCE_ID
    assert repo.has_document(SOURCE_ID) is True
    assert repo.get_document(SOURCE_ID) == FIRST_BYTES


# ** test_int: test_save_document_replaces_single_array_node
def test_save_document_replaces_single_array_node(repo, source):
    '''
    Re-attach replaces the previous array and leaves one document node.

    :param repo: The temporary source repository.
    :type repo: SourceH5Repository
    :param source: The source fixture.
    :type source: SourceAggregate
    '''

    # Write, then replace, the document array.
    repo.save(source)
    repo.save_document(SOURCE_ID, FIRST_BYTES)
    repo.save_document(SOURCE_ID, SECOND_BYTES)

    # Only the replacement bytes remain under the single document node.
    assert repo.get_document(SOURCE_ID) == SECOND_BYTES
    with repo.client() as h5:
        group = h5.get_group(f'/lit_review/sources/{SOURCE_ID}')
        child_names = list(group._v_children)
    assert child_names.count(SOURCE_DOCUMENT_NODE_NAME) == 1


# ** test_int: test_get_document_missing_returns_none
def test_get_document_missing_returns_none(repo, source):
    '''
    A source without an array reports no document.

    :param repo: The temporary source repository.
    :type repo: SourceH5Repository
    :param source: The source fixture.
    :type source: SourceAggregate
    '''

    # Persist metadata only.
    repo.save(source)

    # Missing-array reads stay quiet so the event can raise the domain error.
    assert repo.has_document(SOURCE_ID) is False
    assert repo.get_document(SOURCE_ID) is None

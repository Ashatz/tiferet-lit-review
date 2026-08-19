"""Lit Review Paper H5 Repository Integration Tests"""

# *** imports

# ** infra
import pytest

# ** app
from app.mappers.paper import PaperAggregate
from app.repos.paper import PAPERS_GROUP_PATH, PaperH5Repository

# *** constants

# ** constant: theme_id_a
THEME_ID_A = 'universal-ir-abstractions'

# ** constant: theme_id_b
THEME_ID_B = 'progressive-lowering'

# ** constant: citation_id
CITATION_ID = 'cite-001'

# *** fixtures

# ** fixture: repo
@pytest.fixture
def repo(tmp_path) -> PaperH5Repository:
    '''
    Build a paper repository against a temporary HDF5 file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: A paper H5 repository.
    :rtype: PaperH5Repository
    '''

    # Return a repository pointing at an isolated temp file.
    return PaperH5Repository(h5_file=str(tmp_path / 'lit_review.h5'))

# ** fixture: paper
@pytest.fixture
def paper() -> PaperAggregate:
    '''
    Build a paper aggregate with one named section, a brief, and a citation.

    :return: A paper that can be saved and rehydrated.
    :rtype: PaperAggregate
    '''

    # Return a paper whose children can be saved and rehydrated.
    opened = PaperAggregate(
        title='MLIR argument',
        outline_id='outline-001',
    )
    opened.add_section(
        'Introduction',
        theme_ids=[THEME_ID_A, THEME_ID_B],
        id='intro-section',
        content='Drafted introduction.',
        context='Why this section exists.',
    )
    opened.set_abstract(
        'A standing argument brief.',
        source_abstract_id='abs-001',
    )
    opened.add_citation(CITATION_ID, section_id='intro-section')
    return opened

# *** tests

# ** test_int: test_save_and_get_restores_children
def test_save_and_get_restores_children(repo, paper):
    '''
    Saving a paper persists owned children and get restores them.

    :param repo: The temporary paper repository.
    :type repo: PaperH5Repository
    :param paper: The paper fixture.
    :type paper: PaperAggregate
    '''

    # Persist the paper and read it back.
    repo.save(paper)
    loaded = repo.get(paper.id)

    # The rehydrated paper owns the section, brief, and citation.
    assert loaded is not None
    assert loaded.title == 'MLIR argument'
    assert loaded.outline_id == 'outline-001'
    assert loaded.section_count == 1
    assert loaded.sections[0].id == 'intro-section'
    assert loaded.sections[0].title == 'Introduction'
    assert loaded.sections[0].content == 'Drafted introduction.'
    assert loaded.sections[0].context == 'Why this section exists.'
    assert [theme.theme_id for theme in loaded.sections[0].themes] == [
        THEME_ID_A,
        THEME_ID_B,
    ]
    assert loaded.abstract.body == 'A standing argument brief.'
    assert loaded.abstract.source_abstract_id == 'abs-001'
    assert loaded.citations[0].citation_id == CITATION_ID
    assert loaded.citations[0].section_id == 'intro-section'

# ** test_int: test_list_filters_by_outline_id
def test_list_filters_by_outline_id(repo, paper):
    '''
    Listing by outline_id returns only papers forked from that outline.

    :param repo: The temporary paper repository.
    :type repo: PaperH5Repository
    :param paper: The paper fixture.
    :type paper: PaperAggregate
    '''

    # Persist one paper and list with a matching and a missing origin.
    repo.save(paper)
    matching = repo.list(outline_id='outline-001')
    missing = repo.list(outline_id='not-an-outline')

    # Only the matching filter returns the saved paper.
    assert [item.id for item in matching] == [paper.id]
    assert missing == []

# ** test_int: test_exists_and_missing_get
def test_exists_and_missing_get(repo, paper):
    '''
    exists follows the paper group node; missing get returns None.

    :param repo: The temporary paper repository.
    :type repo: PaperH5Repository
    :param paper: The paper fixture.
    :type paper: PaperAggregate
    '''

    # A missing paper is neither existent nor loadable.
    assert repo.exists(paper.id) is False
    assert repo.get(paper.id) is None

    # After save, the group node is present under the papers path.
    repo.save(paper)
    assert repo.exists(paper.id) is True
    with repo.client() as h5:
        assert h5.node_exists(f'{PAPERS_GROUP_PATH}/{paper.id}') is True

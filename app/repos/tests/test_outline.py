"""Lit Review Outline H5 Repository Integration Tests"""

# *** imports

# ** infra
import pytest

# ** app
from app.mappers.outline import OutlineAggregate
from app.repos.outline import OUTLINES_GROUP_PATH, OutlineH5Repository

# *** constants

# ** constant: theme_id_a
THEME_ID_A = 'universal-ir-abstractions'

# ** constant: theme_id_b
THEME_ID_B = 'progressive-lowering'

# *** fixtures

# ** fixture: repo
@pytest.fixture
def repo(tmp_path) -> OutlineH5Repository:
    '''
    Build an outline repository against a temporary HDF5 file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: An outline H5 repository.
    :rtype: OutlineH5Repository
    '''

    # Return a repository pointing at an isolated temp file.
    return OutlineH5Repository(h5_file=str(tmp_path / 'lit_review.h5'))


# ** fixture: outline
@pytest.fixture
def outline() -> OutlineAggregate:
    '''
    Build an outline aggregate with one named slot and two themes.

    :return: An outline arranged as a named grouping of two themes.
    :rtype: OutlineAggregate
    '''

    # Return an outline whose slots can be saved and rehydrated.
    assembled = OutlineAggregate(title='MLIR argument')
    assembled.add_slot(
        'Introduction',
        theme_ids=[THEME_ID_A, THEME_ID_B],
        id='intro-slot',
    )
    return assembled


# *** tests

# ** test_int: test_save_and_get_restores_slots_in_order
def test_save_and_get_restores_slots_in_order(repo, outline):
    '''
    Saving an outline persists owned slots and get restores them in order.

    :param repo: The temporary outline repository.
    :type repo: OutlineH5Repository
    :param outline: The outline fixture.
    :type outline: OutlineAggregate
    '''

    # Persist the outline and read it back.
    repo.save(outline)
    loaded = repo.get(outline.id)

    # The rehydrated outline owns the named slot and both theme joins.
    assert loaded is not None
    assert loaded.title == 'MLIR argument'
    assert loaded.slot_count == 1
    assert loaded.slots[0].id == 'intro-slot'
    assert loaded.slots[0].title == 'Introduction'
    assert [theme.theme_id for theme in loaded.slots[0].themes] == [
        THEME_ID_A,
        THEME_ID_B,
    ]
    assert loaded.slots[0].position == 0


# ** test_int: test_list_filters_by_theme_id
def test_list_filters_by_theme_id(repo, outline):
    '''
    Listing by theme_id returns only outlines that own that slot.

    :param repo: The temporary outline repository.
    :type repo: OutlineH5Repository
    :param outline: The outline fixture.
    :type outline: OutlineAggregate
    '''

    # Persist one outline and list with a matching and a missing theme.
    repo.save(outline)
    matching = repo.list(theme_id=THEME_ID_A)
    missing = repo.list(theme_id='not-a-theme')

    # Only the matching filter returns the saved outline.
    assert [item.id for item in matching] == [outline.id]
    assert missing == []


# ** test_int: test_exists_and_missing_get
def test_exists_and_missing_get(repo, outline):
    '''
    exists follows the outline group node; missing get returns None.

    :param repo: The temporary outline repository.
    :type repo: OutlineH5Repository
    :param outline: The outline fixture.
    :type outline: OutlineAggregate
    '''

    # A missing outline is neither existent nor loadable.
    assert repo.exists(outline.id) is False
    assert repo.get(outline.id) is None

    # After save, the group node is present under the outlines path.
    repo.save(outline)
    assert repo.exists(outline.id) is True
    with repo.client() as h5:
        assert h5.node_exists(f'{OUTLINES_GROUP_PATH}/{outline.id}') is True

"""Lit Review Outline Event Tests"""

# *** imports

# ** infra
import pytest
from unittest import mock

# ** app
from tiferet import DomainEvent
from tiferet.assets import TiferetError

from app.events.outline import (
    OUTLINE_NOT_FOUND_ID,
    AssembleOutline,
    GetOutline,
    ShowOutline,
)
from app.events.theme import THEME_NOT_FOUND_ID
from app.interfaces.citation import CitationService
from app.interfaces.citation_style import CitationStyleRuleService
from app.interfaces.linkage import LinkageService
from app.interfaces.outline import OutlineService
from app.interfaces.source import SourceService
from app.interfaces.theme import ThemeService
from app.mappers.outline import OutlineAggregate, OutlineResponse
from app.mappers.theme import ThemeAggregate

# *** constants

# ** constant: outline_id
OUTLINE_ID = 'b2c3d4e5-f6a7-8901-bcde-f12345678901'

# ** constant: theme_id_a
THEME_ID_A = 'universal-ir-abstractions'

# ** constant: theme_id_b
THEME_ID_B = 'progressive-lowering'

# ** constant: missing_theme_id
MISSING_THEME_ID = 'missing-theme'

# *** fixtures

# ** fixture: theme_a
@pytest.fixture
def theme_a() -> ThemeAggregate:
    '''
    Build the first theme fixture for assembly order.

    :return: A theme placed first in the sample outline.
    :rtype: ThemeAggregate
    '''

    # Return the first arranged theme.
    return ThemeAggregate(
        id=THEME_ID_A,
        name='Universal IR abstractions',
        synthesized_description='Operations are the unit.',
        linkage_count=1,
    )


# ** fixture: theme_b
@pytest.fixture
def theme_b() -> ThemeAggregate:
    '''
    Build the second theme fixture for assembly order.

    :return: A theme placed second in the sample outline.
    :rtype: ThemeAggregate
    '''

    # Return the second arranged theme.
    return ThemeAggregate(
        id=THEME_ID_B,
        name='Progressive lowering',
        synthesized_description='Lower in small verified steps.',
        linkage_count=1,
    )


# ** fixture: outline
@pytest.fixture
def outline(theme_a, theme_b) -> OutlineAggregate:
    '''
    Build an outline aggregate with two slots.

    :param theme_a: The first theme fixture.
    :type theme_a: ThemeAggregate
    :param theme_b: The second theme fixture.
    :type theme_b: ThemeAggregate
    :return: An outline with two owned slots.
    :rtype: OutlineAggregate
    '''

    # Assemble the sample outline through the owned-slot lifecycle.
    assembled = OutlineAggregate(
        id=OUTLINE_ID,
        title='MLIR argument',
    )
    assembled.add_slot(theme_a.id)
    assembled.add_slot(theme_b.id)
    return assembled


# ** fixture: assemble_dependencies
@pytest.fixture
def assemble_dependencies(theme_a, theme_b) -> dict:
    '''
    Build mocked services for AssembleOutline.

    :param theme_a: The first theme fixture.
    :type theme_a: ThemeAggregate
    :param theme_b: The second theme fixture.
    :type theme_b: ThemeAggregate
    :return: Constructor dependencies for the assemble event.
    :rtype: dict
    '''

    # Mock each injected service with its interface contract.
    outline_service = mock.Mock(spec=OutlineService)
    theme_service = mock.Mock(spec=ThemeService)

    # Resolve known themes; unknown ids return None.
    def get_theme(theme_id):
        return {
            THEME_ID_A: theme_a,
            THEME_ID_B: theme_b,
        }.get(theme_id)

    theme_service.get.side_effect = get_theme

    # Return the assembled dependency map.
    return {
        'outline_service': outline_service,
        'theme_service': theme_service,
    }


# ** fixture: show_dependencies
@pytest.fixture
def show_dependencies(outline, theme_a, theme_b) -> dict:
    '''
    Build mocked services for ShowOutline.

    :param outline: The outline fixture.
    :type outline: OutlineAggregate
    :param theme_a: The first theme fixture.
    :type theme_a: ThemeAggregate
    :param theme_b: The second theme fixture.
    :type theme_b: ThemeAggregate
    :return: Constructor dependencies for the show event.
    :rtype: dict
    '''

    # Mock each injected service with its interface contract.
    outline_service = mock.Mock(spec=OutlineService)
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    source_service = mock.Mock(spec=SourceService)
    citation_style_service = mock.Mock(spec=CitationStyleRuleService)

    # Resolve the sample outline and its slotted themes.
    outline_service.get.return_value = outline
    theme_service.get.side_effect = lambda theme_id: {
        THEME_ID_A: theme_a,
        THEME_ID_B: theme_b,
    }.get(theme_id)
    linkage_service.list.return_value = []

    # Return the assembled dependency map.
    return {
        'outline_service': outline_service,
        'theme_service': theme_service,
        'linkage_service': linkage_service,
        'citation_service': citation_service,
        'source_service': source_service,
        'citation_style_service': citation_style_service,
    }


# *** tests

# ** test: test_assemble_outline_creates_slots_in_order
def test_assemble_outline_creates_slots_in_order(assemble_dependencies):
    '''
    Assembling two theme ids creates one outline with two slots in that order.

    :param assemble_dependencies: Mocked assemble-event dependencies.
    :type assemble_dependencies: dict
    '''

    # Assemble an outline from two known themes.
    result = DomainEvent.handle(
        AssembleOutline,
        dependencies=assemble_dependencies,
        title='MLIR argument',
        theme_ids=[THEME_ID_A, THEME_ID_B],
    )

    # The new outline is saved with both slots in the supplied order.
    assemble_dependencies['outline_service'].save.assert_called_once()
    assert result.title == 'MLIR argument'
    assert result.slot_count == 2
    assert [slot.theme_id for slot in result.slots] == [THEME_ID_A, THEME_ID_B]
    assert [slot.position for slot in result.slots] == [0, 1]
    assert not hasattr(result, 'content')
    assert not hasattr(result, 'context')


# ** test: test_assemble_outline_missing_theme_writes_nothing
def test_assemble_outline_missing_theme_writes_nothing(assemble_dependencies):
    '''
    A missing theme id fails with THEME_NOT_FOUND and writes no outline.

    :param assemble_dependencies: Mocked assemble-event dependencies.
    :type assemble_dependencies: dict
    '''

    # Assemble with a known theme followed by an unknown one.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            AssembleOutline,
            dependencies=assemble_dependencies,
            title='MLIR argument',
            theme_ids=[THEME_ID_A, MISSING_THEME_ID],
        )

    # Assert the structured not-found error and that nothing was saved.
    assert exc_info.value.error_code == THEME_NOT_FOUND_ID
    assemble_dependencies['outline_service'].save.assert_not_called()


# ** test: test_assemble_outline_creates_new_id_on_reassemble
def test_assemble_outline_creates_new_id_on_reassemble(assemble_dependencies):
    '''
    Re-assemble with the same themes creates a new Outline id.

    :param assemble_dependencies: Mocked assemble-event dependencies.
    :type assemble_dependencies: dict
    '''

    # Assemble the same arrangement twice.
    first = DomainEvent.handle(
        AssembleOutline,
        dependencies=assemble_dependencies,
        title='MLIR argument',
        theme_ids=[THEME_ID_A, THEME_ID_B],
    )
    second = DomainEvent.handle(
        AssembleOutline,
        dependencies=assemble_dependencies,
        title='MLIR argument',
        theme_ids=[THEME_ID_A, THEME_ID_B],
    )

    # Each assemble is a new outline; the slots match and the ids do not.
    assert first.id != second.id
    assert [slot.theme_id for slot in first.slots] == [
        slot.theme_id for slot in second.slots
    ]
    assert assemble_dependencies['outline_service'].save.call_count == 2


# ** test: test_show_outline_names_slotted_themes
def test_show_outline_names_slotted_themes(
        outline,
        theme_a,
        theme_b,
        show_dependencies,
    ):
    '''
    Showing an outline names each slot's theme and carries no section prose.

    :param outline: The outline fixture.
    :type outline: OutlineAggregate
    :param theme_a: The first theme fixture.
    :type theme_a: ThemeAggregate
    :param theme_b: The second theme fixture.
    :type theme_b: ThemeAggregate
    :param show_dependencies: Mocked show-event dependencies.
    :type show_dependencies: dict
    '''

    # Show the assembled outline without a citation style.
    result = DomainEvent.handle(
        ShowOutline,
        dependencies=show_dependencies,
        id=OUTLINE_ID,
    )

    # Theme names appear in slot order; no section content or context exists.
    assert isinstance(result, OutlineResponse)
    assert result.id == outline.id
    assert [theme.id for theme in result.linked_themes] == [
        theme_a.id,
        theme_b.id,
    ]
    assert [theme.name for theme in result.linked_themes] == [
        theme_a.name,
        theme_b.name,
    ]
    assert result.citation_previews == []
    assert not hasattr(result, 'content')
    assert not hasattr(result, 'context')
    show_dependencies['citation_style_service'].get_rule.assert_not_called()


# ** test: test_get_outline_missing_outline
def test_get_outline_missing_outline():
    '''
    Getting an unknown outline raises OUTLINE_NOT_FOUND.
    '''

    # Outline service cannot resolve the requested id.
    outline_service = mock.Mock(spec=OutlineService)
    outline_service.get.return_value = None

    # Execute and expect OUTLINE_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            GetOutline,
            dependencies={'outline_service': outline_service},
            id='missing-outline',
        )

    # Assert the structured not-found error.
    assert exc_info.value.error_code == OUTLINE_NOT_FOUND_ID


# ** test: test_show_outline_missing_outline
def test_show_outline_missing_outline(show_dependencies):
    '''
    Showing an unknown outline raises OUTLINE_NOT_FOUND.

    :param show_dependencies: Mocked show-event dependencies.
    :type show_dependencies: dict
    '''

    # The outline service cannot resolve the requested id.
    show_dependencies['outline_service'].get.return_value = None

    # Execute and expect OUTLINE_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            ShowOutline,
            dependencies=show_dependencies,
            id='missing-outline',
        )

    # Assert the structured not-found error.
    assert exc_info.value.error_code == OUTLINE_NOT_FOUND_ID

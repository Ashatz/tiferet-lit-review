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
    OUTLINE_SLOT_NOT_FOUND_ID,
    AddOutlineSlot,
    AddOutlineSlotTheme,
    AssembleOutline,
    GetOutline,
    RemoveOutlineSlotTheme,
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

# ** constant: slot_id
SLOT_ID = 'c3d4e5f6-a7b8-9012-cdef-123456789012'

# ** constant: theme_id_a
THEME_ID_A = 'universal-ir-abstractions'

# ** constant: theme_id_b
THEME_ID_B = 'progressive-lowering'

# ** constant: missing_theme_id
MISSING_THEME_ID = 'missing-theme'

# ** constant: missing_slot_id
MISSING_SLOT_ID = 'missing-slot'

# *** fixtures

# ** fixture: theme_a
@pytest.fixture
def theme_a() -> ThemeAggregate:
    '''
    Build the first theme fixture for slot membership.

    :return: A theme included first in the sample slot.
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
    Build the second theme fixture for slot membership.

    :return: A theme included second in the sample slot.
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
    Build an outline aggregate with one named slot and two themes.

    :param theme_a: The first theme fixture.
    :type theme_a: ThemeAggregate
    :param theme_b: The second theme fixture.
    :type theme_b: ThemeAggregate
    :return: An outline with one owned named slot.
    :rtype: OutlineAggregate
    '''

    # Assemble the sample outline through the owned-slot lifecycle.
    assembled = OutlineAggregate(
        id=OUTLINE_ID,
        title='MLIR argument',
    )
    assembled.add_slot(
        'Introduction',
        theme_ids=[theme_a.id, theme_b.id],
        id=SLOT_ID,
    )
    return assembled

# ** fixture: assemble_dependencies
@pytest.fixture
def assemble_dependencies() -> dict:
    '''
    Build mocked services for AssembleOutline.

    :return: Constructor dependencies for the assemble event.
    :rtype: dict
    '''

    # Mock the injected outline service.
    return {
        'outline_service': mock.Mock(spec=OutlineService),
    }

# ** fixture: slot_dependencies
@pytest.fixture
def slot_dependencies(theme_a, theme_b) -> dict:
    '''
    Build mocked services for slot and theme-join events.

    :param theme_a: The first theme fixture.
    :type theme_a: ThemeAggregate
    :param theme_b: The second theme fixture.
    :type theme_b: ThemeAggregate
    :return: Constructor dependencies for slot mutation events.
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

# ** test: test_assemble_outline_creates_empty_outline
def test_assemble_outline_creates_empty_outline(assemble_dependencies):
    '''
    Assembling by title creates an outline with zero slots.

    :param assemble_dependencies: Mocked assemble-event dependencies.
    :type assemble_dependencies: dict
    '''

    # Name an outline without any slots.
    result = DomainEvent.handle(
        AssembleOutline,
        dependencies=assemble_dependencies,
        title='MLIR argument',
    )

    # The new outline is saved empty so named slots can be added later.
    assemble_dependencies['outline_service'].save.assert_called_once()
    assert result.title == 'MLIR argument'
    assert result.slot_count == 0
    assert result.slots == []
    assert not hasattr(result, 'content')
    assert not hasattr(result, 'context')

# ** test: test_assemble_outline_creates_new_id_on_reassemble
def test_assemble_outline_creates_new_id_on_reassemble(assemble_dependencies):
    '''
    Re-assemble with the same title creates a new Outline id.

    :param assemble_dependencies: Mocked assemble-event dependencies.
    :type assemble_dependencies: dict
    '''

    # Assemble the same arrangement twice.
    first = DomainEvent.handle(
        AssembleOutline,
        dependencies=assemble_dependencies,
        title='MLIR argument',
    )
    second = DomainEvent.handle(
        AssembleOutline,
        dependencies=assemble_dependencies,
        title='MLIR argument',
    )

    # Each assemble is a new outline.
    assert first.id != second.id
    assert assemble_dependencies['outline_service'].save.call_count == 2

# ** test: test_add_outline_slot_appends_named_grouping
def test_add_outline_slot_appends_named_grouping(theme_a, theme_b, slot_dependencies):
    '''
    Adding a slot appends a named grouping with optional themes.

    :param theme_a: The first theme fixture.
    :type theme_a: ThemeAggregate
    :param theme_b: The second theme fixture.
    :type theme_b: ThemeAggregate
    :param slot_dependencies: Mocked slot-event dependencies.
    :type slot_dependencies: dict
    '''

    # Start from an empty outline.
    outline = OutlineAggregate(id=OUTLINE_ID, title='MLIR argument')
    slot_dependencies['outline_service'].get.return_value = outline

    # Append a named slot that already includes both themes.
    result = DomainEvent.handle(
        AddOutlineSlot,
        dependencies=slot_dependencies,
        id=OUTLINE_ID,
        title='Introduction',
        theme_ids=[THEME_ID_A, THEME_ID_B],
    )

    # The owned slot is saved with its title and theme joins.
    slot_dependencies['outline_service'].save.assert_called_once_with(outline)
    assert result.slot_count == 1
    assert result.slots[0].title == 'Introduction'
    assert result.slots[0].id
    assert [theme.theme_id for theme in result.slots[0].themes] == [
        THEME_ID_A,
        THEME_ID_B,
    ]
    assert result.slots[0].position == 0
    assert not hasattr(result, 'content')
    assert not hasattr(result, 'context')

# ** test: test_add_outline_slot_without_themes
def test_add_outline_slot_without_themes(slot_dependencies):
    '''
    Adding a slot by title alone creates an empty grouping.

    :param slot_dependencies: Mocked slot-event dependencies.
    :type slot_dependencies: dict
    '''

    # Start from an empty outline.
    outline = OutlineAggregate(id=OUTLINE_ID, title='MLIR argument')
    slot_dependencies['outline_service'].get.return_value = outline

    # Append a named slot with no themes.
    result = DomainEvent.handle(
        AddOutlineSlot,
        dependencies=slot_dependencies,
        id=OUTLINE_ID,
        title='Methods',
    )

    # The owned slot is saved empty so themes can be added later.
    slot_dependencies['outline_service'].save.assert_called_once_with(outline)
    slot_dependencies['theme_service'].get.assert_not_called()
    assert result.slot_count == 1
    assert result.slots[0].title == 'Methods'
    assert result.slots[0].theme_count == 0
    assert result.slots[0].themes == []

# ** test: test_add_outline_slot_missing_outline
def test_add_outline_slot_missing_outline(slot_dependencies):
    '''
    Adding a slot to an unknown outline raises OUTLINE_NOT_FOUND.

    :param slot_dependencies: Mocked slot-event dependencies.
    :type slot_dependencies: dict
    '''

    # The outline service cannot resolve the requested id.
    slot_dependencies['outline_service'].get.return_value = None

    # Execute and expect OUTLINE_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            AddOutlineSlot,
            dependencies=slot_dependencies,
            id='missing-outline',
            title='Introduction',
        )

    # Assert the structured not-found error and that nothing was saved.
    assert exc_info.value.error_code == OUTLINE_NOT_FOUND_ID
    slot_dependencies['outline_service'].save.assert_not_called()

# ** test: test_add_outline_slot_missing_theme
def test_add_outline_slot_missing_theme(outline, slot_dependencies):
    '''
    Adding a slot with an unknown theme raises THEME_NOT_FOUND.

    :param outline: The outline fixture.
    :type outline: OutlineAggregate
    :param slot_dependencies: Mocked slot-event dependencies.
    :type slot_dependencies: dict
    '''

    # The outline exists; the theme does not.
    slot_dependencies['outline_service'].get.return_value = outline

    # Execute and expect THEME_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            AddOutlineSlot,
            dependencies=slot_dependencies,
            id=OUTLINE_ID,
            title='Discussion',
            theme_ids=[MISSING_THEME_ID],
        )

    # Assert the structured not-found error and that no slot was written.
    assert exc_info.value.error_code == THEME_NOT_FOUND_ID
    slot_dependencies['outline_service'].save.assert_not_called()
    assert outline.slot_count == 1

# ** test: test_add_outline_slot_theme_is_idempotent
def test_add_outline_slot_theme_is_idempotent(outline, slot_dependencies):
    '''
    Re-adding an existing theme to a slot returns the outline unchanged.

    :param outline: The outline fixture.
    :type outline: OutlineAggregate
    :param slot_dependencies: Mocked slot-event dependencies.
    :type slot_dependencies: dict
    '''

    # The outline already owns this theme on the named slot.
    slot_dependencies['outline_service'].get.return_value = outline

    # Re-add the first theme to the existing slot.
    result = DomainEvent.handle(
        AddOutlineSlotTheme,
        dependencies=slot_dependencies,
        id=OUTLINE_ID,
        slot_id=SLOT_ID,
        theme_id=THEME_ID_A,
    )

    # No save and the theme count stays at two.
    slot_dependencies['outline_service'].save.assert_not_called()
    assert result is outline
    assert result.slots[0].theme_count == 2

# ** test: test_add_outline_slot_theme_missing_slot
def test_add_outline_slot_theme_missing_slot(outline, slot_dependencies):
    '''
    Adding a theme to an unknown slot raises OUTLINE_SLOT_NOT_FOUND.

    :param outline: The outline fixture.
    :type outline: OutlineAggregate
    :param slot_dependencies: Mocked slot-event dependencies.
    :type slot_dependencies: dict
    '''

    # The outline exists; the slot does not.
    slot_dependencies['outline_service'].get.return_value = outline

    # Execute and expect OUTLINE_SLOT_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            AddOutlineSlotTheme,
            dependencies=slot_dependencies,
            id=OUTLINE_ID,
            slot_id=MISSING_SLOT_ID,
            theme_id=THEME_ID_A,
        )

    # Assert the structured not-found error and that nothing was saved.
    assert exc_info.value.error_code == OUTLINE_SLOT_NOT_FOUND_ID
    slot_dependencies['outline_service'].save.assert_not_called()

# ** test: test_remove_outline_slot_theme
def test_remove_outline_slot_theme(outline, slot_dependencies):
    '''
    Removing a theme from a named slot drops that join.

    :param outline: The outline fixture.
    :type outline: OutlineAggregate
    :param slot_dependencies: Mocked slot-event dependencies.
    :type slot_dependencies: dict
    '''

    # The outline owns both themes on the named slot.
    slot_dependencies['outline_service'].get.return_value = outline

    # Remove the first theme from the existing slot.
    result = DomainEvent.handle(
        RemoveOutlineSlotTheme,
        dependencies={'outline_service': slot_dependencies['outline_service']},
        id=OUTLINE_ID,
        slot_id=SLOT_ID,
        theme_id=THEME_ID_A,
    )

    # The remaining theme stays on the named slot.
    slot_dependencies['outline_service'].save.assert_called_once_with(outline)
    assert result.slots[0].theme_count == 1
    assert [theme.theme_id for theme in result.slots[0].themes] == [THEME_ID_B]

# ** test: test_remove_outline_slot_theme_missing_slot
def test_remove_outline_slot_theme_missing_slot(outline, slot_dependencies):
    '''
    Removing a theme from an unknown slot raises OUTLINE_SLOT_NOT_FOUND.

    :param outline: The outline fixture.
    :type outline: OutlineAggregate
    :param slot_dependencies: Mocked slot-event dependencies.
    :type slot_dependencies: dict
    '''

    # The outline exists; the slot does not.
    slot_dependencies['outline_service'].get.return_value = outline

    # Execute and expect OUTLINE_SLOT_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            RemoveOutlineSlotTheme,
            dependencies={'outline_service': slot_dependencies['outline_service']},
            id=OUTLINE_ID,
            slot_id=MISSING_SLOT_ID,
            theme_id=THEME_ID_A,
        )

    # Assert the structured not-found error and that nothing was saved.
    assert exc_info.value.error_code == OUTLINE_SLOT_NOT_FOUND_ID
    slot_dependencies['outline_service'].save.assert_not_called()

# ** test: test_show_outline_names_slots_and_themes
def test_show_outline_names_slots_and_themes(
        outline,
        theme_a,
        theme_b,
        show_dependencies,
    ):
    '''
    Showing an outline names each slot and its themes and carries no prose.

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

    # Slot titles and theme names appear; no section content or context exists.
    assert isinstance(result, OutlineResponse)
    assert result.id == outline.id
    assert [slot.title for slot in result.slots] == ['Introduction']
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

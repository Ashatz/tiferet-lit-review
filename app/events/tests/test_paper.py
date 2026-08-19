"""Lit Review Paper Event Tests"""

# *** imports

# ** infra
import pytest
from unittest import mock

# ** app
from tiferet import DomainEvent
from tiferet.assets import TiferetError

from app.events.abstract import ABSTRACT_NOT_FOUND_ID
from app.events.citation import CITATION_NOT_FOUND_ID
from app.events.outline import OUTLINE_NOT_FOUND_ID
from app.events.paper import (
    PAPER_NOT_FOUND_ID,
    PAPER_SECTION_NOT_FOUND_ID,
    AddPaperCitation,
    OpenPaperFromOutline,
    SetPaperAbstract,
    ShowPaper,
    UpdatePaperSection,
)
from app.interfaces.abstract import AbstractService
from app.interfaces.citation import CitationService
from app.interfaces.outline import OutlineService
from app.interfaces.paper import PaperService
from app.interfaces.theme import ThemeService
from app.mappers.abstract import AbstractAggregate
from app.mappers.citation import CitationAggregate
from app.mappers.outline import OutlineAggregate
from app.mappers.paper import PaperAggregate, PaperResponse
from app.mappers.theme import ThemeAggregate

# *** constants

# ** constant: outline_id
OUTLINE_ID = 'b2c3d4e5-f6a7-8901-bcde-f12345678901'

# ** constant: paper_id
PAPER_ID = 'd4e5f6a7-b8c9-0123-def0-234567890123'

# ** constant: section_id
SECTION_ID = 'e5f6a7b8-c9d0-1234-ef01-345678901234'

# ** constant: theme_id_a
THEME_ID_A = 'universal-ir-abstractions'

# ** constant: theme_id_b
THEME_ID_B = 'progressive-lowering'

# ** constant: citation_id
CITATION_ID = 'cite-001'

# ** constant: abstract_id
ABSTRACT_ID = 'abs-001'

# *** fixtures

# ** fixture: theme_a
@pytest.fixture
def theme_a() -> ThemeAggregate:
    '''
    Build the first theme fixture for section membership.

    :return: A theme included first in the sample section.
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
    Build the second theme fixture for section membership.

    :return: A theme included second in the sample section.
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
    Build an outline aggregate with two named slots.

    :param theme_a: The first theme fixture.
    :type theme_a: ThemeAggregate
    :param theme_b: The second theme fixture.
    :type theme_b: ThemeAggregate
    :return: An outline with two owned named slots.
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
        id='intro-slot',
    )
    assembled.add_slot('Results', id='results-slot')
    return assembled

# ** fixture: paper
@pytest.fixture
def paper(theme_a, theme_b) -> PaperAggregate:
    '''
    Build a paper aggregate with one named section and two themes.

    :param theme_a: The first theme fixture.
    :type theme_a: ThemeAggregate
    :param theme_b: The second theme fixture.
    :type theme_b: ThemeAggregate
    :return: A paper with one owned named section.
    :rtype: PaperAggregate
    '''

    # Open the sample paper through the owned-section lifecycle.
    opened = PaperAggregate(
        id=PAPER_ID,
        title='MLIR argument',
        outline_id=OUTLINE_ID,
    )
    opened.add_section(
        'Introduction',
        theme_ids=[theme_a.id, theme_b.id],
        id=SECTION_ID,
    )
    return opened

# ** fixture: open_dependencies
@pytest.fixture
def open_dependencies(outline) -> dict:
    '''
    Build mocked services for OpenPaperFromOutline.

    :param outline: The outline fixture.
    :type outline: OutlineAggregate
    :return: Constructor dependencies for the open event.
    :rtype: dict
    '''

    # Mock each injected service with its interface contract.
    paper_service = mock.Mock(spec=PaperService)
    outline_service = mock.Mock(spec=OutlineService)
    outline_service.get.return_value = outline

    # Return the assembled dependency map.
    return {
        'paper_service': paper_service,
        'outline_service': outline_service,
    }

# ** fixture: paper_dependencies
@pytest.fixture
def paper_dependencies(paper) -> dict:
    '''
    Build mocked services for paper-owned mutation events.

    :param paper: The paper fixture.
    :type paper: PaperAggregate
    :return: Constructor dependencies for paper mutation events.
    :rtype: dict
    '''

    # Mock the injected paper service.
    paper_service = mock.Mock(spec=PaperService)
    paper_service.get.return_value = paper
    return {
        'paper_service': paper_service,
    }

# ** fixture: show_dependencies
@pytest.fixture
def show_dependencies(paper, theme_a, theme_b) -> dict:
    '''
    Build mocked services for ShowPaper.

    :param paper: The paper fixture.
    :type paper: PaperAggregate
    :param theme_a: The first theme fixture.
    :type theme_a: ThemeAggregate
    :param theme_b: The second theme fixture.
    :type theme_b: ThemeAggregate
    :return: Constructor dependencies for the show event.
    :rtype: dict
    '''

    # Mock each injected service with its interface contract.
    paper_service = mock.Mock(spec=PaperService)
    theme_service = mock.Mock(spec=ThemeService)
    citation_service = mock.Mock(spec=CitationService)
    paper_service.get.return_value = paper
    theme_service.get.side_effect = lambda theme_id: {
        THEME_ID_A: theme_a,
        THEME_ID_B: theme_b,
    }.get(theme_id)

    # Return the assembled dependency map.
    return {
        'paper_service': paper_service,
        'theme_service': theme_service,
        'citation_service': citation_service,
    }

# *** tests

# ** test: test_open_paper_from_outline_creates_sections_in_slot_order
def test_open_paper_from_outline_creates_sections_in_slot_order(open_dependencies, outline):
    '''
    Opening a paper forks one empty section per outline slot, in order.

    :param open_dependencies: Constructor dependencies for the open event.
    :type open_dependencies: dict
    :param outline: The outline fixture.
    :type outline: OutlineAggregate
    '''

    # Open a paper from the sample outline.
    paper = DomainEvent.handle(
        OpenPaperFromOutline,
        dependencies=open_dependencies,
        outline_id=OUTLINE_ID,
    )

    # The paper owns one section per slot, with themes copied and empty drafts.
    assert paper.outline_id == OUTLINE_ID
    assert paper.title == 'MLIR argument'
    assert paper.section_count == 2
    assert [section.title for section in paper.sections] == [
        'Introduction',
        'Results',
    ]
    assert [theme.theme_id for theme in paper.sections[0].themes] == [
        THEME_ID_A,
        THEME_ID_B,
    ]
    assert paper.sections[0].content == ''
    assert paper.sections[0].context == ''
    assert paper.sections[1].theme_count == 0
    open_dependencies['paper_service'].save.assert_called_once()
    open_dependencies['outline_service'].save.assert_not_called()

# ** test: test_open_paper_from_outline_missing_outline
def test_open_paper_from_outline_missing_outline(open_dependencies):
    '''
    Opening a paper from a missing outline raises OUTLINE_NOT_FOUND.

    :param open_dependencies: Constructor dependencies for the open event.
    :type open_dependencies: dict
    '''

    # Resolve no origin outline.
    open_dependencies['outline_service'].get.return_value = None

    # The missing outline writes no paper.
    with pytest.raises(TiferetError) as error:
        DomainEvent.handle(
            OpenPaperFromOutline,
            dependencies=open_dependencies,
            outline_id='missing',
        )
    assert error.value.error_code == OUTLINE_NOT_FOUND_ID
    open_dependencies['paper_service'].save.assert_not_called()

# ** test: test_update_paper_section_persists_content_and_context
def test_update_paper_section_persists_content_and_context(paper_dependencies, paper):
    '''
    Updating a section persists content and context exactly.

    :param paper_dependencies: Constructor dependencies for the update event.
    :type paper_dependencies: dict
    :param paper: The paper fixture.
    :type paper: PaperAggregate
    '''

    # Write both draft fields on the owned section.
    updated = DomainEvent.handle(
        UpdatePaperSection,
        dependencies=paper_dependencies,
        id=PAPER_ID,
        section_id=SECTION_ID,
        content='Drafted introduction.',
        context='Why this section exists.',
    )

    # The owned section keeps both writes.
    section = updated.get_section(SECTION_ID)
    assert section.content == 'Drafted introduction.'
    assert section.context == 'Why this section exists.'
    paper_dependencies['paper_service'].save.assert_called_once()

# ** test: test_update_paper_section_missing_section
def test_update_paper_section_missing_section(paper_dependencies):
    '''
    Updating a missing section raises PAPER_SECTION_NOT_FOUND.

    :param paper_dependencies: Constructor dependencies for the update event.
    :type paper_dependencies: dict
    '''

    # The missing section writes nothing.
    with pytest.raises(TiferetError) as error:
        DomainEvent.handle(
            UpdatePaperSection,
            dependencies=paper_dependencies,
            id=PAPER_ID,
            section_id='missing-section',
            content='unused',
        )
    assert error.value.error_code == PAPER_SECTION_NOT_FOUND_ID
    paper_dependencies['paper_service'].save.assert_not_called()

# ** test: test_show_paper_includes_themes_before_citations
def test_show_paper_includes_themes_before_citations(show_dependencies, theme_a, theme_b):
    '''
    Showing a paper includes its section themes before any citations.

    :param show_dependencies: Constructor dependencies for the show event.
    :type show_dependencies: dict
    :param theme_a: The first theme fixture.
    :type theme_a: ThemeAggregate
    :param theme_b: The second theme fixture.
    :type theme_b: ThemeAggregate
    '''

    # Show the paper immediately after open.
    shown = DomainEvent.handle(
        ShowPaper,
        dependencies=show_dependencies,
        id=PAPER_ID,
    )

    # Themes are visible even when no citations have been added.
    assert isinstance(shown, PaperResponse)
    assert [theme.id for theme in shown.linked_themes] == [
        theme_a.id,
        theme_b.id,
    ]
    assert shown.linked_citations == []
    assert shown.citation_count == 0

# ** test: test_set_paper_abstract_copies_kb_abstract_without_deleting
def test_set_paper_abstract_copies_kb_abstract_without_deleting(paper_dependencies):
    '''
    Copying a KB Abstract onto the paper does not delete the source brief.

    :param paper_dependencies: Shared paper service mock.
    :type paper_dependencies: dict
    '''

    # Mock a standing KB Abstract that remains after the copy.
    abstract_service = mock.Mock(spec=AbstractService)
    abstract = AbstractAggregate(
        id=ABSTRACT_ID,
        name='MLIR brief',
        body='A standing argument brief.',
    )
    abstract_service.get.return_value = abstract

    # Copy the KB Abstract onto the paper.
    paper = DomainEvent.handle(
        SetPaperAbstract,
        dependencies={
            'paper_service': paper_dependencies['paper_service'],
            'abstract_service': abstract_service,
        },
        id=PAPER_ID,
        abstract_id=ABSTRACT_ID,
    )

    # The paper owns a copy; the KB Abstract is not deleted.
    assert paper.abstract.body == 'A standing argument brief.'
    assert paper.abstract.source_abstract_id == ABSTRACT_ID
    abstract_service.save.assert_not_called()
    paper_dependencies['paper_service'].save.assert_called_once()

# ** test: test_set_paper_abstract_missing_kb_abstract
def test_set_paper_abstract_missing_kb_abstract(paper_dependencies):
    '''
    Copying a missing KB Abstract raises ABSTRACT_NOT_FOUND.

    :param paper_dependencies: Shared paper service mock.
    :type paper_dependencies: dict
    '''

    # Resolve no KB Abstract.
    abstract_service = mock.Mock(spec=AbstractService)
    abstract_service.get.return_value = None

    # The missing brief writes no paper abstract.
    with pytest.raises(TiferetError) as error:
        DomainEvent.handle(
            SetPaperAbstract,
            dependencies={
                'paper_service': paper_dependencies['paper_service'],
                'abstract_service': abstract_service,
            },
            id=PAPER_ID,
            abstract_id='missing',
        )
    assert error.value.error_code == ABSTRACT_NOT_FOUND_ID
    paper_dependencies['paper_service'].save.assert_not_called()

# ** test: test_add_paper_citation_missing_citation
def test_add_paper_citation_missing_citation(paper_dependencies):
    '''
    Adding a missing KB citation raises CITATION_NOT_FOUND.

    :param paper_dependencies: Shared paper service mock.
    :type paper_dependencies: dict
    '''

    # Resolve no KB citation.
    citation_service = mock.Mock(spec=CitationService)
    citation_service.get.return_value = None

    # The missing citation writes no manuscript join.
    with pytest.raises(TiferetError) as error:
        DomainEvent.handle(
            AddPaperCitation,
            dependencies={
                'paper_service': paper_dependencies['paper_service'],
                'citation_service': citation_service,
            },
            id=PAPER_ID,
            citation_id=CITATION_ID,
        )
    assert error.value.error_code == CITATION_NOT_FOUND_ID
    paper_dependencies['paper_service'].save.assert_not_called()

# ** test: test_add_paper_citation_joins_existing_citation
def test_add_paper_citation_joins_existing_citation(paper_dependencies):
    '''
    Adding an existing KB citation records the manuscript join.

    :param paper_dependencies: Shared paper service mock.
    :type paper_dependencies: dict
    '''

    # Resolve a known KB citation.
    citation_service = mock.Mock(spec=CitationService)
    citation_service.get.return_value = CitationAggregate(
        id=CITATION_ID,
        source_id='src-001',
        locator='p. 1',
        excerpt='Operations are the unit.',
    )

    # Record the citation on the owned section.
    paper = DomainEvent.handle(
        AddPaperCitation,
        dependencies={
            'paper_service': paper_dependencies['paper_service'],
            'citation_service': citation_service,
        },
        id=PAPER_ID,
        citation_id=CITATION_ID,
        section_id=SECTION_ID,
    )

    # The paper now uses the citation in that section.
    assert paper.has_citation(CITATION_ID, section_id=SECTION_ID)
    assert paper.citation_count == 1
    paper_dependencies['paper_service'].save.assert_called_once()

# ** test: test_get_paper_missing
def test_get_paper_missing():
    '''
    Retrieving a missing paper raises PAPER_NOT_FOUND.
    '''

    # Resolve no paper.
    paper_service = mock.Mock(spec=PaperService)
    paper_service.get.return_value = None

    # The missing paper is not shown.
    with pytest.raises(TiferetError) as error:
        DomainEvent.handle(
            ShowPaper,
            dependencies={
                'paper_service': paper_service,
                'theme_service': mock.Mock(spec=ThemeService),
                'citation_service': mock.Mock(spec=CitationService),
            },
            id='missing',
        )
    assert error.value.error_code == PAPER_NOT_FOUND_ID

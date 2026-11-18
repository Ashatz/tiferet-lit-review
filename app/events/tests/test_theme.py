"""Lit Review Theme Event Tests"""

# *** imports

# ** core
from unittest import mock

# ** infra
import pytest
from tiferet_h5.utils import H5Client

# ** app
from tiferet import DomainEvent
from tiferet.assets import TiferetError

from app.events.citation import CITATION_NOT_FOUND_ID
from app.events.theme import (
    LINKAGE_NOT_FOUND_ID,
    THEME_NOT_FOUND_ID,
    LinkCitationToTheme,
    ReinstateLinkage,
    ResynthesizeTheme,
    RetireLinkage,
    ShowTheme,
    UpdateTheme,
)
from app.interfaces.activity import ActivityService
from app.interfaces.citation import CitationService
from app.interfaces.linkage import LinkageService
from app.interfaces.synthesis import ThemeSynthesisService
from app.interfaces.theme import ThemeService
from app.mappers.citation import CitationAggregate
from app.mappers.linkage import LinkageAggregate
from app.mappers.theme import ThemeAggregate
from app.repos.citation import CITATIONS_NODE_PATH, CitationH5Repository
from app.repos.linkage import LINKAGES_TABLE_PATH, LinkageH5Repository
from app.repos.theme import ThemeH5Repository

# *** constants

# ** constant: theme_id
THEME_ID = 'universal-ir-abstractions'

# ** constant: citation_id
CITATION_ID = '02a49f90-0ff1-48cb-916a-fbc92f9712dd'

# ** constant: curated_description
CURATED_DESCRIPTION = 'Custom narrative synthesis'

# ** constant: synthesized_description
SYNTHESIZED_DESCRIPTION = 'Lattner et al. (2020): Operations are the unit.'

# *** fixtures

# ** fixture: theme
@pytest.fixture
def theme() -> ThemeAggregate:
    '''
    Build a theme aggregate with curated synthesis text.

    :return: A theme with an existing synthesized description.
    :rtype: ThemeAggregate
    '''

    # Return a theme whose description must survive a default link.
    return ThemeAggregate(
        id=THEME_ID,
        name='Universal IR abstractions',
        synthesized_description=CURATED_DESCRIPTION,
        linkage_count=0,
        retired_linkage_count=0,
    )

# ** fixture: citation
@pytest.fixture
def citation() -> CitationAggregate:
    '''
    Build a citation aggregate to attach to a theme.

    :return: A citation belonging to a placeholder source.
    :rtype: CitationAggregate
    '''

    # Return a citation with the identifiers used by the link tests.
    return CitationAggregate(
        id=CITATION_ID,
        source_id='source-1',
        locator='4-4',
        excerpt='Operations are the unit.',
    )

# ** fixture: linkage
@pytest.fixture
def linkage() -> LinkageAggregate:
    '''
    Build the linkage created by a successful theme link.

    :return: A linkage for the sample citation and theme.
    :rtype: LinkageAggregate
    '''

    # Return the structural pair the link event persists.
    return LinkageAggregate(
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
    )

# ** fixture: link_dependencies
@pytest.fixture
def link_dependencies(theme, citation, linkage) -> dict:
    '''
    Build mocked services for LinkCitationToTheme.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param linkage: The linkage fixture.
    :type linkage: LinkageAggregate
    :return: Constructor dependencies for the link event.
    :rtype: dict
    '''

    # Mock each injected service with its interface contract.
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_synthesis_service = mock.Mock(spec=ThemeSynthesisService)

    # Resolve the sample theme and citation; default list is empty (new pair).
    theme_service.get.return_value = theme
    citation_service.get.return_value = citation
    citation_service.list.return_value = [citation]
    linkage_service.list.return_value = []
    theme_synthesis_service.synthesize.return_value = SYNTHESIZED_DESCRIPTION

    # After save, a full-set list returns the new linkage for opt-in synthesis.
    def list_linkages(theme_id=None, citation_id=None):
        if citation_id is not None:
            return []
        return [linkage]

    linkage_service.list.side_effect = list_linkages

    # Return the assembled dependency map.
    return {
        'theme_service': theme_service,
        'linkage_service': linkage_service,
        'citation_service': citation_service,
        'theme_synthesis_service': theme_synthesis_service,
        'activity_service': mock.Mock(spec=ActivityService),
    }

# *** tests

# ** test: test_link_citation_to_theme_default_preserves_description
def test_link_citation_to_theme_default_preserves_description(
        theme,
        link_dependencies,
    ):
    '''
    Default linking creates the linkage without rewriting synthesis.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param link_dependencies: Mocked link-event dependencies.
    :type link_dependencies: dict
    '''

    # Link without the opt-in synthesis flag.
    result = DomainEvent.handle(
        LinkCitationToTheme,
        dependencies=link_dependencies,
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
    )

    # The linkage is saved and the count increments; the curated text stays.
    link_dependencies['linkage_service'].save.assert_called_once()
    link_dependencies['theme_service'].save.assert_called_once_with(theme)
    link_dependencies['theme_synthesis_service'].synthesize.assert_not_called()
    assert result.linkage_count == 1
    assert result.synthesized_description == CURATED_DESCRIPTION

# ** test: test_link_citation_to_theme_include_synthesis_rewrites_description
def test_link_citation_to_theme_include_synthesis_rewrites_description(
        theme,
        citation,
        link_dependencies,
    ):
    '''
    Opt-in linking re-synthesizes from the full linkage set.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param link_dependencies: Mocked link-event dependencies.
    :type link_dependencies: dict
    '''

    # Link with include_synthesis so the injected synthesizer runs.
    result = DomainEvent.handle(
        LinkCitationToTheme,
        dependencies=link_dependencies,
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
        include_synthesis=True,
    )

    # The synthesizer receives the full citation set and the description updates.
    link_dependencies['theme_synthesis_service'].synthesize.assert_called_once()
    args, _kwargs = link_dependencies['theme_synthesis_service'].synthesize.call_args
    assert args[0] is theme
    assert args[1] == [citation]
    assert result.linkage_count == 1
    assert result.synthesized_description == SYNTHESIZED_DESCRIPTION

# ** test: test_link_citation_to_theme_is_idempotent
def test_link_citation_to_theme_is_idempotent(theme, linkage, link_dependencies):
    '''
    Re-linking an existing pair returns the theme without mutation.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param linkage: The existing linkage fixture.
    :type linkage: LinkageAggregate
    :param link_dependencies: Mocked link-event dependencies.
    :type link_dependencies: dict
    '''

    # An existing pair is already stored for this citation and theme.
    link_dependencies['linkage_service'].list.side_effect = None
    link_dependencies['linkage_service'].list.return_value = [linkage]

    # Re-link the same pair.
    result = DomainEvent.handle(
        LinkCitationToTheme,
        dependencies=link_dependencies,
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
    )

    # No second row, no save, no synthesis, and the curated text remains.
    link_dependencies['linkage_service'].save.assert_not_called()
    link_dependencies['theme_service'].save.assert_not_called()
    link_dependencies['theme_synthesis_service'].synthesize.assert_not_called()
    assert result is theme
    assert result.synthesized_description == CURATED_DESCRIPTION
    assert result.linkage_count == 0

# ** test: test_link_citation_to_theme_missing_theme
def test_link_citation_to_theme_missing_theme(link_dependencies):
    '''
    Linking to an unknown theme raises THEME_NOT_FOUND.

    :param link_dependencies: Mocked link-event dependencies.
    :type link_dependencies: dict
    '''

    # The theme service cannot resolve the requested id.
    link_dependencies['theme_service'].get.return_value = None

    # Execute and expect THEME_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            LinkCitationToTheme,
            dependencies=link_dependencies,
            citation_id=CITATION_ID,
            theme_id=THEME_ID,
        )

    # Assert the structured not-found error.
    assert exc_info.value.error_code == THEME_NOT_FOUND_ID

# ** test: test_link_citation_to_theme_missing_citation
def test_link_citation_to_theme_missing_citation(link_dependencies):
    '''
    Linking an unknown citation raises CITATION_NOT_FOUND.

    :param link_dependencies: Mocked link-event dependencies.
    :type link_dependencies: dict
    '''

    # The citation service cannot resolve the requested id.
    link_dependencies['citation_service'].get.return_value = None

    # Execute and expect CITATION_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            LinkCitationToTheme,
            dependencies=link_dependencies,
            citation_id=CITATION_ID,
            theme_id=THEME_ID,
        )

    # Assert the structured not-found error.
    assert exc_info.value.error_code == CITATION_NOT_FOUND_ID

# ** test: test_link_citation_to_theme_idempotent_with_synthesis_uses_active_set
def test_link_citation_to_theme_idempotent_with_synthesis_uses_active_set(
        theme,
        citation,
        linkage,
        link_dependencies,
    ):
    '''
    Re-linking an existing, now-retired pair with -s still re-synthesizes,
    excluding the retired excerpt (AC #6: link and synthesize paths agree).

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param linkage: The existing linkage fixture.
    :type linkage: LinkageAggregate
    :param link_dependencies: Mocked link-event dependencies.
    :type link_dependencies: dict
    '''

    # The existing pair is retired; it is the only linkage on the theme.
    linkage.retire(reason='Superseded.')
    link_dependencies['linkage_service'].list.side_effect = None
    link_dependencies['linkage_service'].list.return_value = [linkage]

    # Re-link the retired pair with the opt-in synthesis flag.
    result = DomainEvent.handle(
        LinkCitationToTheme,
        dependencies=link_dependencies,
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
        include_synthesis=True,
    )

    # No new linkage or count change, but synthesis still ran over an empty
    # active set -- the retired citation never reaches the synthesizer.
    link_dependencies['linkage_service'].save.assert_not_called()
    link_dependencies['theme_synthesis_service'].synthesize.assert_called_once_with(theme, [])
    link_dependencies['theme_service'].save.assert_called_once_with(theme)
    assert result is theme
    assert result.linkage_count == 0

# ** test: test_update_theme_sets_description_without_citations
def test_update_theme_sets_description_without_citations(theme):
    '''
    Editorial update writes synthesized_description with zero citations.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    '''

    # Theme service returns the existing theme; no citations are required.
    theme_service = mock.Mock(spec=ThemeService)
    theme_service.get.return_value = theme

    # Write the exact curated narrative via the CLI description alias.
    result = DomainEvent.handle(
        UpdateTheme,
        dependencies={
            'theme_service': theme_service,
            'activity_service': mock.Mock(spec=ActivityService),
        },
        id=THEME_ID,
        description=CURATED_DESCRIPTION,
    )

    # The stored text matches the provided narrative and the theme is saved.
    theme_service.save.assert_called_once_with(theme)
    assert result.synthesized_description == CURATED_DESCRIPTION
    assert result.linkage_count == 0

# ** test: test_update_theme_sets_name
def test_update_theme_sets_name(theme):
    '''
    Editorial update writes the theme name when provided.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    '''

    # Theme service returns the existing theme.
    theme_service = mock.Mock(spec=ThemeService)
    theme_service.get.return_value = theme

    # Rename the theme without touching the description.
    result = DomainEvent.handle(
        UpdateTheme,
        dependencies={
            'theme_service': theme_service,
            'activity_service': mock.Mock(spec=ActivityService),
        },
        id=THEME_ID,
        name='Renamed theme',
    )

    # Only the name changes; the curated description remains.
    assert result.name == 'Renamed theme'
    assert result.synthesized_description == CURATED_DESCRIPTION

# ** test: test_update_theme_missing_theme
def test_update_theme_missing_theme():
    '''
    Updating an unknown theme raises THEME_NOT_FOUND.
    '''

    # Theme service cannot resolve the requested id.
    theme_service = mock.Mock(spec=ThemeService)
    theme_service.get.return_value = None

    # Execute and expect THEME_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            UpdateTheme,
            dependencies={
                'theme_service': theme_service,
                'activity_service': mock.Mock(spec=ActivityService),
            },
            id='missing-theme',
            description=CURATED_DESCRIPTION,
        )

    # Assert the structured not-found error.
    assert exc_info.value.error_code == THEME_NOT_FOUND_ID

# ** test: test_resynthesize_theme_excludes_retired_linkages
def test_resynthesize_theme_excludes_retired_linkages(theme, citation, linkage):
    '''
    A retired linkage's excerpt never reaches the synthesizer.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param linkage: The linkage fixture, retired for this test.
    :type linkage: LinkageAggregate
    '''

    # Mock the four injected services used by ResynthesizeTheme.
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_synthesis_service = mock.Mock(spec=ThemeSynthesisService)

    # The theme's only linkage has been retired.
    linkage.retire(reason='Superseded.')
    theme_service.get.return_value = theme
    linkage_service.list.return_value = [linkage]
    citation_service.get.return_value = citation
    theme_synthesis_service.synthesize.return_value = ''

    # Re-synthesize on demand.
    DomainEvent.handle(
        ResynthesizeTheme,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
            'theme_synthesis_service': theme_synthesis_service,
            'activity_service': mock.Mock(spec=ActivityService),
        },
        id=THEME_ID,
    )

    # The synthesizer receives an empty citation set; nothing retired leaks in.
    theme_synthesis_service.synthesize.assert_called_once_with(theme, [])

# ** fixture: retirement_dependencies
@pytest.fixture
def retirement_dependencies(theme, citation, linkage) -> dict:
    '''
    Build mocked services for RetireLinkage / ReinstateLinkage.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param linkage: The existing linkage fixture.
    :type linkage: LinkageAggregate
    :return: Constructor dependencies for the retirement events.
    :rtype: dict
    '''

    # Mock each injected service with its interface contract.
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)

    # Resolve the sample theme, citation, and the existing linkage pair.
    theme_service.get.return_value = theme
    citation_service.get.return_value = citation
    linkage_service.list.return_value = [linkage]

    # Return the assembled dependency map.
    return {
        'theme_service': theme_service,
        'linkage_service': linkage_service,
        'citation_service': citation_service,
        'activity_service': mock.Mock(spec=ActivityService),
    }

# ** test: test_retire_linkage_marks_retired_and_moves_counts
def test_retire_linkage_marks_retired_and_moves_counts(theme, linkage, retirement_dependencies):
    '''
    Retiring an active linkage stamps it and moves the theme's counts.

    :param theme: The theme fixture, seeded with one active linkage.
    :type theme: ThemeAggregate
    :param linkage: The active linkage fixture.
    :type linkage: LinkageAggregate
    :param retirement_dependencies: Mocked retirement-event dependencies.
    :type retirement_dependencies: dict
    '''

    # The theme currently counts this linkage as active.
    theme.set_attribute('linkage_count', 1)

    # Retire the linkage with a reason.
    result = DomainEvent.handle(
        RetireLinkage,
        dependencies=retirement_dependencies,
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
        reason='Superseded by stronger corroboration.',
    )

    # The linkage is retired and saved; the counts move active -> retired.
    retirement_dependencies['linkage_service'].save.assert_called_once_with(linkage)
    retirement_dependencies['theme_service'].save.assert_called_once_with(theme)
    assert result.is_active() is False
    assert result.retirement_reason == 'Superseded by stronger corroboration.'
    assert theme.linkage_count == 0
    assert theme.retired_linkage_count == 1

# ** test: test_retire_linkage_is_idempotent
def test_retire_linkage_is_idempotent(theme, linkage, retirement_dependencies):
    '''
    Retiring an already-retired linkage does not restamp or raise.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param linkage: The linkage fixture, pre-retired for this test.
    :type linkage: LinkageAggregate
    :param retirement_dependencies: Mocked retirement-event dependencies.
    :type retirement_dependencies: dict
    '''

    # The linkage is already retired at a known timestamp.
    linkage.retire(reason='Original reason.')
    original_retired_at = linkage.retired_at
    theme.set_attribute('retired_linkage_count', 1)

    # Retire it again with a different reason.
    result = DomainEvent.handle(
        RetireLinkage,
        dependencies=retirement_dependencies,
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
        reason='A different reason.',
    )

    # No save, no restamp, no count change, and the original reason stands.
    retirement_dependencies['linkage_service'].save.assert_not_called()
    retirement_dependencies['theme_service'].save.assert_not_called()
    assert result is linkage
    assert result.retired_at == original_retired_at
    assert result.retirement_reason == 'Original reason.'
    assert theme.retired_linkage_count == 1

# ** test: test_retire_linkage_missing_linkage
def test_retire_linkage_missing_linkage(retirement_dependencies):
    '''
    Retiring a nonexistent pairing raises LINKAGE_NOT_FOUND.

    :param retirement_dependencies: Mocked retirement-event dependencies.
    :type retirement_dependencies: dict
    '''

    # No linkage exists between this citation and theme.
    retirement_dependencies['linkage_service'].list.return_value = []

    # Execute and expect LINKAGE_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            RetireLinkage,
            dependencies=retirement_dependencies,
            citation_id=CITATION_ID,
            theme_id=THEME_ID,
        )

    # Assert the structured not-found error.
    assert exc_info.value.error_code == LINKAGE_NOT_FOUND_ID

# ** test: test_reinstate_linkage_returns_to_active_and_moves_counts
def test_reinstate_linkage_returns_to_active_and_moves_counts(
        theme,
        linkage,
        retirement_dependencies,
    ):
    '''
    Reinstating a retired linkage clears its state and moves the counts.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param linkage: The linkage fixture, pre-retired for this test.
    :type linkage: LinkageAggregate
    :param retirement_dependencies: Mocked retirement-event dependencies.
    :type retirement_dependencies: dict
    '''

    # The linkage starts retired; the theme counts it as such.
    linkage.retire(reason='Superseded.')
    theme.set_attribute('retired_linkage_count', 1)

    # Reinstate the linkage.
    result = DomainEvent.handle(
        ReinstateLinkage,
        dependencies=retirement_dependencies,
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
    )

    # The linkage is active again; the counts move retired -> active.
    retirement_dependencies['linkage_service'].save.assert_called_once_with(linkage)
    retirement_dependencies['theme_service'].save.assert_called_once_with(theme)
    assert result.is_active() is True
    assert theme.linkage_count == 1
    assert theme.retired_linkage_count == 0

# ** test: test_reinstate_linkage_is_idempotent
def test_reinstate_linkage_is_idempotent(theme, linkage, retirement_dependencies):
    '''
    Reinstating an already-active linkage is a no-op.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param linkage: The already-active linkage fixture.
    :type linkage: LinkageAggregate
    :param retirement_dependencies: Mocked retirement-event dependencies.
    :type retirement_dependencies: dict
    '''

    # Reinstate an already-active linkage.
    result = DomainEvent.handle(
        ReinstateLinkage,
        dependencies=retirement_dependencies,
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
    )

    # No save and no count change.
    retirement_dependencies['linkage_service'].save.assert_not_called()
    retirement_dependencies['theme_service'].save.assert_not_called()
    assert result is linkage
    assert theme.linkage_count == 0

# ** test: test_reinstate_linkage_missing_linkage
def test_reinstate_linkage_missing_linkage(retirement_dependencies):
    '''
    Reinstating a nonexistent pairing raises LINKAGE_NOT_FOUND.

    :param retirement_dependencies: Mocked retirement-event dependencies.
    :type retirement_dependencies: dict
    '''

    # No linkage exists between this citation and theme.
    retirement_dependencies['linkage_service'].list.return_value = []

    # Execute and expect LINKAGE_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            ReinstateLinkage,
            dependencies=retirement_dependencies,
            citation_id=CITATION_ID,
            theme_id=THEME_ID,
        )

    # Assert the structured not-found error.
    assert exc_info.value.error_code == LINKAGE_NOT_FOUND_ID

# ** test: test_show_theme_lists_active_linkages_only_by_default
def test_show_theme_lists_active_linkages_only_by_default(theme, citation, linkage):
    '''
    theme show without --include-retired lists only active linkages.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param linkage: The linkage fixture, retired for this test.
    :type linkage: LinkageAggregate
    '''

    # The theme's only linkage is retired.
    linkage.retire(reason='Superseded.')
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_service.get.return_value = theme
    linkage_service.list.return_value = [linkage]
    citation_service.list.return_value = [citation]

    # Show without opting into retired linkages.
    result = DomainEvent.handle(
        ShowTheme,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
        },
        id=THEME_ID,
    )

    # No active citations, and retired_citations is left unset (None).
    assert result.citations == []
    assert result.retired_citations is None

# ** test: test_show_theme_include_retired_lists_retirement_details
def test_show_theme_include_retired_lists_retirement_details(theme, citation, linkage):
    '''
    theme show --include-retired lists retired linkages with timestamp/reason.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param linkage: The linkage fixture, retired for this test.
    :type linkage: LinkageAggregate
    '''

    # The theme's only linkage is retired.
    linkage.retire(reason='Superseded by stronger corroboration.')
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_service.get.return_value = theme
    linkage_service.list.return_value = [linkage]
    citation_service.list.return_value = [citation]

    # Show with --include-retired.
    result = DomainEvent.handle(
        ShowTheme,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
        },
        id=THEME_ID,
        include_retired=True,
    )

    # The retired citation view carries its provenance and retirement detail.
    assert result.citations == []
    assert len(result.retired_citations) == 1
    retired_view = result.retired_citations[0]
    assert retired_view.id == citation.id
    assert retired_view.excerpt == citation.excerpt
    assert retired_view.retired_at == linkage.retired_at
    assert retired_view.retirement_reason == 'Superseded by stronger corroboration.'

# ** test: test_show_theme_bulk_load_preserves_order_and_fields
@pytest.mark.parametrize('citation_count', [7, 8])
def test_show_theme_bulk_load_preserves_order_and_fields(theme, citation_count):
    '''
    Bulk loading preserves the full response in linkage order.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation_count: The number of active linked citations.
    :type citation_count: int
    '''

    # Provide fully populated citations in reverse table order.
    citations = [
        CitationAggregate(
            id=f'citation-{index}',
            source_id=f'source-{index}',
            locator=f'{index + 1}-{index + 1}',
            excerpt=f'Exact excerpt {index}: évidence.',
            context_note=f'Exact context {index}.',
            title=f'Exact title {index}',
            created_at=1700000000 + index,
        )
        for index in range(citation_count)
    ]
    linkages = [
        LinkageAggregate(citation_id=citation.id, theme_id=theme.id)
        for citation in citations
    ]
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_service.get.return_value = theme
    linkage_service.list.return_value = linkages
    citation_service.list.return_value = list(reversed(citations))
    original_theme = theme.model_dump()

    # Show without invoking any per-citation lookup.
    result = DomainEvent.handle(
        ShowTheme,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
        },
        id=theme.id,
    )

    # Order and citation fields survive. Weight is a linkage field, not citation identity.
    assert [item.model_dump(exclude={'relevancy_weight'}) for item in result.citations] == [
        citation.model_dump() for citation in citations
    ]
    assert result.model_dump(
        exclude={'citations', 'retired_citations'},
    ) == original_theme
    assert result.retired_citations is None
    assert theme.model_dump() == original_theme
    linkage_service.list.assert_called_once_with(theme_id=theme.id)
    citation_service.list.assert_called_once_with(ids=[item.id for item in citations])
    citation_service.get.assert_not_called()
    citation_service.save.assert_not_called()
    linkage_service.save.assert_not_called()
    theme_service.save.assert_not_called()

# ** test: test_show_theme_empty_skips_citation_service
def test_show_theme_empty_skips_citation_service(theme):
    '''
    A theme with no linkages never opens the citation service.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    '''

    # Set up an existing theme without evidence.
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_service.get.return_value = theme
    linkage_service.list.return_value = []

    # Show the empty theme with an explicitly empty retirement view.
    result = DomainEvent.handle(
        ShowTheme,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
        },
        id=theme.id,
        include_retired=True,
    )

    # Neither citation read path is needed.
    assert result.citations == []
    assert result.retired_citations == []
    citation_service.list.assert_not_called()
    citation_service.get.assert_not_called()

# ** test: test_show_theme_missing_theme_skips_evidence
def test_show_theme_missing_theme_skips_evidence():
    '''
    A missing theme raises before reading linkage or citation tables.
    '''

    # No theme is registered for the requested identifier.
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_service.get.return_value = None

    # The original structured error remains the public outcome.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            ShowTheme,
            dependencies={
                'theme_service': theme_service,
                'linkage_service': linkage_service,
                'citation_service': citation_service,
            },
            id='missing-theme',
        )

    # Missing themes cannot trigger the bulk read.
    assert exc_info.value.error_code == THEME_NOT_FOUND_ID
    linkage_service.list.assert_not_called()
    citation_service.list.assert_not_called()
    citation_service.get.assert_not_called()

# ** test: test_show_theme_missing_and_repeated_citations
def test_show_theme_missing_and_repeated_citations(theme, citation):
    '''
    Missing rows are skipped and repeated references retain the first row.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    '''

    # Duplicate stored IDs retain get's first-match behavior.
    duplicate = citation.model_copy(update={'excerpt': 'Not the first row.'})
    active = LinkageAggregate(citation_id=citation.id, theme_id=theme.id)
    retired = LinkageAggregate(citation_id=citation.id, theme_id=theme.id)
    retired.retire(reason='Retain provenance.')
    missing = LinkageAggregate(citation_id='missing', theme_id=theme.id)
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_service.get.return_value = theme
    linkage_service.list.return_value = [active, missing, active, retired]
    citation_service.list.return_value = [citation, duplicate]

    # Preserve each linkage's position and its retirement state.
    result = DomainEvent.handle(
        ShowTheme,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
        },
        id=theme.id,
        include_retired=True,
    )

    # Active repetition survives, the missing row vanishes, and retirement stays.
    assert [item.model_dump(exclude={'relevancy_weight'}) for item in result.citations] == [
        citation.model_dump(),
        citation.model_dump(),
    ]
    assert len(result.retired_citations) == 1
    retired_view = result.retired_citations[0]
    assert retired_view.model_dump(
        exclude={'retired_at', 'retirement_reason', 'relevancy_weight'},
    ) == citation.model_dump()
    assert retired_view.retired_at == retired.retired_at
    assert retired_view.retirement_reason == 'Retain provenance.'
    citation_service.get.assert_not_called()
    assert citation_service.list.call_count == 1

# ** test_int: test_show_theme_reads_selected_citation_arrays_only
@pytest.mark.parametrize('citation_count', [7, 8])
def test_show_theme_reads_selected_citation_arrays_only(tmp_path, theme, citation_count):
    '''
    A multi-link show does not scan a citations table or an unlinked array.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation_count: The number of linked citations.
    :type citation_count: int
    '''

    # Persist linked citations plus one unlinked citation in an isolated store.
    h5_file = str(tmp_path / 'theme-show.h5')
    theme_service = ThemeH5Repository(h5_file=h5_file)
    linkage_service = LinkageH5Repository(h5_file=h5_file)
    citation_service = CitationH5Repository(h5_file=h5_file)
    theme_service.save(theme)
    expected = []
    for index in range(citation_count):
        citation = CitationAggregate(
            id=f'citation-{index}',
            source_id='source-1',
            locator=f'{index + 1}-{index + 1}',
            excerpt=f'Exact evidence {index}.',
            context_note=f'Exact context {index}.',
            title=f'Exact title {index}',
            created_at=1700000000 + index,
        )
        citation_service.save(citation)
        linkage_service.save(LinkageAggregate(
            citation_id=citation.id,
            theme_id=theme.id,
        ))
        expected.append(citation.model_dump())
    citation_service.save(CitationAggregate(
        id='unlinked-citation',
        source_id='source-1',
        locator='99-99',
        excerpt='Do not read this excerpt.',
        context_note='Do not read this note.',
    ))

    # Require read-only access and instrument the actual HDF5 boundary.
    theme_service.mode = 'r'
    linkage_service.mode = 'r'
    citation_service.mode = 'r'
    with mock.patch.object(
            H5Client,
            'read_rows',
            autospec=True,
            side_effect=H5Client.read_rows,
        ) as read_rows, mock.patch.object(
            H5Client,
            'get_array',
            autospec=True,
            side_effect=H5Client.get_array,
        ) as get_array:
        result = DomainEvent.handle(
            ShowTheme,
            dependencies={
                'theme_service': theme_service,
                'linkage_service': linkage_service,
                'citation_service': citation_service,
            },
            id=theme.id,
        )

    # Linkages are still one table read. Citation text is selected arrays only.
    paths = [call.args[1] for call in read_rows.call_args_list]
    array_paths = [call.args[1] for call in get_array.call_args_list]
    assert paths == [LINKAGES_TABLE_PATH]
    assert CITATIONS_NODE_PATH not in paths
    assert array_paths
    assert all('unlinked-citation' not in path for path in array_paths)
    assert [
        citation.model_dump(exclude={'relevancy_weight'})
        for citation in result.citations
    ] == expected
    assert result.synthesized_description == theme.synthesized_description

# ** test: test_resynthesize_theme_reloads_linkages
def test_resynthesize_theme_reloads_linkages(theme, citation, linkage):
    '''
    Explicit synthesize reloads all linked citations and updates the text.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param linkage: The linkage fixture.
    :type linkage: LinkageAggregate
    '''

    # Mock the four injected services used by ResynthesizeTheme.
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_synthesis_service = mock.Mock(spec=ThemeSynthesisService)

    # The theme already has a curated description and one stored linkage.
    theme_service.get.return_value = theme
    linkage_service.list.return_value = [linkage]
    citation_service.list.return_value = [citation]
    theme_synthesis_service.synthesize.return_value = SYNTHESIZED_DESCRIPTION

    # Re-synthesize on demand.
    result = DomainEvent.handle(
        ResynthesizeTheme,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
            'theme_synthesis_service': theme_synthesis_service,
            'activity_service': mock.Mock(spec=ActivityService),
        },
        id=THEME_ID,
    )

    # Linkages are reloaded once. Synthesis does not get each citation.
    linkage_service.list.assert_called_once_with(theme_id=THEME_ID)
    citation_service.list.assert_called_once_with(ids=[citation.id])
    citation_service.get.assert_not_called()
    theme_synthesis_service.synthesize.assert_called_once_with(theme, [citation])
    theme_service.save.assert_called_once_with(theme)
    assert result.synthesized_description == SYNTHESIZED_DESCRIPTION

# ** test: test_resynthesize_theme_missing_theme
def test_resynthesize_theme_missing_theme():
    '''
    Synthesizing an unknown theme raises THEME_NOT_FOUND.
    '''

    # Theme service cannot resolve the requested id.
    theme_service = mock.Mock(spec=ThemeService)
    theme_service.get.return_value = None

    # Execute and expect THEME_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            ResynthesizeTheme,
            dependencies={
                'theme_service': theme_service,
                'linkage_service': mock.Mock(spec=LinkageService),
                'citation_service': mock.Mock(spec=CitationService),
                'theme_synthesis_service': mock.Mock(spec=ThemeSynthesisService),
                'activity_service': mock.Mock(spec=ActivityService),
            },
            id='missing-theme',
        )

    # Assert the structured not-found error.
    assert exc_info.value.error_code == THEME_NOT_FOUND_ID

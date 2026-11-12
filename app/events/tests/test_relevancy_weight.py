"""Lit Review Linkage Relevancy Weight Event Tests"""

# *** imports

# ** core
import json
from pathlib import Path
from unittest import mock

# ** infra
import pytest

# ** app
from tiferet import DomainEvent
from tiferet.assets import TiferetError
from tiferet.repos.feature import FeatureConfigRepository

from app.domain.activity import (
    LINKAGE_WEIGHT_CLEARED_ACTION,
    LINKAGE_WEIGHT_SET_ACTION,
)
from app.events.theme import (
    LINKAGE_NOT_FOUND_ID,
    RELEVANCY_WEIGHT_OUT_OF_RANGE_ID,
    ClearLinkageRelevancyWeight,
    LinkCitationToTheme,
    ListThemes,
    ReinstateLinkage,
    ResynthesizeTheme,
    RetireLinkage,
    SetLinkageRelevancyWeight,
    ShowTheme,
)
from app.interfaces.activity import ActivityService
from app.interfaces.citation import CitationService
from app.interfaces.linkage import LinkageService
from app.interfaces.source import SourceService
from app.interfaces.synthesis import ThemeSynthesisService
from app.interfaces.theme import ThemeService
from app.mappers.citation import CitationAggregate
from app.mappers.linkage import LinkageAggregate
from app.mappers.theme import ThemeAggregate
from app.utils.synthesis import NaiveThemeSynthesizer

# *** constants

# ** constant: theme_id
THEME_ID = 'universal-ir-abstractions'

# ** constant: citation_id
CITATION_ID = '02a49f90-0ff1-48cb-916a-fbc92f9712dd'

# ** constant: curated_description
CURATED_DESCRIPTION = 'Custom narrative synthesis'

# *** fixtures

# ** fixture: theme
@pytest.fixture
def theme() -> ThemeAggregate:
    '''
    Build a theme whose description must survive a weight change.

    :return: A theme with curated synthesis text.
    :rtype: ThemeAggregate
    '''

    # Return a theme that weight commands must not rewrite.
    return ThemeAggregate(
        id=THEME_ID,
        name='Universal IR abstractions',
        synthesized_description=CURATED_DESCRIPTION,
        linkage_count=1,
        retired_linkage_count=0,
    )

# ** fixture: citation
@pytest.fixture
def citation() -> CitationAggregate:
    '''
    Build the citation attached to the sample linkage.

    :return: A citation for the weight tests.
    :rtype: CitationAggregate
    '''

    # Return the citation named by the linkage fixture.
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
    Build an existing unweighted linkage.

    :return: A linkage for the sample citation and theme.
    :rtype: LinkageAggregate
    '''

    # Return the pair the weight commands address.
    return LinkageAggregate(citation_id=CITATION_ID, theme_id=THEME_ID)

# ** fixture: weight_dependencies
@pytest.fixture
def weight_dependencies(theme, citation, linkage) -> dict:
    '''
    Build mocked services for set and clear weight.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param linkage: The existing linkage fixture.
    :type linkage: LinkageAggregate
    :return: Constructor dependencies for the weight events.
    :rtype: dict
    '''

    # Resolve the sample theme, citation, and existing pair.
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
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

# *** tests

# ** test: test_weight_features_match_cli_ids
def test_weight_features_match_cli_ids():
    '''
    CLI theme weight and theme clear-weight resolve to the wired features.
    '''

    # Load the checked-in feature catalog from the repository root.
    feature_config = Path(__file__).resolve().parents[3] / 'app' / 'assets' / 'feature.yml'
    feature_repo = FeatureConfigRepository(feature_config=str(feature_config))

    # Hyphenated clear-weight normalises to theme.clear_weight.
    assert feature_repo.get('theme.weight') is not None
    assert feature_repo.get('theme.clear_weight') is not None

# ** test: test_link_citation_to_theme_is_born_unweighted
def test_link_citation_to_theme_is_born_unweighted(theme):
    '''
    A new linkage is unweighted even if a weight is passed beside the link.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    '''

    # Mock a new pair. An extra weight kwarg must not stick.
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_synthesis_service = mock.Mock(spec=ThemeSynthesisService)
    theme_service.get.return_value = theme
    citation_service.get.return_value = CitationAggregate(
        id=CITATION_ID,
        source_id='source-1',
        locator='4-4',
        excerpt='Operations are the unit.',
    )
    linkage_service.list.return_value = []
    DomainEvent.handle(
        LinkCitationToTheme,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
            'theme_synthesis_service': theme_synthesis_service,
            'activity_service': mock.Mock(spec=ActivityService),
        },
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
        weight=80,
    )

    # The saved row is unjudged, and synthesis did not run.
    saved = linkage_service.save.call_args[0][0]
    assert saved.relevancy_weight is None
    theme_synthesis_service.synthesize.assert_not_called()
    assert theme.synthesized_description == CURATED_DESCRIPTION

# ** test: test_set_relevancy_weight_on_existing_pair
def test_set_relevancy_weight_on_existing_pair(theme, linkage, weight_dependencies):
    '''
    Setting a weight writes the linkage only and records the field name.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param linkage: The existing linkage fixture.
    :type linkage: LinkageAggregate
    :param weight_dependencies: Mocked pair dependencies.
    :type weight_dependencies: dict
    '''

    # Set a judged weight on the existing pair.
    result = DomainEvent.handle(
        SetLinkageRelevancyWeight,
        dependencies=weight_dependencies,
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
        weight=73,
    )

    # The linkage changes; the description and retirement do not.
    weight_dependencies['linkage_service'].save.assert_called_once_with(linkage)
    weight_dependencies['theme_service'].save.assert_not_called()
    assert result.relevancy_weight == 73
    assert result.is_active() is True
    assert theme.synthesized_description == CURATED_DESCRIPTION

    # Activity names the field and never stores the number.
    activity = weight_dependencies['activity_service']
    activity.record.assert_called_once()
    (entry,), _ = activity.record.call_args
    assert entry.action == LINKAGE_WEIGHT_SET_ACTION
    assert entry.changed_fields == ['relevancy_weight']
    assert 73 not in entry.model_dump().values()

# ** test: test_set_relevancy_weight_noop_records_nothing
def test_set_relevancy_weight_noop_records_nothing(linkage, weight_dependencies):
    '''
    Setting the same weight writes nothing and records no activity.

    :param linkage: The linkage fixture, already weighted.
    :type linkage: LinkageAggregate
    :param weight_dependencies: Mocked pair dependencies.
    :type weight_dependencies: dict
    '''

    # The pair already carries this judgment.
    linkage.set_relevancy_weight(73)

    # Repeat the same set.
    result = DomainEvent.handle(
        SetLinkageRelevancyWeight,
        dependencies=weight_dependencies,
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
        weight=73,
    )

    # No write and no activity.
    weight_dependencies['linkage_service'].save.assert_not_called()
    weight_dependencies['activity_service'].record.assert_not_called()
    assert result.relevancy_weight == 73

# ** test: test_clear_relevancy_weight_on_existing_pair
def test_clear_relevancy_weight_on_existing_pair(linkage, weight_dependencies):
    '''
    Clearing a weight returns the mapping to unjudged and records the field name.

    :param linkage: The linkage fixture, already weighted.
    :type linkage: LinkageAggregate
    :param weight_dependencies: Mocked pair dependencies.
    :type weight_dependencies: dict
    '''

    # Start from a judged mapping.
    linkage.set_relevancy_weight(73)

    # Clear it.
    result = DomainEvent.handle(
        ClearLinkageRelevancyWeight,
        dependencies=weight_dependencies,
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
    )

    # The linkage is unjudged, and activity does not store the old number.
    weight_dependencies['linkage_service'].save.assert_called_once_with(linkage)
    assert result.relevancy_weight is None
    (entry,), _ = weight_dependencies['activity_service'].record.call_args
    assert entry.action == LINKAGE_WEIGHT_CLEARED_ACTION
    assert entry.changed_fields == ['relevancy_weight']
    assert 73 not in entry.model_dump().values()

# ** test: test_clear_relevancy_weight_noop_records_nothing
def test_clear_relevancy_weight_noop_records_nothing(linkage, weight_dependencies):
    '''
    Clearing an already-absent weight writes nothing and records no activity.

    :param linkage: The unweighted linkage fixture.
    :type linkage: LinkageAggregate
    :param weight_dependencies: Mocked pair dependencies.
    :type weight_dependencies: dict
    '''

    # Clear an unjudged mapping.
    result = DomainEvent.handle(
        ClearLinkageRelevancyWeight,
        dependencies=weight_dependencies,
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
    )

    # No write and no activity.
    weight_dependencies['linkage_service'].save.assert_not_called()
    weight_dependencies['activity_service'].record.assert_not_called()
    assert result.relevancy_weight is None

# ** test: test_weight_commands_missing_pair
@pytest.mark.parametrize('event', [SetLinkageRelevancyWeight, ClearLinkageRelevancyWeight])
def test_weight_commands_missing_pair(event, weight_dependencies):
    '''
    Weight commands do not create a linkage.

    :param event: The set or clear event.
    :type event: type
    :param weight_dependencies: Mocked pair dependencies.
    :type weight_dependencies: dict
    '''

    # No linkage exists between this citation and theme.
    weight_dependencies['linkage_service'].list.return_value = []

    # Execute and expect LINKAGE_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            event,
            dependencies=weight_dependencies,
            citation_id=CITATION_ID,
            theme_id=THEME_ID,
            weight=40,
        )

    # Nothing was written.
    assert exc_info.value.error_code == LINKAGE_NOT_FOUND_ID
    weight_dependencies['linkage_service'].save.assert_not_called()

# ** test: test_set_relevancy_weight_out_of_range
@pytest.mark.parametrize('weight', [0, 101, -1, True])
def test_set_relevancy_weight_out_of_range(weight, weight_dependencies):
    '''
    An out-of-range weight raises RELEVANCY_WEIGHT_OUT_OF_RANGE.

    :param weight: The rejected weight.
    :type weight: object
    :param weight_dependencies: Mocked pair dependencies.
    :type weight_dependencies: dict
    '''

    # The pair exists; the judgment does not.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            SetLinkageRelevancyWeight,
            dependencies=weight_dependencies,
            citation_id=CITATION_ID,
            theme_id=THEME_ID,
            weight=weight,
        )

    # The structured range error writes nothing.
    assert exc_info.value.error_code == RELEVANCY_WEIGHT_OUT_OF_RANGE_ID
    weight_dependencies['linkage_service'].save.assert_not_called()
    weight_dependencies['activity_service'].record.assert_not_called()

# ** test: test_show_theme_carries_weight_in_linkage_order
def test_show_theme_carries_weight_in_linkage_order(theme):
    '''
    theme show carries the integer or null in linkage order, including retired.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    '''

    # Two active linkages and one retired, not ordered by weight.
    high = CitationAggregate(
        id='high',
        source_id='source-1',
        locator='1-1',
        excerpt='High excerpt.',
    )
    absent = CitationAggregate(
        id='absent',
        source_id='source-1',
        locator='2-2',
        excerpt='Unjudged excerpt.',
    )
    retired_citation = CitationAggregate(
        id='retired',
        source_id='source-1',
        locator='3-3',
        excerpt='Retired excerpt.',
    )
    high_link = LinkageAggregate(citation_id='high', theme_id=theme.id)
    high_link.set_relevancy_weight(90)
    absent_link = LinkageAggregate(citation_id='absent', theme_id=theme.id)
    retired_link = LinkageAggregate(citation_id='retired', theme_id=theme.id)
    retired_link.set_relevancy_weight(7)
    retired_link.retire(reason='Displaced.')
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_service.get.return_value = theme
    linkage_service.list.return_value = [high_link, absent_link, retired_link]
    citation_service.list.return_value = [absent, retired_citation, high]

    # Show active and retired views.
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

    # Order stays linkage order. Absent is null, never 0.
    assert [item.id for item in result.citations] == ['high', 'absent']
    assert [item.relevancy_weight for item in result.citations] == [90, None]
    assert json.loads(result.citations[1].model_dump_json())['relevancy_weight'] is None
    assert '"relevancy_weight":null' in result.citations[1].model_dump_json()
    assert result.retired_citations[0].relevancy_weight == 7
    assert result.retired_citations[0].relevancy_weight != 0

# ** test: test_list_themes_has_no_weight
def test_list_themes_has_no_weight(theme):
    '''
    theme list stays theme-level and does not roll up weights.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    '''

    # List does not consult linkages.
    theme_service = mock.Mock(spec=ThemeService)
    theme_service.list.return_value = [theme]
    result = DomainEvent.handle(
        ListThemes,
        dependencies={'theme_service': theme_service},
    )

    # No weight, sum, or average on the theme row.
    dumped = result[0].model_dump()
    assert 'relevancy_weight' not in dumped
    assert not any('weight' in key or 'sum' in key or 'average' in key for key in dumped)

# ** test: test_weighted_and_unweighted_linkages_synthesize_the_same
def test_weighted_and_unweighted_linkages_synthesize_the_same(theme):
    '''
    A weighted linkage and an unweighted one produce the same synthesis.

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    '''

    # Newest linkage is weighted; the older one is not.
    older = CitationAggregate(
        id='older',
        source_id='source-1',
        locator='1-1',
        excerpt='Older excerpt.',
    )
    newer = CitationAggregate(
        id='newer',
        source_id='source-1',
        locator='2-2',
        excerpt='Newer excerpt.',
    )
    older_link = LinkageAggregate(citation_id='older', theme_id=theme.id)
    newer_link = LinkageAggregate(citation_id='newer', theme_id=theme.id)
    newer_link.set_relevancy_weight(80)
    citations = {'older': older, 'newer': newer}
    source_service = mock.Mock(spec=SourceService)
    source = mock.Mock()
    source.authors = [mock.Mock(display_name='Lattner')]
    source.year = 2020
    source_service.get.return_value = source
    synthesizer = NaiveThemeSynthesizer(source_service=source_service)
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_service.get.return_value = theme
    linkage_service.list.return_value = [older_link, newer_link]
    citation_service.get.side_effect = lambda citation_id: citations[citation_id]
    dependencies = {
        'theme_service': theme_service,
        'linkage_service': linkage_service,
        'citation_service': citation_service,
        'theme_synthesis_service': synthesizer,
        'activity_service': mock.Mock(spec=ActivityService),
    }

    # Synthesize the mixed set, then the same set with the weight cleared.
    weighted = DomainEvent.handle(
        ResynthesizeTheme,
        dependencies=dependencies,
        id=theme.id,
    )
    newer_link.clear_relevancy_weight()
    theme.set_attribute('synthesized_description', CURATED_DESCRIPTION)
    unweighted = DomainEvent.handle(
        ResynthesizeTheme,
        dependencies=dependencies,
        id=theme.id,
    )

    # Newest-linkage-first collage, independent of the weight.
    expected = 'Lattner (2020): Newer excerpt.\nLattner (2020): Older excerpt.'
    assert weighted.synthesized_description == expected
    assert unweighted.synthesized_description == expected

# ** test: test_retire_and_reinstate_keep_weight_through_events
def test_retire_and_reinstate_keep_weight_through_events(linkage, weight_dependencies):
    '''
    Retire and reinstate do not clear a recorded weight.

    :param linkage: The linkage fixture.
    :type linkage: LinkageAggregate
    :param weight_dependencies: Mocked pair dependencies.
    :type weight_dependencies: dict
    '''

    # Judge the mapping before retiring it.
    linkage.set_relevancy_weight(15)

    # Retire, then reinstate.
    retired = DomainEvent.handle(
        RetireLinkage,
        dependencies=weight_dependencies,
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
        reason='Displaced.',
    )
    reinstated = DomainEvent.handle(
        ReinstateLinkage,
        dependencies=weight_dependencies,
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
    )

    # The weight survives both acts.
    assert retired.relevancy_weight == 15
    assert reinstated.relevancy_weight == 15
    assert reinstated.is_active() is True

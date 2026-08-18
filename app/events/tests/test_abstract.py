"""Lit Review Abstract Event Tests"""

# *** imports

# ** infra
import pytest
from unittest import mock

# ** app
from tiferet import DomainEvent
from tiferet.assets import TiferetError

from app.events.abstract import (
    ABSTRACT_NOT_FOUND_ID,
    AddAbstract,
    LinkThemeToAbstract,
    SynthesizeAbstract,
    UpdateAbstract,
)
from app.events.theme import THEME_NOT_FOUND_ID
from app.interfaces.abstract import AbstractService
from app.interfaces.synthesis import AbstractSynthesisService
from app.interfaces.theme import ThemeService
from app.mappers.abstract import AbstractAggregate
from app.mappers.theme import ThemeAggregate

# *** constants

# ** constant: abstract_id
ABSTRACT_ID = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'

# ** constant: theme_id
THEME_ID = 'universal-ir-abstractions'

# ** constant: curated_body
CURATED_BODY = 'This paper argues that multi-level IR is the unit of reuse.'

# ** constant: synthesized_body
SYNTHESIZED_BODY = 'Universal IR abstractions: Operations are the unit.'

# *** fixtures

# ** fixture: abstract
@pytest.fixture
def abstract() -> AbstractAggregate:
    '''
    Build an abstract aggregate with curated body text.

    :return: An abstract with an existing body.
    :rtype: AbstractAggregate
    '''

    # Return an abstract whose body must survive a default link.
    return AbstractAggregate(
        id=ABSTRACT_ID,
        name='Multi-level IR argument',
        body=CURATED_BODY,
    )

# ** fixture: theme
@pytest.fixture
def theme() -> ThemeAggregate:
    '''
    Build a theme aggregate to join to an abstract.

    :return: A theme with a synthesized description.
    :rtype: ThemeAggregate
    '''

    # Return a theme with the identifiers used by the link tests.
    return ThemeAggregate(
        id=THEME_ID,
        name='Universal IR abstractions',
        synthesized_description='Operations are the unit.',
        linkage_count=1,
    )

# ** fixture: link_dependencies
@pytest.fixture
def link_dependencies(abstract, theme) -> dict:
    '''
    Build mocked services for LinkThemeToAbstract.

    :param abstract: The abstract fixture.
    :type abstract: AbstractAggregate
    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :return: Constructor dependencies for the link event.
    :rtype: dict
    '''

    # Mock each injected service with its interface contract.
    abstract_service = mock.Mock(spec=AbstractService)
    theme_service = mock.Mock(spec=ThemeService)
    abstract_synthesis_service = mock.Mock(spec=AbstractSynthesisService)

    # Resolve the sample abstract and theme.
    abstract_service.get.return_value = abstract
    theme_service.get.return_value = theme
    abstract_synthesis_service.synthesize.return_value = SYNTHESIZED_BODY

    # Return the assembled dependency map.
    return {
        'abstract_service': abstract_service,
        'theme_service': theme_service,
        'abstract_synthesis_service': abstract_synthesis_service,
    }

# *** tests

# ** test: test_add_abstract_creates_empty_body
def test_add_abstract_creates_empty_body():
    '''
    Adding an abstract by name creates an empty body and zero theme_count.
    '''

    # Abstract service persists whatever aggregate the event constructs.
    abstract_service = mock.Mock(spec=AbstractService)

    # Add an abstract with only a name.
    result = DomainEvent.handle(
        AddAbstract,
        dependencies={'abstract_service': abstract_service},
        name='Multi-level IR argument',
    )

    # The new brief is empty and has no themes; it is saved.
    abstract_service.save.assert_called_once()
    assert result.name == 'Multi-level IR argument'
    assert result.body == ''
    assert result.theme_count == 0
    assert result.themes == []

# ** test: test_update_abstract_sets_body_without_themes
def test_update_abstract_sets_body_without_themes(abstract):
    '''
    Editorial update writes body with zero themes required.

    :param abstract: The abstract fixture.
    :type abstract: AbstractAggregate
    '''

    # Abstract service returns the existing abstract; no themes are required.
    abstract_service = mock.Mock(spec=AbstractService)
    abstract_service.get.return_value = abstract

    # Write the exact curated brief.
    result = DomainEvent.handle(
        UpdateAbstract,
        dependencies={'abstract_service': abstract_service},
        id=ABSTRACT_ID,
        body=CURATED_BODY,
    )

    # The stored text matches the provided brief and the abstract is saved.
    abstract_service.save.assert_called_once_with(abstract)
    assert result.body == CURATED_BODY
    assert result.theme_count == 0

# ** test: test_link_theme_to_abstract_default_preserves_body
def test_link_theme_to_abstract_default_preserves_body(
        abstract,
        link_dependencies,
    ):
    '''
    Default linking creates the join without rewriting the body.

    :param abstract: The abstract fixture.
    :type abstract: AbstractAggregate
    :param link_dependencies: Mocked link-event dependencies.
    :type link_dependencies: dict
    '''

    # Link without the opt-in synthesis flag.
    result = DomainEvent.handle(
        LinkThemeToAbstract,
        dependencies=link_dependencies,
        id=ABSTRACT_ID,
        theme_id=THEME_ID,
    )

    # The owned join is saved and the count increments; the curated text stays.
    link_dependencies['abstract_service'].save.assert_called_once_with(abstract)
    link_dependencies['abstract_synthesis_service'].synthesize.assert_not_called()
    assert result.theme_count == 1
    assert result.themes[0].theme_id == THEME_ID
    assert result.body == CURATED_BODY

# ** test: test_link_theme_to_abstract_is_idempotent
def test_link_theme_to_abstract_is_idempotent(abstract, link_dependencies):
    '''
    Re-linking an existing pair returns the abstract without mutation.

    :param abstract: The abstract fixture.
    :type abstract: AbstractAggregate
    :param link_dependencies: Mocked link-event dependencies.
    :type link_dependencies: dict
    '''

    # The abstract already owns this theme join.
    abstract.add_theme(THEME_ID)

    # Re-link the same pair.
    result = DomainEvent.handle(
        LinkThemeToAbstract,
        dependencies=link_dependencies,
        id=ABSTRACT_ID,
        theme_id=THEME_ID,
    )

    # No save, no synthesis, and the curated text remains.
    link_dependencies['abstract_service'].save.assert_not_called()
    link_dependencies['abstract_synthesis_service'].synthesize.assert_not_called()
    assert result is abstract
    assert result.body == CURATED_BODY
    assert result.theme_count == 1

# ** test: test_link_theme_to_abstract_include_synthesis_rewrites_body
def test_link_theme_to_abstract_include_synthesis_rewrites_body(
        abstract,
        theme,
        link_dependencies,
    ):
    '''
    Opt-in linking re-synthesizes from the full joined theme set.

    :param abstract: The abstract fixture.
    :type abstract: AbstractAggregate
    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param link_dependencies: Mocked link-event dependencies.
    :type link_dependencies: dict
    '''

    # Link with include_synthesis so the injected synthesizer runs.
    result = DomainEvent.handle(
        LinkThemeToAbstract,
        dependencies=link_dependencies,
        id=ABSTRACT_ID,
        theme_id=THEME_ID,
        include_synthesis=True,
    )

    # The synthesizer receives the full theme set and the body updates.
    link_dependencies['abstract_synthesis_service'].synthesize.assert_called_once()
    args, _kwargs = link_dependencies['abstract_synthesis_service'].synthesize.call_args
    assert args[0] is abstract
    assert args[1] == [theme]
    assert result.theme_count == 1
    assert result.body == SYNTHESIZED_BODY

# ** test: test_synthesize_abstract_reloads_joins
def test_synthesize_abstract_reloads_joins(abstract, theme):
    '''
    Explicit synthesize reloads all joined themes and updates the body.

    :param abstract: The abstract fixture.
    :type abstract: AbstractAggregate
    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    '''

    # The abstract already owns one theme join.
    abstract.add_theme(THEME_ID)

    # Mock the three injected services used by SynthesizeAbstract.
    abstract_service = mock.Mock(spec=AbstractService)
    theme_service = mock.Mock(spec=ThemeService)
    abstract_synthesis_service = mock.Mock(spec=AbstractSynthesisService)

    # The abstract already has a curated body and one owned join.
    abstract_service.get.return_value = abstract
    theme_service.get.return_value = theme
    abstract_synthesis_service.synthesize.return_value = SYNTHESIZED_BODY

    # Re-synthesize on demand.
    result = DomainEvent.handle(
        SynthesizeAbstract,
        dependencies={
            'abstract_service': abstract_service,
            'theme_service': theme_service,
            'abstract_synthesis_service': abstract_synthesis_service,
        },
        id=ABSTRACT_ID,
    )

    # Owned joins are resolved, the synthesizer runs, and the body updates.
    theme_service.get.assert_called_once_with(THEME_ID)
    abstract_synthesis_service.synthesize.assert_called_once_with(abstract, [theme])
    abstract_service.save.assert_called_once_with(abstract)
    assert result.body == SYNTHESIZED_BODY

# ** test: test_link_theme_to_abstract_missing_abstract
def test_link_theme_to_abstract_missing_abstract(link_dependencies):
    '''
    Linking to an unknown abstract raises ABSTRACT_NOT_FOUND.

    :param link_dependencies: Mocked link-event dependencies.
    :type link_dependencies: dict
    '''

    # The abstract service cannot resolve the requested id.
    link_dependencies['abstract_service'].get.return_value = None

    # Execute and expect ABSTRACT_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            LinkThemeToAbstract,
            dependencies=link_dependencies,
            id=ABSTRACT_ID,
            theme_id=THEME_ID,
        )

    # Assert the structured not-found error and that nothing was saved.
    assert exc_info.value.error_code == ABSTRACT_NOT_FOUND_ID
    link_dependencies['abstract_service'].save.assert_not_called()

# ** test: test_link_theme_to_abstract_missing_theme
def test_link_theme_to_abstract_missing_theme(abstract, link_dependencies):
    '''
    Linking an unknown theme raises THEME_NOT_FOUND.

    :param abstract: The abstract fixture.
    :type abstract: AbstractAggregate
    :param link_dependencies: Mocked link-event dependencies.
    :type link_dependencies: dict
    '''

    # The theme service cannot resolve the requested id.
    link_dependencies['theme_service'].get.return_value = None

    # Execute and expect THEME_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            LinkThemeToAbstract,
            dependencies=link_dependencies,
            id=ABSTRACT_ID,
            theme_id=THEME_ID,
        )

    # Assert the structured not-found error and that no join was written.
    assert exc_info.value.error_code == THEME_NOT_FOUND_ID
    link_dependencies['abstract_service'].save.assert_not_called()
    assert abstract.theme_count == 0

# ** test: test_update_abstract_missing_abstract
def test_update_abstract_missing_abstract():
    '''
    Updating an unknown abstract raises ABSTRACT_NOT_FOUND.
    '''

    # Abstract service cannot resolve the requested id.
    abstract_service = mock.Mock(spec=AbstractService)
    abstract_service.get.return_value = None

    # Execute and expect ABSTRACT_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            UpdateAbstract,
            dependencies={'abstract_service': abstract_service},
            id='missing-abstract',
            body=CURATED_BODY,
        )

    # Assert the structured not-found error.
    assert exc_info.value.error_code == ABSTRACT_NOT_FOUND_ID

# ** test: test_synthesize_abstract_missing_abstract
def test_synthesize_abstract_missing_abstract():
    '''
    Synthesizing an unknown abstract raises ABSTRACT_NOT_FOUND.
    '''

    # Abstract service cannot resolve the requested id.
    abstract_service = mock.Mock(spec=AbstractService)
    abstract_service.get.return_value = None

    # Execute and expect ABSTRACT_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            SynthesizeAbstract,
            dependencies={
                'abstract_service': abstract_service,
                'theme_service': mock.Mock(spec=ThemeService),
                'abstract_synthesis_service': mock.Mock(spec=AbstractSynthesisService),
            },
            id='missing-abstract',
        )

    # Assert the structured not-found error.
    assert exc_info.value.error_code == ABSTRACT_NOT_FOUND_ID

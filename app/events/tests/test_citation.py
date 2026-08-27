"""Lit Review Citation Event Tests"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError
from unittest import mock

# ** app
from tiferet import DomainEvent

from app.domain.citation import MAX_CONTEXT_NOTE_BYTES, MAX_EXCERPT_BYTES, MAX_TITLE_BYTES
from app.events.citation import AddCitation, UpdateCitation
from app.interfaces.citation import CitationService
from app.interfaces.source import SourceService
from app.mappers.citation import CitationAggregate
from app.mappers.source import SourceAggregate

# *** constants

# ** constant: source_id
SOURCE_ID = 'source-1'

# ** constant: citation_id
CITATION_ID = '02a49f90-0ff1-48cb-916a-fbc92f9712dd'

# ** constant: locator
LOCATOR = '4-4'

# ** constant: excerpt
EXCERPT = 'Operations are the unit.'

# ** constant: citation_title
CITATION_TITLE = 'Operations as the unit of compilation'

# *** fixtures

# ** fixture: source
@pytest.fixture
def source() -> SourceAggregate:
    '''
    Build a source whose page-range locator convention accepts LOCATOR.

    :return: A minimal PDF source.
    :rtype: SourceAggregate
    '''

    # Return a source with the page_range convention derived from medium.
    source = SourceAggregate(
        id=SOURCE_ID,
        medium='pdf',
        year=2020,
        title='MLIR: A Compiler Infrastructure',
    )
    source.add_author('Lattner, C.')
    return source

# ** fixture: citation
@pytest.fixture
def citation() -> CitationAggregate:
    '''
    Build a citation aggregate with an existing title, for update tests.

    :return: A citation belonging to the sample source.
    :rtype: CitationAggregate
    '''

    # Return a citation whose title an update event may replace or clear.
    return CitationAggregate(
        id=CITATION_ID,
        source_id=SOURCE_ID,
        locator=LOCATOR,
        excerpt=EXCERPT,
        title='Original title',
    )

# ** fixture: add_dependencies
@pytest.fixture
def add_dependencies(source) -> dict:
    '''
    Build mocked services for AddCitation.

    :param source: The source fixture.
    :type source: SourceAggregate
    :return: Constructor dependencies for the add event.
    :rtype: dict
    '''

    # Mock each injected service with its interface contract.
    citation_service = mock.Mock(spec=CitationService)
    source_service = mock.Mock(spec=SourceService)
    source_service.get.return_value = source

    # Return the assembled dependency map.
    return {
        'citation_service': citation_service,
        'source_service': source_service,
    }

# ** fixture: update_dependencies
@pytest.fixture
def update_dependencies(citation, source) -> dict:
    '''
    Build mocked services for UpdateCitation.

    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param source: The source fixture.
    :type source: SourceAggregate
    :return: Constructor dependencies for the update event.
    :rtype: dict
    '''

    # Mock each injected service with its interface contract.
    citation_service = mock.Mock(spec=CitationService)
    source_service = mock.Mock(spec=SourceService)
    citation_service.get.return_value = citation
    source_service.get.return_value = source

    # Return the assembled dependency map.
    return {
        'citation_service': citation_service,
        'source_service': source_service,
    }

# *** tests

# ** test: test_add_citation_stores_exact_title
def test_add_citation_stores_exact_title(add_dependencies):
    '''
    A supplied title is stored exactly as given.

    :param add_dependencies: Mocked add-event dependencies.
    :type add_dependencies: dict
    '''

    # Add a citation with an explicit title.
    result = DomainEvent.handle(
        AddCitation,
        dependencies=add_dependencies,
        source_id=SOURCE_ID,
        locator=LOCATOR,
        excerpt=EXCERPT,
        title=CITATION_TITLE,
    )

    # The exact title is stored and the citation is saved.
    assert result.title == CITATION_TITLE
    add_dependencies['citation_service'].save.assert_called_once()

# ** test: test_add_citation_without_title_is_none
def test_add_citation_without_title_is_none(add_dependencies):
    '''
    Omitting the title creates a valid citation with title is None.

    :param add_dependencies: Mocked add-event dependencies.
    :type add_dependencies: dict
    '''

    # Add a citation without a title.
    result = DomainEvent.handle(
        AddCitation,
        dependencies=add_dependencies,
        source_id=SOURCE_ID,
        locator=LOCATOR,
        excerpt=EXCERPT,
    )

    # No title was supplied, so none is stored.
    assert result.title is None

# ** test: test_add_citation_blank_title_becomes_none
def test_add_citation_blank_title_becomes_none(add_dependencies):
    '''
    A blank or whitespace-only title is treated as absent.

    :param add_dependencies: Mocked add-event dependencies.
    :type add_dependencies: dict
    '''

    # Add a citation with a whitespace-only title.
    result = DomainEvent.handle(
        AddCitation,
        dependencies=add_dependencies,
        source_id=SOURCE_ID,
        locator=LOCATOR,
        excerpt=EXCERPT,
        title='   ',
    )

    # The blank title normalizes to absent, not an empty string.
    assert result.title is None

# ** test: test_add_citation_overlong_title_raises
def test_add_citation_overlong_title_raises(add_dependencies):
    '''
    A title exceeding the byte cap is rejected rather than truncated.

    :param add_dependencies: Mocked add-event dependencies.
    :type add_dependencies: dict
    '''

    # Build a title one byte over the declared cap.
    overlong_title = 'x' * (MAX_TITLE_BYTES + 1)

    # Execute and expect a validation failure, not a silent truncation.
    with pytest.raises(ValidationError):
        DomainEvent.handle(
            AddCitation,
            dependencies=add_dependencies,
            source_id=SOURCE_ID,
            locator=LOCATOR,
            excerpt=EXCERPT,
            title=overlong_title,
        )

    # No citation was saved.
    add_dependencies['citation_service'].save.assert_not_called()

# ** test: test_update_citation_replaces_title
def test_update_citation_replaces_title(citation, update_dependencies):
    '''
    Supplying a title replaces the existing one.

    :param citation: The citation fixture, with an existing title.
    :type citation: CitationAggregate
    :param update_dependencies: Mocked update-event dependencies.
    :type update_dependencies: dict
    '''

    # Update with a new title.
    result = DomainEvent.handle(
        UpdateCitation,
        dependencies=update_dependencies,
        id=CITATION_ID,
        title=CITATION_TITLE,
    )

    # The title is replaced and the citation is saved.
    assert result.title == CITATION_TITLE
    update_dependencies['citation_service'].save.assert_called_once_with(citation)

# ** test: test_update_citation_clear_title
def test_update_citation_clear_title(citation, update_dependencies):
    '''
    --clear-title clears the title without touching other fields.

    :param citation: The citation fixture, with an existing title.
    :type citation: CitationAggregate
    :param update_dependencies: Mocked update-event dependencies.
    :type update_dependencies: dict
    '''

    # Clear the title only.
    result = DomainEvent.handle(
        UpdateCitation,
        dependencies=update_dependencies,
        id=CITATION_ID,
        clear_title=True,
    )

    # The title is absent; every other field is untouched.
    assert result.title is None
    assert result.locator == LOCATOR
    assert result.excerpt == EXCERPT

# ** test: test_update_citation_blank_title_becomes_none
def test_update_citation_blank_title_becomes_none(citation, update_dependencies):
    '''
    Supplying a blank or whitespace-only title clears it.

    :param citation: The citation fixture, with an existing title.
    :type citation: CitationAggregate
    :param update_dependencies: Mocked update-event dependencies.
    :type update_dependencies: dict
    '''

    # Update with a whitespace-only title.
    result = DomainEvent.handle(
        UpdateCitation,
        dependencies=update_dependencies,
        id=CITATION_ID,
        title='   ',
    )

    # The blank title normalizes to absent.
    assert result.title is None

# ** test: test_update_citation_omitted_title_unchanged
def test_update_citation_omitted_title_unchanged(citation, update_dependencies):
    '''
    Omitting both title and clear_title leaves the existing title untouched.

    :param citation: The citation fixture, with an existing title.
    :type citation: CitationAggregate
    :param update_dependencies: Mocked update-event dependencies.
    :type update_dependencies: dict
    '''

    # Update only the excerpt; the title is not mentioned.
    result = DomainEvent.handle(
        UpdateCitation,
        dependencies=update_dependencies,
        id=CITATION_ID,
        excerpt='Updated excerpt.',
    )

    # The pre-existing title survives an unrelated update.
    assert result.title == 'Original title'

# ** test: test_update_citation_overlong_title_raises
def test_update_citation_overlong_title_raises(citation, update_dependencies):
    '''
    An overlong replacement title is rejected rather than truncated.

    :param citation: The citation fixture, with an existing title.
    :type citation: CitationAggregate
    :param update_dependencies: Mocked update-event dependencies.
    :type update_dependencies: dict
    '''

    # Build a title one byte over the declared cap.
    overlong_title = 'x' * (MAX_TITLE_BYTES + 1)

    # Execute and expect a validation failure; the original title survives.
    with pytest.raises(ValidationError):
        DomainEvent.handle(
            UpdateCitation,
            dependencies=update_dependencies,
            id=CITATION_ID,
            title=overlong_title,
        )
    assert citation.title == 'Original title'

# ** test: test_add_citation_overlong_excerpt_raises
def test_add_citation_overlong_excerpt_raises(add_dependencies):
    '''
    An excerpt exceeding the byte cap is rejected rather than truncated.

    :param add_dependencies: Mocked add-event dependencies.
    :type add_dependencies: dict
    '''

    # Build an excerpt one byte over the declared cap.
    overlong_excerpt = 'x' * (MAX_EXCERPT_BYTES + 1)

    # Execute and expect a validation failure before any row changes.
    with pytest.raises(ValidationError):
        DomainEvent.handle(
            AddCitation,
            dependencies=add_dependencies,
            source_id=SOURCE_ID,
            locator=LOCATOR,
            excerpt=overlong_excerpt,
        )

    # No citation was saved.
    add_dependencies['citation_service'].save.assert_not_called()

# ** test: test_add_citation_exact_capacity_excerpt_succeeds
def test_add_citation_exact_capacity_excerpt_succeeds(add_dependencies):
    '''
    An excerpt exactly at the byte cap is accepted and stored intact.

    :param add_dependencies: Mocked add-event dependencies.
    :type add_dependencies: dict
    '''

    # Build an excerpt exactly at the declared cap.
    exact_excerpt = 'x' * MAX_EXCERPT_BYTES

    # Execute and expect the citation to be created and saved.
    result = DomainEvent.handle(
        AddCitation,
        dependencies=add_dependencies,
        source_id=SOURCE_ID,
        locator=LOCATOR,
        excerpt=exact_excerpt,
    )

    # The full excerpt is stored, byte for byte.
    assert result.excerpt == exact_excerpt
    add_dependencies['citation_service'].save.assert_called_once()

# ** test: test_add_citation_overlong_context_note_raises
def test_add_citation_overlong_context_note_raises(add_dependencies):
    '''
    A context note exceeding the byte cap is rejected rather than truncated.

    :param add_dependencies: Mocked add-event dependencies.
    :type add_dependencies: dict
    '''

    # Build a context note one byte over the declared cap.
    overlong_note = 'x' * (MAX_CONTEXT_NOTE_BYTES + 1)

    # Execute and expect a validation failure before any row changes.
    with pytest.raises(ValidationError):
        DomainEvent.handle(
            AddCitation,
            dependencies=add_dependencies,
            source_id=SOURCE_ID,
            locator=LOCATOR,
            excerpt=EXCERPT,
            context_note=overlong_note,
        )

    # No citation was saved.
    add_dependencies['citation_service'].save.assert_not_called()

# ** test: test_update_citation_overlong_excerpt_raises
def test_update_citation_overlong_excerpt_raises(citation, update_dependencies):
    '''
    An overlong replacement excerpt is rejected; the original excerpt survives.

    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param update_dependencies: Mocked update-event dependencies.
    :type update_dependencies: dict
    '''

    # Build an excerpt one byte over the declared cap.
    overlong_excerpt = 'x' * (MAX_EXCERPT_BYTES + 1)

    # Execute and expect a validation failure; the original excerpt survives.
    with pytest.raises(ValidationError):
        DomainEvent.handle(
            UpdateCitation,
            dependencies=update_dependencies,
            id=CITATION_ID,
            excerpt=overlong_excerpt,
        )
    assert citation.excerpt == EXCERPT

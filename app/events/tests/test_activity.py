"""Lit Review Activity Recording Event Tests"""

# *** imports

# ** infra
import pytest
from unittest import mock

# ** app
from tiferet import DomainEvent

from app.domain.activity import (
    CITATION_ADDED_ACTION,
    CITATION_SUBJECT_TYPE,
    CITATION_UPDATED_ACTION,
    LINKAGE_CREATED_ACTION,
    LINKAGE_REINSTATED_ACTION,
    LINKAGE_RETIRED_ACTION,
    SOURCE_ADDED_ACTION,
    SOURCE_DOCUMENT_ATTACHED_ACTION,
    SOURCE_SUBJECT_TYPE,
    SOURCE_UPDATED_ACTION,
    THEME_ADDED_ACTION,
    THEME_SUBJECT_TYPE,
    THEME_SYNTHESIZED_ACTION,
    THEME_UPDATED_ACTION,
)
from app.events.activity import ListActivities
from app.events.citation import AddCitation, UpdateCitation
from app.events.source import AddSource, AttachSourceDocument, UpdateSource
from app.events.theme import (
    AddTheme,
    LinkCitationToTheme,
    ReinstateLinkage,
    RetireLinkage,
    UpdateTheme,
)
from app.interfaces.activity import ActivityService
from app.interfaces.citation import CitationService
from app.interfaces.file import DocumentFileService
from app.interfaces.linkage import LinkageService
from app.interfaces.source import SourceService
from app.interfaces.synthesis import ThemeSynthesisService
from app.interfaces.theme import ThemeService
from app.mappers.citation import CitationAggregate
from app.mappers.linkage import LinkageAggregate
from app.mappers.source import SourceAggregate
from app.mappers.theme import ThemeAggregate

# *** constants

# ** constant: source_id
SOURCE_ID = '4cfaeea5-869a-444a-8a51-7680812c118d'

# ** constant: theme_id
THEME_ID = 'universal-ir-abstractions'

# ** constant: citation_id
CITATION_ID = '02a49f90-0ff1-48cb-916a-fbc92f9712dd'

# ** constant: sensitive_excerpt
SENSITIVE_EXCERPT = 'Operations are the fundamental unit of abstraction.'

# ** constant: sensitive_context_note
SENSITIVE_CONTEXT_NOTE = 'Discussed alongside the dialect registration mechanism.'

# ** constant: sensitive_overview_note
SENSITIVE_OVERVIEW_NOTE = 'Proposes a reusable IR ecosystem for compiler design.'

# ** constant: sensitive_document_name
SENSITIVE_DOCUMENT_NAME = 'lattner_et_al_2020_mlir.pdf'

# *** fixtures

# ** fixture: source
@pytest.fixture
def source() -> SourceAggregate:
    '''
    Build a source aggregate with sensitive-content fields populated.

    :return: A source carrying an overview note and document name.
    :rtype: SourceAggregate
    '''

    # Return a source whose sensitive text must never leak into activity.
    result = SourceAggregate(
        id=SOURCE_ID,
        medium='pdf',
        year=2020,
        title='MLIR: A Compiler Infrastructure for the End of Moore\'s Law',
        overview_note=SENSITIVE_OVERVIEW_NOTE,
    )
    result.add_author('Lattner, C.')
    return result

# ** fixture: citation
@pytest.fixture
def citation() -> CitationAggregate:
    '''
    Build a citation aggregate with sensitive-content fields populated.

    :return: A citation carrying an excerpt and context note.
    :rtype: CitationAggregate
    '''

    # Return a citation whose excerpt/context_note must never leak into activity.
    return CitationAggregate(
        id=CITATION_ID,
        source_id=SOURCE_ID,
        locator='4-4',
        excerpt=SENSITIVE_EXCERPT,
        context_note=SENSITIVE_CONTEXT_NOTE,
    )

# ** fixture: theme
@pytest.fixture
def theme() -> ThemeAggregate:
    '''
    Build a theme aggregate with one active linkage already counted.

    :return: A theme ready for linkage retirement/reinstatement tests.
    :rtype: ThemeAggregate
    '''

    # Return a theme with a curated synthesis and one active linkage.
    return ThemeAggregate(
        id=THEME_ID,
        name='Universal IR abstractions',
        synthesized_description='Curated narrative synthesis.',
        linkage_count=1,
        retired_linkage_count=0,
    )

# ** fixture: linkage
@pytest.fixture
def linkage() -> LinkageAggregate:
    '''
    Build the linkage shared by the retire/reinstate tests.

    :return: A linkage for the sample citation and theme.
    :rtype: LinkageAggregate
    '''

    # Return the structural pair used by the retirement tests.
    return LinkageAggregate(citation_id=CITATION_ID, theme_id=THEME_ID)

# *** tests

# ** test: test_add_source_records_source_added
def test_add_source_records_source_added():
    '''
    AddSource records a source.added entry naming the new source (AC #1).
    '''

    # Mock persistence and the activity service.
    source_service = mock.Mock(spec=SourceService)
    activity_service = mock.Mock(spec=ActivityService)

    # Create a new source.
    result = DomainEvent.handle(
        AddSource,
        dependencies={
            'source_service': source_service,
            'activity_service': activity_service,
        },
        source_medium='pdf',
        authors=['Lattner, C.'],
        year=2020,
        title='MLIR: A Compiler Infrastructure',
    )

    # Exactly one entry is recorded, naming the new source.
    activity_service.record.assert_called_once()
    (entry,), _ = activity_service.record.call_args
    assert entry.action == SOURCE_ADDED_ACTION
    assert entry.subject_type == SOURCE_SUBJECT_TYPE
    assert entry.subject_id == result.id
    assert entry.changed_fields == []

# ** test: test_add_citation_records_citation_added_without_excerpt
def test_add_citation_records_citation_added_without_excerpt(source):
    '''
    AddCitation records citation.added and never carries the excerpt (AC #3, #11).

    :param source: The source fixture the citation belongs to.
    :type source: SourceAggregate
    '''

    # Mock persistence and the activity service.
    citation_service = mock.Mock(spec=CitationService)
    source_service = mock.Mock(spec=SourceService)
    activity_service = mock.Mock(spec=ActivityService)
    source_service.get.return_value = source

    # Create a new citation carrying a sensitive excerpt and context note.
    result = DomainEvent.handle(
        AddCitation,
        dependencies={
            'citation_service': citation_service,
            'source_service': source_service,
            'activity_service': activity_service,
        },
        source_id=SOURCE_ID,
        locator='4-4',
        excerpt=SENSITIVE_EXCERPT,
        context_note=SENSITIVE_CONTEXT_NOTE,
    )

    # Exactly one entry is recorded, naming the new citation with no values.
    activity_service.record.assert_called_once()
    (entry,), _ = activity_service.record.call_args
    assert entry.action == CITATION_ADDED_ACTION
    assert entry.subject_type == CITATION_SUBJECT_TYPE
    assert entry.subject_id == result.id
    assert entry.changed_fields == []
    for value in entry.model_dump().values():
        assert SENSITIVE_EXCERPT not in str(value)
        assert SENSITIVE_CONTEXT_NOTE not in str(value)

# ** test: test_add_theme_records_theme_added
def test_add_theme_records_theme_added():
    '''
    AddTheme records a theme.added entry naming the new theme (AC #4).
    '''

    # Mock persistence and the activity service.
    theme_service = mock.Mock(spec=ThemeService)
    activity_service = mock.Mock(spec=ActivityService)
    theme_service.exists.return_value = False

    # Create a new theme.
    result = DomainEvent.handle(
        AddTheme,
        dependencies={
            'theme_service': theme_service,
            'activity_service': activity_service,
        },
        name='Universal IR abstractions',
    )

    # Exactly one entry is recorded, naming the new theme.
    activity_service.record.assert_called_once()
    (entry,), _ = activity_service.record.call_args
    assert entry.action == THEME_ADDED_ACTION
    assert entry.subject_type == THEME_SUBJECT_TYPE
    assert entry.subject_id == result.id

# ** test: test_update_source_records_only_touched_field_names
def test_update_source_records_only_touched_field_names(source):
    '''
    UpdateSource records changed_fields by name only, never by value (AC #2).

    :param source: The source fixture to update.
    :type source: SourceAggregate
    '''

    # Mock persistence and the activity service.
    source_service = mock.Mock(spec=SourceService)
    activity_service = mock.Mock(spec=ActivityService)
    source_service.get.return_value = source

    # Update only the overview note.
    DomainEvent.handle(
        UpdateSource,
        dependencies={
            'source_service': source_service,
            'activity_service': activity_service,
        },
        id=SOURCE_ID,
        overview_note='A revised overview.',
    )

    # The entry names the touched field only; no note text is present.
    activity_service.record.assert_called_once()
    (entry,), _ = activity_service.record.call_args
    assert entry.action == SOURCE_UPDATED_ACTION
    assert entry.changed_fields == ['overview_note']
    assert 'A revised overview.' not in entry.changed_fields

# ** test: test_update_source_no_op_records_nothing
def test_update_source_no_op_records_nothing(source):
    '''
    An UpdateSource call that touches nothing records no entry.

    :param source: The source fixture to update.
    :type source: SourceAggregate
    '''

    # Mock persistence and the activity service.
    source_service = mock.Mock(spec=SourceService)
    activity_service = mock.Mock(spec=ActivityService)
    source_service.get.return_value = source

    # Call update with no field arguments supplied.
    DomainEvent.handle(
        UpdateSource,
        dependencies={
            'source_service': source_service,
            'activity_service': activity_service,
        },
        id=SOURCE_ID,
    )

    # No activity entry is recorded for a no-op update.
    activity_service.record.assert_not_called()

# ** test: test_attach_source_document_records_document_name_only
def test_attach_source_document_records_document_name_only(source):
    '''
    AttachSourceDocument always records, naming only document_name (AC #2).

    :param source: The source fixture to attach a document to.
    :type source: SourceAggregate
    '''

    # Mock persistence, file reads, and the activity service.
    source_service = mock.Mock(spec=SourceService)
    document_file_service = mock.Mock(spec=DocumentFileService)
    activity_service = mock.Mock(spec=ActivityService)
    source_service.get.return_value = source
    document_file_service.read_bytes.return_value = b'%PDF-1.4 fake document body'

    # Attach a document, deriving its name.
    DomainEvent.handle(
        AttachSourceDocument,
        dependencies={
            'source_service': source_service,
            'document_file_service': document_file_service,
            'activity_service': activity_service,
        },
        source_id=SOURCE_ID,
        path='/tmp/2002.11054v2.pdf',
    )

    # The entry names only document_name; no path or byte content appears.
    activity_service.record.assert_called_once()
    (entry,), _ = activity_service.record.call_args
    assert entry.action == SOURCE_DOCUMENT_ATTACHED_ACTION
    assert entry.changed_fields == ['document_name']

# ** test: test_update_citation_records_only_touched_field_names
def test_update_citation_records_only_touched_field_names(source, citation):
    '''
    UpdateCitation records changed_fields by name only, never by value.

    :param source: The parent source fixture.
    :type source: SourceAggregate
    :param citation: The citation fixture to update.
    :type citation: CitationAggregate
    '''

    # Mock persistence and the activity service.
    citation_service = mock.Mock(spec=CitationService)
    source_service = mock.Mock(spec=SourceService)
    activity_service = mock.Mock(spec=ActivityService)
    citation_service.get.return_value = citation
    source_service.get.return_value = source

    # Update only the context note.
    DomainEvent.handle(
        UpdateCitation,
        dependencies={
            'citation_service': citation_service,
            'source_service': source_service,
            'activity_service': activity_service,
        },
        id=CITATION_ID,
        context_note='A revised context note.',
    )

    # The entry names the touched field only; no note text is present.
    activity_service.record.assert_called_once()
    (entry,), _ = activity_service.record.call_args
    assert entry.action == CITATION_UPDATED_ACTION
    assert entry.changed_fields == ['context_note']

# ** test: test_update_citation_no_op_records_nothing
def test_update_citation_no_op_records_nothing(source, citation):
    '''
    An UpdateCitation call that touches nothing records no entry.

    :param source: The parent source fixture.
    :type source: SourceAggregate
    :param citation: The citation fixture to update.
    :type citation: CitationAggregate
    '''

    # Mock persistence and the activity service.
    citation_service = mock.Mock(spec=CitationService)
    source_service = mock.Mock(spec=SourceService)
    activity_service = mock.Mock(spec=ActivityService)
    citation_service.get.return_value = citation
    source_service.get.return_value = source

    # Call update with no field arguments supplied.
    DomainEvent.handle(
        UpdateCitation,
        dependencies={
            'citation_service': citation_service,
            'source_service': source_service,
            'activity_service': activity_service,
        },
        id=CITATION_ID,
    )

    # No activity entry is recorded for a no-op update.
    activity_service.record.assert_not_called()

# ** test: test_update_theme_editorial_write_records_theme_updated_not_synthesized
def test_update_theme_editorial_write_records_theme_updated_not_synthesized(theme):
    '''
    UpdateTheme's manual edit records theme.updated, distinct from synthesis.

    :param theme: The theme fixture to update.
    :type theme: ThemeAggregate
    '''

    # Mock persistence and the activity service.
    theme_service = mock.Mock(spec=ThemeService)
    activity_service = mock.Mock(spec=ActivityService)
    theme_service.get.return_value = theme

    # Apply an editorial description edit.
    DomainEvent.handle(
        UpdateTheme,
        dependencies={
            'theme_service': theme_service,
            'activity_service': activity_service,
        },
        id=THEME_ID,
        description='A hand-curated narrative.',
    )

    # The action token is theme.updated, not theme.synthesized.
    activity_service.record.assert_called_once()
    (entry,), _ = activity_service.record.call_args
    assert entry.action == THEME_UPDATED_ACTION
    assert entry.changed_fields == ['synthesized_description']

# ** test: test_link_citation_to_theme_new_pair_records_linkage_created
def test_link_citation_to_theme_new_pair_records_linkage_created(theme, citation):
    '''
    A new linkage records linkage.created with theme as subject, citation as related (AC #5).

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    '''

    # Mock the four injected services plus the activity service.
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_synthesis_service = mock.Mock(spec=ThemeSynthesisService)
    activity_service = mock.Mock(spec=ActivityService)
    theme_service.get.return_value = theme
    citation_service.get.return_value = citation
    linkage_service.list.return_value = []

    # Link the citation without opting into synthesis.
    DomainEvent.handle(
        LinkCitationToTheme,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
            'theme_synthesis_service': theme_synthesis_service,
            'activity_service': activity_service,
        },
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
    )

    # Exactly one entry: linkage.created, theme subject, citation related.
    activity_service.record.assert_called_once()
    (entry,), _ = activity_service.record.call_args
    assert entry.action == LINKAGE_CREATED_ACTION
    assert entry.subject_type == THEME_SUBJECT_TYPE
    assert entry.subject_id == THEME_ID
    assert entry.related_type == CITATION_SUBJECT_TYPE
    assert entry.related_id == CITATION_ID

# ** test: test_link_citation_to_theme_idempotent_records_nothing
def test_link_citation_to_theme_idempotent_records_nothing(theme, citation, linkage):
    '''
    Re-linking an existing pair without synthesis records nothing (AC #6).

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param linkage: The existing linkage fixture.
    :type linkage: LinkageAggregate
    '''

    # Mock services with an existing pair already stored.
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_synthesis_service = mock.Mock(spec=ThemeSynthesisService)
    activity_service = mock.Mock(spec=ActivityService)
    theme_service.get.return_value = theme
    citation_service.get.return_value = citation
    linkage_service.list.return_value = [linkage]

    # Re-link the same pair without opting into synthesis.
    DomainEvent.handle(
        LinkCitationToTheme,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
            'theme_synthesis_service': theme_synthesis_service,
            'activity_service': activity_service,
        },
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
    )

    # No entry is recorded for the idempotent, no-op re-link.
    activity_service.record.assert_not_called()

# ** test: test_link_citation_to_theme_idempotent_with_synthesis_records_only_synthesized
def test_link_citation_to_theme_idempotent_with_synthesis_records_only_synthesized(
        theme,
        citation,
        linkage,
    ):
    '''
    An idempotent re-link with include_synthesis records theme.synthesized
    only, never a second linkage.created (AC #6).

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param linkage: The existing linkage fixture.
    :type linkage: LinkageAggregate
    '''

    # Mock services with an existing pair already stored.
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    theme_synthesis_service = mock.Mock(spec=ThemeSynthesisService)
    activity_service = mock.Mock(spec=ActivityService)
    theme_service.get.return_value = theme
    citation_service.get.return_value = citation
    linkage_service.list.return_value = [linkage]
    theme_synthesis_service.synthesize.return_value = 'Resynthesized text.'

    # Re-link the same pair, opting into synthesis this time.
    DomainEvent.handle(
        LinkCitationToTheme,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
            'theme_synthesis_service': theme_synthesis_service,
            'activity_service': activity_service,
        },
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
        include_synthesis=True,
    )

    # Exactly one entry: theme.synthesized, never a second linkage.created.
    activity_service.record.assert_called_once()
    (entry,), _ = activity_service.record.call_args
    assert entry.action == THEME_SYNTHESIZED_ACTION
    assert entry.subject_id == THEME_ID

# ** test: test_retire_linkage_records_linkage_retired
def test_retire_linkage_records_linkage_retired(theme, citation, linkage):
    '''
    Retiring an active linkage records linkage.retired (AC #5).

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param linkage: The active linkage fixture.
    :type linkage: LinkageAggregate
    '''

    # Mock services with the active linkage already stored.
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    activity_service = mock.Mock(spec=ActivityService)
    theme_service.get.return_value = theme
    citation_service.get.return_value = citation
    linkage_service.list.return_value = [linkage]

    # Retire the linkage.
    DomainEvent.handle(
        RetireLinkage,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
            'activity_service': activity_service,
        },
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
        reason='Superseded.',
    )

    # Exactly one entry is recorded for the real state change.
    activity_service.record.assert_called_once()
    (entry,), _ = activity_service.record.call_args
    assert entry.action == LINKAGE_RETIRED_ACTION
    assert entry.subject_id == THEME_ID
    assert entry.related_id == CITATION_ID

# ** test: test_retire_linkage_idempotent_records_nothing
def test_retire_linkage_idempotent_records_nothing(theme, citation, linkage):
    '''
    Retiring an already-retired linkage records nothing (AC #6).

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param linkage: The linkage fixture, pre-retired for this test.
    :type linkage: LinkageAggregate
    '''

    # The linkage is already retired before the call under test.
    linkage.retire(reason='Original reason.')
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    activity_service = mock.Mock(spec=ActivityService)
    theme_service.get.return_value = theme
    citation_service.get.return_value = citation
    linkage_service.list.return_value = [linkage]

    # Attempt to retire it again.
    DomainEvent.handle(
        RetireLinkage,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
            'activity_service': activity_service,
        },
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
        reason='A different reason.',
    )

    # No entry is recorded for the idempotent, no-op retirement.
    activity_service.record.assert_not_called()

# ** test: test_reinstate_linkage_records_linkage_reinstated
def test_reinstate_linkage_records_linkage_reinstated(theme, citation, linkage):
    '''
    Reinstating a retired linkage records linkage.reinstated (AC #5).

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param linkage: The linkage fixture, pre-retired for this test.
    :type linkage: LinkageAggregate
    '''

    # The linkage starts retired.
    linkage.retire(reason='Superseded.')
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    activity_service = mock.Mock(spec=ActivityService)
    theme_service.get.return_value = theme
    citation_service.get.return_value = citation
    linkage_service.list.return_value = [linkage]

    # Reinstate the linkage.
    DomainEvent.handle(
        ReinstateLinkage,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
            'activity_service': activity_service,
        },
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
    )

    # Exactly one entry is recorded for the real state change.
    activity_service.record.assert_called_once()
    (entry,), _ = activity_service.record.call_args
    assert entry.action == LINKAGE_REINSTATED_ACTION
    assert entry.subject_id == THEME_ID
    assert entry.related_id == CITATION_ID

# ** test: test_reinstate_linkage_idempotent_records_nothing
def test_reinstate_linkage_idempotent_records_nothing(theme, citation, linkage):
    '''
    Reinstating an already-active linkage records nothing (AC #6).

    :param theme: The theme fixture.
    :type theme: ThemeAggregate
    :param citation: The citation fixture.
    :type citation: CitationAggregate
    :param linkage: The already-active linkage fixture.
    :type linkage: LinkageAggregate
    '''

    # Mock services; the linkage is already active.
    theme_service = mock.Mock(spec=ThemeService)
    linkage_service = mock.Mock(spec=LinkageService)
    citation_service = mock.Mock(spec=CitationService)
    activity_service = mock.Mock(spec=ActivityService)
    theme_service.get.return_value = theme
    citation_service.get.return_value = citation
    linkage_service.list.return_value = [linkage]

    # Attempt to reinstate the already-active linkage.
    DomainEvent.handle(
        ReinstateLinkage,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
            'activity_service': activity_service,
        },
        citation_id=CITATION_ID,
        theme_id=THEME_ID,
    )

    # No entry is recorded for the idempotent, no-op reinstatement.
    activity_service.record.assert_not_called()

# ** test: test_add_source_survives_activity_recording_failure
def test_add_source_survives_activity_recording_failure():
    '''
    A failed activity append never affects the domain write it followed (AC #9).
    '''

    # Mock persistence; the activity service raises on every record() call.
    source_service = mock.Mock(spec=SourceService)
    activity_service = mock.Mock(spec=ActivityService)
    activity_service.record.side_effect = RuntimeError('storage unavailable')

    # Create a new source despite the activity backend being unavailable.
    result = DomainEvent.handle(
        AddSource,
        dependencies={
            'source_service': source_service,
            'activity_service': activity_service,
        },
        source_medium='pdf',
        authors=['Lattner, C.'],
        year=2020,
        title='MLIR: A Compiler Infrastructure',
    )

    # The domain write succeeded and was not undone by the recording failure.
    source_service.save.assert_called_once_with(result)
    activity_service.record.assert_called_once()

# ** test: test_list_activities_applies_filters_and_returns_service_result
def test_list_activities_applies_filters_and_returns_service_result():
    '''
    ListActivities forwards its filters and returns the service's result (AC #7).
    '''

    # Mock the activity service to return a sentinel list.
    activity_service = mock.Mock(spec=ActivityService)
    sentinel = [mock.Mock()]
    activity_service.list.return_value = sentinel

    # List with every optional filter supplied.
    result = DomainEvent.handle(
        ListActivities,
        dependencies={'activity_service': activity_service},
        action=SOURCE_ADDED_ACTION,
        subject_type=SOURCE_SUBJECT_TYPE,
        subject_id=SOURCE_ID,
        related_id=None,
    )

    # The filters reach the service unchanged and its result is returned.
    activity_service.list.assert_called_once_with(
        action=SOURCE_ADDED_ACTION,
        subject_type=SOURCE_SUBJECT_TYPE,
        subject_id=SOURCE_ID,
        related_id=None,
    )
    assert result is sentinel

"""Lit Review Source Document Event Tests"""

# *** imports

# ** core
from pathlib import Path

# ** infra
import pytest
from unittest import mock

# ** app
from tiferet import DomainEvent
from tiferet.assets import TiferetError
from tiferet.contexts.feature import FeatureContext
from tiferet.contexts.request import RequestContext
from tiferet.repos.feature import FeatureConfigRepository
from app.domain.source import (
    PAGE_RANGE_LOCATOR_CONVENTION,
    SLIDE_RANGE_LOCATOR_CONVENTION,
    WEB_LOCATOR_CONVENTION,
    is_valid_locator,
)

from app.events.source import (
    SOURCE_DOCUMENT_NOT_FOUND_ID,
    SOURCE_NOT_FOUND_ID,
    AddSource,
    AttachSourceDocument,
    DownloadSourceDocument,
    GetSourceDocument,
    UpdateSource,
)
from app.interfaces.activity import ActivityService
from app.interfaces.file import DocumentFileService
from app.interfaces.source import SourceService
from app.mappers.source import SourceAggregate, SourceDocumentResponse

# *** constants

# ** constant: source_id
SOURCE_ID = '4cfaeea5-869a-444a-8a51-7680812c118d'

# ** constant: upload_path
UPLOAD_PATH = '/tmp/2002.11054v2.pdf'

# ** constant: document_bytes
DOCUMENT_BYTES = b'%PDF-1.4 fake document body'

# ** constant: custom_document_name
CUSTOM_DOCUMENT_NAME = 'custom_name.pdf'

# *** fixtures

# ** fixture: multi_author_source
@pytest.fixture
def multi_author_source() -> SourceAggregate:
    '''
    Build a multi-author source used for default-name derivation.

    :return: A source with two authors and no attached document.
    :rtype: SourceAggregate
    '''

    # Return a source whose derived name must include et_al.
    source = SourceAggregate(
        id=SOURCE_ID,
        medium='pdf',
        year=2020,
        title='MLIR: A Compiler Infrastructure for the End of Moore\'s Law',
    )
    source.add_author('Lattner, C.')
    source.add_author('Amini, M.')
    return source

# ** fixture: single_author_source
@pytest.fixture
def single_author_source() -> SourceAggregate:
    '''
    Build a single-author source used for default-name derivation.

    :return: A source with one author and no attached document.
    :rtype: SourceAggregate
    '''

    # Return a source whose derived name must omit et_al.
    source = SourceAggregate(
        id='single-author-source',
        medium='pdf',
        year=2024,
        title='A Method for Efficient Heterogeneous Parallel Compilation',
    )
    source.add_author('Tan, Z.')
    return source

# ** fixture: attached_source
@pytest.fixture
def attached_source(multi_author_source) -> SourceAggregate:
    '''
    Build a source that already has an API document name.

    :param multi_author_source: The multi-author source fixture.
    :type multi_author_source: SourceAggregate
    :return: The same source with a stored document name.
    :rtype: SourceAggregate
    '''

    # Attach the default derived name as if a previous upload succeeded.
    multi_author_source.attach_document(
        multi_author_source.derive_document_name(path=UPLOAD_PATH)
    )
    return multi_author_source

# ** fixture: attach_dependencies
@pytest.fixture
def attach_dependencies(multi_author_source) -> dict:
    '''
    Build mocked services for AttachSourceDocument.

    :param multi_author_source: The multi-author source fixture.
    :type multi_author_source: SourceAggregate
    :return: Constructor dependencies for the attach event.
    :rtype: dict
    '''

    # Mock each injected service with its interface contract.
    source_service = mock.Mock(spec=SourceService)
    document_file_service = mock.Mock(spec=DocumentFileService)

    # Resolve the sample source and return raw upload bytes.
    source_service.get.return_value = multi_author_source
    document_file_service.read_bytes.return_value = DOCUMENT_BYTES

    # Return the assembled dependency map.
    return {
        'source_service': source_service,
        'document_file_service': document_file_service,
        'activity_service': mock.Mock(spec=ActivityService),
    }

# *** tests

# ** test: test_derive_document_name_includes_et_al_for_multiple_authors
def test_derive_document_name_includes_et_al_for_multiple_authors(
        multi_author_source,
    ):
    '''
    Default names include et_al, year, a title slug, and the PDF extension.

    :param multi_author_source: The multi-author source fixture.
    :type multi_author_source: SourceAggregate
    '''

    # Derive the API name from the bibliographic record and upload path.
    name = multi_author_source.derive_document_name(path=UPLOAD_PATH)

    # The name follows the settled {first}_et_al_{year}_{title}.{ext} shape.
    assert name.startswith('lattner_et_al_2020_')
    assert name.endswith('.pdf')
    assert 'mlir' in name

# ** test: test_derive_document_name_omits_et_al_for_single_author
def test_derive_document_name_omits_et_al_for_single_author(
        single_author_source,
    ):
    '''
    Default names omit et_al when the source has one author.

    :param single_author_source: The single-author source fixture.
    :type single_author_source: SourceAggregate
    '''

    # Derive the API name for a single-author PDF.
    name = single_author_source.derive_document_name(path=UPLOAD_PATH)

    # The first-author slug and year are present; et_al is not.
    assert name.startswith('tan_2024_')
    assert '_et_al_' not in name
    assert name.endswith('.pdf')

# ** test: test_attach_source_document_derives_name_and_stores_bytes
def test_attach_source_document_derives_name_and_stores_bytes(
        multi_author_source,
        attach_dependencies,
    ):
    '''
    Attach without a name override stores derived document_name and bytes.

    :param multi_author_source: The multi-author source fixture.
    :type multi_author_source: SourceAggregate
    :param attach_dependencies: Mocked attach-event dependencies.
    :type attach_dependencies: dict
    '''

    # Attach the upload without supplying an API name.
    result = DomainEvent.handle(
        AttachSourceDocument,
        dependencies=attach_dependencies,
        source_id=SOURCE_ID,
        path=UPLOAD_PATH,
    )

    # The source is saved, then the array is written under the source id.
    source_service = attach_dependencies['source_service']
    file_service = attach_dependencies['document_file_service']
    file_service.read_bytes.assert_called_once_with(UPLOAD_PATH)
    source_service.save.assert_called_once_with(multi_author_source)
    source_service.save_document.assert_called_once_with(
        SOURCE_ID,
        DOCUMENT_BYTES,
    )

    # Ordinary get is metadata-only; the derived name is non-empty and PDF.
    source_service.get_document.assert_not_called()
    assert result.document_name
    assert result.document_name.startswith('lattner_et_al_2020_')
    assert result.document_name.endswith('.pdf')

# ** test: test_attach_source_document_uses_supplied_name
def test_attach_source_document_uses_supplied_name(
        multi_author_source,
        attach_dependencies,
    ):
    '''
    Attach with -n stores the exact supplied document name.

    :param multi_author_source: The multi-author source fixture.
    :type multi_author_source: SourceAggregate
    :param attach_dependencies: Mocked attach-event dependencies.
    :type attach_dependencies: dict
    '''

    # Attach with an explicit API name override.
    result = DomainEvent.handle(
        AttachSourceDocument,
        dependencies=attach_dependencies,
        source_id=SOURCE_ID,
        path=UPLOAD_PATH,
        document_name=CUSTOM_DOCUMENT_NAME,
    )

    # The stored name is the override, not the derived bibliographic slug.
    assert result.document_name == CUSTOM_DOCUMENT_NAME
    attach_dependencies['source_service'].save_document.assert_called_once()

# ** test: test_attach_source_document_uses_cli_name_alias
def test_attach_source_document_uses_cli_name_alias(
        multi_author_source,
        attach_dependencies,
    ):
    '''
    Attach with the CLI-facing name= alias stores that exact document name.

    :param multi_author_source: The multi-author source fixture.
    :type multi_author_source: SourceAggregate
    :param attach_dependencies: Mocked attach-event dependencies.
    :type attach_dependencies: dict
    '''

    # Attach as the feature configuration now does: only the name alias.
    result = DomainEvent.handle(
        AttachSourceDocument,
        dependencies=attach_dependencies,
        source_id=SOURCE_ID,
        path=UPLOAD_PATH,
        name=CUSTOM_DOCUMENT_NAME,
    )

    # The stored name is the CLI-supplied override, not the derived slug.
    assert result.document_name == CUSTOM_DOCUMENT_NAME
    attach_dependencies['source_service'].save_document.assert_called_once()

# ** test: test_attach_source_document_name_alias_omitted_still_derives
def test_attach_source_document_name_alias_omitted_still_derives(
        multi_author_source,
        attach_dependencies,
    ):
    '''
    Attach with neither document_name nor name still derives a name.

    :param multi_author_source: The multi-author source fixture.
    :type multi_author_source: SourceAggregate
    :param attach_dependencies: Mocked attach-event dependencies.
    :type attach_dependencies: dict
    '''

    # Attach passing the CLI alias as None, mirroring an omitted -n/--name flag.
    result = DomainEvent.handle(
        AttachSourceDocument,
        dependencies=attach_dependencies,
        source_id=SOURCE_ID,
        path=UPLOAD_PATH,
        name=None,
    )

    # The name is still derived from the bibliographic record.
    assert result.document_name.startswith('lattner_et_al_2020_')

# ** test: test_attach_source_document_document_name_wins_over_name_alias
def test_attach_source_document_document_name_wins_over_name_alias(
        multi_author_source,
        attach_dependencies,
    ):
    '''
    A programmatic document_name takes precedence over the CLI name alias.

    :param multi_author_source: The multi-author source fixture.
    :type multi_author_source: SourceAggregate
    :param attach_dependencies: Mocked attach-event dependencies.
    :type attach_dependencies: dict
    '''

    # Supply both aliases; document_name must win.
    result = DomainEvent.handle(
        AttachSourceDocument,
        dependencies=attach_dependencies,
        source_id=SOURCE_ID,
        path=UPLOAD_PATH,
        document_name=CUSTOM_DOCUMENT_NAME,
        name='ignored_name.pdf',
    )

    # The programmatic override is stored, not the CLI alias.
    assert result.document_name == CUSTOM_DOCUMENT_NAME

# ** test: test_attach_source_document_missing_source
def test_attach_source_document_missing_source():
    '''
    Attach against a missing source raises SOURCE_NOT_FOUND and writes no array.
    '''

    # Source service cannot resolve the requested id.
    source_service = mock.Mock(spec=SourceService)
    document_file_service = mock.Mock(spec=DocumentFileService)
    source_service.get.return_value = None

    # Execute and expect SOURCE_NOT_FOUND before any file or array write.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            AttachSourceDocument,
            dependencies={
                'source_service': source_service,
                'document_file_service': document_file_service,
                'activity_service': mock.Mock(spec=ActivityService),
            },
            source_id='missing-source',
            path=UPLOAD_PATH,
        )

    # Assert the structured error and that no array was written.
    assert exc_info.value.error_code == SOURCE_NOT_FOUND_ID
    document_file_service.read_bytes.assert_not_called()
    source_service.save_document.assert_not_called()

# ** test: test_attach_source_document_replaces_existing_array
def test_attach_source_document_replaces_existing_array(
        attached_source,
    ):
    '''
    Re-attach updates the document name and replaces the previous array.

    :param attached_source: A source that already has a document name.
    :type attached_source: SourceAggregate
    '''

    # Mock services as if a previous document is already stored.
    source_service = mock.Mock(spec=SourceService)
    document_file_service = mock.Mock(spec=DocumentFileService)
    source_service.get.return_value = attached_source
    document_file_service.read_bytes.return_value = b'replacement-bytes'

    # Re-attach with a new API name.
    result = DomainEvent.handle(
        AttachSourceDocument,
        dependencies={
            'source_service': source_service,
            'document_file_service': document_file_service,
            'activity_service': mock.Mock(spec=ActivityService),
        },
        source_id=SOURCE_ID,
        path=UPLOAD_PATH,
        document_name=CUSTOM_DOCUMENT_NAME,
    )

    # One save_document call replaces the previous array and updates the name.
    source_service.save_document.assert_called_once_with(
        SOURCE_ID,
        b'replacement-bytes',
    )
    assert result.document_name == CUSTOM_DOCUMENT_NAME

# ** test: test_get_source_document_returns_bytes_and_name
def test_get_source_document_returns_bytes_and_name(attached_source):
    '''
    GetSourceDocument returns the stored name and body.

    :param attached_source: A source that already has a document name.
    :type attached_source: SourceAggregate
    '''

    # Mock a metadata get plus an explicit array read.
    source_service = mock.Mock(spec=SourceService)
    source_service.get.return_value = attached_source
    source_service.get_document.return_value = DOCUMENT_BYTES

    # Retrieve the named body.
    result = DomainEvent.handle(
        GetSourceDocument,
        dependencies={'source_service': source_service},
        source_id=SOURCE_ID,
    )

    # The response carries the API name and the stored bytes.
    source_service.get_document.assert_called_once_with(SOURCE_ID)
    assert isinstance(result, SourceDocumentResponse)
    assert result.document_name == attached_source.document_name
    assert result.content == DOCUMENT_BYTES

# ** test: test_get_source_document_missing_attachment
def test_get_source_document_missing_attachment(multi_author_source):
    '''
    Get-document against a source with no attachment raises SOURCE_DOCUMENT_NOT_FOUND.

    :param multi_author_source: A source with no document name.
    :type multi_author_source: SourceAggregate
    '''

    # Metadata exists; the array does not.
    source_service = mock.Mock(spec=SourceService)
    source_service.get.return_value = multi_author_source
    source_service.get_document.return_value = None

    # Execute and expect SOURCE_DOCUMENT_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            GetSourceDocument,
            dependencies={'source_service': source_service},
            source_id=SOURCE_ID,
        )

    # Assert the structured missing-document error.
    assert exc_info.value.error_code == SOURCE_DOCUMENT_NOT_FOUND_ID

# ** test: test_download_source_document_writes_api_name
def test_download_source_document_writes_api_name(
        attached_source,
        tmp_path: Path,
    ):
    '''
    Download writes document_name, not the original upload basename.

    :param attached_source: A source that already has a document name.
    :type attached_source: SourceAggregate
    :param tmp_path: Temporary destination directory.
    :type tmp_path: Path
    '''

    # Mock retrieve; write is asserted on the file service.
    source_service = mock.Mock(spec=SourceService)
    document_file_service = mock.Mock(spec=DocumentFileService)
    source_service.get.return_value = attached_source
    source_service.get_document.return_value = DOCUMENT_BYTES

    # Download into the temporary directory.
    result = DomainEvent.handle(
        DownloadSourceDocument,
        dependencies={
            'source_service': source_service,
            'document_file_service': document_file_service,
        },
        source_id=SOURCE_ID,
        out=str(tmp_path),
    )

    # The written path uses the API name, not 2002.11054v2.pdf.
    expected_path = str(tmp_path / attached_source.document_name)
    document_file_service.write_bytes.assert_called_once_with(
        expected_path,
        DOCUMENT_BYTES,
    )
    assert result.document_name == attached_source.document_name
    assert result.document_name != '2002.11054v2.pdf'

# ** test: test_download_source_document_missing_attachment
def test_download_source_document_missing_attachment(multi_author_source):
    '''
    Download against a source with no attachment raises SOURCE_DOCUMENT_NOT_FOUND.

    :param multi_author_source: A source with no document name.
    :type multi_author_source: SourceAggregate
    '''

    # Metadata exists; the array does not.
    source_service = mock.Mock(spec=SourceService)
    document_file_service = mock.Mock(spec=DocumentFileService)
    source_service.get.return_value = multi_author_source
    source_service.get_document.return_value = None

    # Execute and expect SOURCE_DOCUMENT_NOT_FOUND.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            DownloadSourceDocument,
            dependencies={
                'source_service': source_service,
                'document_file_service': document_file_service,
            },
            source_id=SOURCE_ID,
        )

    # Assert no file was written.
    assert exc_info.value.error_code == SOURCE_DOCUMENT_NOT_FOUND_ID
    document_file_service.write_bytes.assert_not_called()

# ** test: test_add_web_source_accepts_cli_url_alias
def test_add_web_source_accepts_cli_url_alias():
    '''
    AddSource accepts the optional raw CLI URL without any network access.
    '''

    # Mock persistence while exercising the complete source-domain validation.
    source_service = mock.Mock(spec=SourceService)

    # Capture a web-native source with a canonical online location.
    result = DomainEvent.handle(
        AddSource,
        dependencies={
            'source_service': source_service,
            'activity_service': mock.Mock(spec=ActivityService),
        },
        source_medium='web',
        authors=['Example, A.'],
        year=2026,
        title='An Online Reading',
        url='https://example.com/reading/module-5#section-1',
    )

    # The URL round-trips unchanged and web sources use the flexible locator.
    assert result.source_url == 'https://example.com/reading/module-5#section-1'
    assert result.locator_convention == 'web_locator'
    source_service.save.assert_called_once_with(result)

# ** test: test_web_locator_accepts_canonical_text_reference
def test_web_locator_accepts_canonical_text_reference():
    '''
    Web locators support textual references while page ranges retain their rule.
    '''

    # A module-and-section reference is valid for the web medium only.
    assert is_valid_locator(WEB_LOCATOR_CONVENTION, '5.1') is True
    assert is_valid_locator(PAGE_RANGE_LOCATOR_CONVENTION, '5.1') is False

# ** test: test_source_url_validation_is_local_and_syntactic
@pytest.mark.parametrize(
    'source_url',
    [
        'https://example.com/reading',
        'http://textbook.example.edu/chapter/1#section-2',
    ],
)
def test_source_url_validation_is_local_and_syntactic(source_url):
    '''
    HTTP(S) URLs with hosts are accepted without resolving any remote service.

    :param source_url: A syntactically valid source URL.
    :type source_url: str
    '''

    # Construction validates only local URL structure.
    source = SourceAggregate(
        medium='web',
        year=2026,
        title='Online Text',
        source_url=source_url,
    )

    # The exact accepted value is preserved as provenance metadata.
    assert source.source_url == source_url

# ** test: test_source_url_validation_rejects_invalid_values
@pytest.mark.parametrize(
    'source_url',
    [
        'example.com/reading',
        'ftp://example.com/reading',
        'https://',
        ' https://example.com/reading',
        'https://example.com/reading here',
    ],
)
def test_source_url_validation_rejects_invalid_values(source_url):
    '''
    Invalid source URL syntax fails before any source can be persisted.

    :param source_url: An invalid source URL.
    :type source_url: str
    '''

    # Domain construction rejects unsupported or malformed local URL shapes.
    with pytest.raises(ValueError):
        SourceAggregate(
            medium='web',
            year=2026,
            title='Online Text',
            source_url=source_url,
        )

# ** test: test_update_source_replaces_and_clears_cli_url_alias
def test_update_source_replaces_and_clears_cli_url_alias():
    '''
    UpdateSource distinguishes a CLI URL replacement from explicit removal.
    '''

    # Build a source with the URL an update will replace.
    source = SourceAggregate(
        id=SOURCE_ID,
        medium='book',
        year=2026,
        title='Online Edition',
        source_url='https://example.com/original',
    )
    source.add_author('Example, A.')
    source_service = mock.Mock(spec=SourceService)
    source_service.get.return_value = source

    # Replace through the raw CLI alias, then clear through its explicit flag.
    update_dependencies = {
        'source_service': source_service,
        'activity_service': mock.Mock(spec=ActivityService),
    }
    DomainEvent.handle(
        UpdateSource,
        dependencies=update_dependencies,
        id=SOURCE_ID,
        url='https://example.com/revised',
    )
    assert source.source_url == 'https://example.com/revised'
    DomainEvent.handle(
        UpdateSource,
        dependencies=update_dependencies,
        id=SOURCE_ID,
        clear_url=True,
    )

    # Explicit clear removes only the optional provenance location.
    assert source.source_url is None
    assert source.title == 'Online Edition'

# ** test: test_add_presentation_source_derives_slide_range_convention
def test_add_presentation_source_derives_slide_range_convention():
    '''
    A presentation source derives the slide_range locator convention (AC #1).
    '''

    # Mock persistence while exercising the presentation-medium seam.
    source_service = mock.Mock(spec=SourceService)

    # Capture a presentation source; pdf/book still derive page_range.
    result = DomainEvent.handle(
        AddSource,
        dependencies={
            'source_service': source_service,
            'activity_service': mock.Mock(spec=ActivityService),
        },
        source_medium='presentation',
        authors=['Example, A.'],
        year=2026,
        title='A Compiler Infrastructure Deck',
    )

    # The declared convention is slide_range, distinct from page_range.
    assert result.locator_convention == SLIDE_RANGE_LOCATOR_CONVENTION
    source_service.save.assert_called_once_with(result)

# ** test: test_slide_range_accepts_numeric_ranges_like_page_range
def test_slide_range_accepts_numeric_ranges_like_page_range():
    '''
    Slide ranges share page_range's numeric-range grammar (AC #2).
    '''

    # Equal and unequal numeric ranges are valid; non-numeric text is not.
    assert is_valid_locator(SLIDE_RANGE_LOCATOR_CONVENTION, '9-9') is True
    assert is_valid_locator(SLIDE_RANGE_LOCATOR_CONVENTION, '9-11') is True
    assert is_valid_locator(SLIDE_RANGE_LOCATOR_CONVENTION, 'ix-x') is False

    # Existing page_range validation is unaffected by the new convention.
    assert is_valid_locator(PAGE_RANGE_LOCATOR_CONVENTION, '9-11') is True

# ** test: test_add_source_stores_overview_note
def test_add_source_stores_overview_note():
    '''
    AddSource persists an optional, medium-agnostic overview note (AC #6).
    '''

    # Mock persistence while exercising overview-note capture.
    source_service = mock.Mock(spec=SourceService)

    # Capture a source with a researcher-authored overview note.
    result = DomainEvent.handle(
        AddSource,
        dependencies={
            'source_service': source_service,
            'activity_service': mock.Mock(spec=ActivityService),
        },
        source_medium='pdf',
        authors=['Lattner, C.'],
        year=2020,
        title='MLIR: A Compiler Infrastructure',
        overview_note='Proposes a reusable IR ecosystem for compiler design.',
    )

    # The exact note is stored.
    assert result.overview_note == 'Proposes a reusable IR ecosystem for compiler design.'

# ** test: test_add_source_blank_overview_note_becomes_none
def test_add_source_blank_overview_note_becomes_none():
    '''
    A blank or whitespace-only overview note normalizes to absent.
    '''

    # Mock persistence; omission and blank input both mean no note.
    source_service = mock.Mock(spec=SourceService)

    # Capture a source with a whitespace-only overview note.
    result = DomainEvent.handle(
        AddSource,
        dependencies={
            'source_service': source_service,
            'activity_service': mock.Mock(spec=ActivityService),
        },
        source_medium='pdf',
        authors=['Lattner, C.'],
        year=2020,
        title='MLIR: A Compiler Infrastructure',
        overview_note='   ',
    )

    # The blank note normalizes to absent, not an empty string.
    assert result.overview_note is None

# ** test: test_update_source_replaces_and_clears_overview_note
def test_update_source_replaces_and_clears_overview_note():
    '''
    UpdateSource replaces the overview note, then clears it explicitly (AC #7).
    '''

    # Build a source with no initial overview note.
    source = SourceAggregate(
        id=SOURCE_ID,
        medium='pdf',
        year=2020,
        title='MLIR: A Compiler Infrastructure',
    )
    source.add_author('Lattner, C.')
    source_service = mock.Mock(spec=SourceService)
    source_service.get.return_value = source

    # Replace the overview note.
    update_dependencies = {
        'source_service': source_service,
        'activity_service': mock.Mock(spec=ActivityService),
    }
    DomainEvent.handle(
        UpdateSource,
        dependencies=update_dependencies,
        id=SOURCE_ID,
        overview_note='Revised overview.',
    )
    assert source.overview_note == 'Revised overview.'

    # An unrelated update leaves the overview note untouched.
    DomainEvent.handle(
        UpdateSource,
        dependencies=update_dependencies,
        id=SOURCE_ID,
        publisher='LLVM Foundation',
    )
    assert source.overview_note == 'Revised overview.'
    assert source.publisher == 'LLVM Foundation'

    # Explicit clear removes the overview note without touching other fields.
    DomainEvent.handle(
        UpdateSource,
        dependencies=update_dependencies,
        id=SOURCE_ID,
        clear_overview_note=True,
    )
    assert source.overview_note is None
    assert source.title == 'MLIR: A Compiler Infrastructure'

# ** test: test_attach_feature_omits_name_without_parameter_not_found
def test_attach_feature_omits_name_without_parameter_not_found():
    '''
    The real source.attach feature no longer eagerly resolves $r.name.

    Loads the actual app/assets/feature.yml definition and executes it with
    a mocked resolved event, proving an omitted -n/--name no longer raises
    PARAMETER_NOT_FOUND before AttachSourceDocument runs. Uses only mocks;
    the real .lit_review/lit_review.h5 store is never touched.
    '''

    # Load the real source.attach feature from the checked-in configuration.
    feature_repo = FeatureConfigRepository(feature_config='app/assets/feature.yml')
    feature = feature_repo.get('source.attach')

    # Resolve to a mocked event regardless of the requested service id.
    mock_event = mock.Mock()
    feature_context = FeatureContext.from_domain(
        feature,
        get_dependency=lambda service_id, *flags: mock_event,
    )

    # Build a request as the CLI would, omitting -n/--name entirely.
    request = RequestContext(data={'id': SOURCE_ID, 'file': UPLOAD_PATH})

    # Execute without raising PARAMETER_NOT_FOUND.
    feature_context.execute_feature(request)

    # The mapped params reached the event; no document_name key is forced.
    _, call_kwargs = mock_event.execute.call_args
    assert call_kwargs['source_id'] == SOURCE_ID
    assert call_kwargs['path'] == UPLOAD_PATH
    assert 'document_name' not in call_kwargs

# ** test: test_attach_feature_supplied_name_reaches_event_unchanged
def test_attach_feature_supplied_name_reaches_event_unchanged():
    '''
    A supplied -n/--name reaches AttachSourceDocument unchanged as name=.

    Uses the real source.attach feature definition and a mocked resolved
    event; the real .h5 store is never touched.
    '''

    # Load the real source.attach feature from the checked-in configuration.
    feature_repo = FeatureConfigRepository(feature_config='app/assets/feature.yml')
    feature = feature_repo.get('source.attach')

    # Resolve to a mocked event regardless of the requested service id.
    mock_event = mock.Mock()
    feature_context = FeatureContext.from_domain(
        feature,
        get_dependency=lambda service_id, *flags: mock_event,
    )

    # Build a request as the CLI would, with -n/--name supplied.
    request = RequestContext(data={
        'id': SOURCE_ID,
        'file': UPLOAD_PATH,
        'name': CUSTOM_DOCUMENT_NAME,
    })
    feature_context.execute_feature(request)

    # The raw name value reaches the event unchanged via the request merge.
    _, call_kwargs = mock_event.execute.call_args
    assert call_kwargs['name'] == CUSTOM_DOCUMENT_NAME

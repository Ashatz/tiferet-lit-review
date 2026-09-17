"""Lit Review Citation Link Type Event Tests"""

# *** imports

# ** core
import shutil
from pathlib import Path
from unittest import mock

# ** infra
import pytest

# ** app
from tiferet import DomainEvent
from tiferet.assets import TiferetAPIError, TiferetError

from app.blueprints import build_app
from app.domain.activity import CITATION_ADDED_ACTION
from app.domain.citation import CITATION_TYPE_DEFAULT, CITATION_TYPE_LINK
from app.events.citation import (
    CITATION_LINK_IMMUTABLE_ID,
    CITATION_LINK_ORIGIN_NOT_FOUND_ID,
    INVALID_CITATION_LINK_POINTER_ID,
    INVALID_CITATION_TYPE_ID,
    AddCitation,
    ShowCitation,
    UpdateCitation,
)
from app.events.citation_style import RenderCitation
from app.events.theme import ShowTheme
from app.events.transfer import CopyCitation, MoveCitation
from app.interfaces.activity import ActivityService
from app.interfaces.citation import CitationService
from app.interfaces.citation_style import CitationStyleRuleService
from app.interfaces.linkage import LinkageService
from app.interfaces.project import ProjectService
from app.interfaces.source import SourceService
from app.interfaces.theme import ThemeService
from app.mappers.citation import CitationAggregate
from app.mappers.linkage import LinkageAggregate
from app.mappers.source import SourceAggregate
from app.mappers.theme import ThemeAggregate
from app.repos.citation import CitationH5Repository
from app.repos.source import SourceH5Repository

# *** constants

# ** constant: repo_root
REPO_ROOT = Path(__file__).resolve().parents[3]

# ** constant: asset_files
ASSET_FILES = [
    'app.yml',
    'di.yml',
    'feature.yml',
    'error.yml',
    'cli.yml',
    'citation_styles.yml',
]

# ** constant: source_id
SOURCE_ID = 'source-1'

# ** constant: origin_citation_id
ORIGIN_CITATION_ID = 'origin-citation-1'

# ** constant: link_citation_id
LINK_CITATION_ID = 'link-citation-1'

# ** constant: origin_project_id
ORIGIN_PROJECT_ID = 'kabbalah'

# ** constant: consumer_project_id
CONSUMER_PROJECT_ID = 'thesis'

# ** constant: origin_excerpt
ORIGIN_EXCERPT = 'Operations are the unit.'

# ** constant: origin_context_note
ORIGIN_CONTEXT_NOTE = 'Passage-faithful Kabbalah note.'

# ** constant: local_context_note
LOCAL_CONTEXT_NOTE = 'Tiferet design note.'

# ** constant: pointer
POINTER = f'{ORIGIN_PROJECT_ID}:{ORIGIN_CITATION_ID}'

# *** fixtures

# ** fixture: source
@pytest.fixture
def source() -> SourceAggregate:
    '''
    Build a source whose page-range locator convention accepts 4-4.

    :return: A minimal PDF source.
    :rtype: SourceAggregate
    '''

    # Return a source with the page_range convention derived from medium.
    result = SourceAggregate(
        id=SOURCE_ID,
        medium='pdf',
        year=2020,
        title='MLIR: A Compiler Infrastructure',
    )
    result.add_author('Lattner, C.')
    return result

# ** fixture: origin_citation
@pytest.fixture
def origin_citation() -> CitationAggregate:
    '''
    Build a default origin citation.

    :return: A default citation carrying evidence text.
    :rtype: CitationAggregate
    '''

    # Return a default citation the link pointer may name.
    return CitationAggregate(
        id=ORIGIN_CITATION_ID,
        source_id=SOURCE_ID,
        locator='4-4',
        excerpt=ORIGIN_EXCERPT,
        context_note=ORIGIN_CONTEXT_NOTE,
        type=CITATION_TYPE_DEFAULT,
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
    return {
        'citation_service': citation_service,
        'source_service': source_service,
        'activity_service': mock.Mock(spec=ActivityService),
    }

# ** fixture: app_home
@pytest.fixture
def app_home(tmp_path, monkeypatch) -> Path:
    '''
    Copy app YAML configs into an isolated cwd so the catalog is local.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :param monkeypatch: Pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :return: The isolated application home directory.
    :rtype: Path
    '''

    # Copy configuration YAML so relative app/assets paths resolve in tmp.
    dest = tmp_path / 'app' / 'assets'
    dest.mkdir(parents=True)
    src = REPO_ROOT / 'app' / 'assets'
    for name in ASSET_FILES:
        shutil.copy(src / name, dest / name)

    # Run the app as if tmp_path were the working directory.
    monkeypatch.chdir(tmp_path)
    return tmp_path

# *** functions

# ** function: origin_store_kwargs
def origin_store_kwargs(origin_citation: CitationAggregate, source: SourceAggregate) -> dict:
    '''
    Build catalog and project-store kwargs that resolve a default origin.

    :param origin_citation: The origin citation to return.
    :type origin_citation: CitationAggregate
    :param source: The origin source to return.
    :type source: SourceAggregate
    :return: Execute kwargs for origin lookup.
    :rtype: dict
    '''

    # Catalog returns the origin project; the scoped getter returns origin services.
    project_service = mock.Mock(spec=ProjectService)
    project_service.get.return_value = mock.Mock(
        id=ORIGIN_PROJECT_ID,
        h5_file='kabbalah.h5',
    )
    origin_citation_service = mock.Mock(spec=CitationService)
    origin_citation_service.get.return_value = origin_citation
    origin_source_service = mock.Mock(spec=SourceService)
    origin_source_service.get.return_value = source

    def get_project_dependency(project_id, h5_file):
        def getter(service_id, *flags):
            if service_id == 'citation_service':
                return origin_citation_service
            if service_id == 'source_service':
                return origin_source_service
            return mock.Mock()
        return getter

    # Return the execute kwargs FeatureContext would inject.
    return {
        'project_service': project_service,
        'get_project_dependency': get_project_dependency,
    }

# *** tests

# ** test: test_add_citation_default_type_requires_source_and_stores_default
def test_add_citation_default_type_requires_source_and_stores_default(add_dependencies):
    '''
    citation add without --type still requires source, locator, and excerpt.
    '''

    # Add a default citation the same way existing callers do.
    result = DomainEvent.handle(
        AddCitation,
        dependencies=add_dependencies,
        source_id=SOURCE_ID,
        locator='4-4',
        excerpt=ORIGIN_EXCERPT,
    )

    # The stored row is type=default with local evidence fields.
    assert result.type == CITATION_TYPE_DEFAULT
    assert result.source_id == SOURCE_ID
    assert result.locator == '4-4'
    assert result.excerpt == ORIGIN_EXCERPT
    add_dependencies['citation_service'].save.assert_called_once()

# ** test: test_add_citation_link_stores_pointer_without_local_source
def test_add_citation_link_stores_pointer_without_local_source(
        add_dependencies,
        origin_citation,
        source,
    ):
    '''
    citation add --type link stores the pointer and optional local note.
    '''

    # Add a link without local source or locator.
    result = DomainEvent.handle(
        AddCitation,
        dependencies=add_dependencies,
        excerpt=POINTER,
        type=CITATION_TYPE_LINK,
        context_note=LOCAL_CONTEXT_NOTE,
        title='Linked passage',
        **origin_store_kwargs(origin_citation, source),
    )

    # The local row is a link; origin evidence is not copied onto it.
    assert result.type == CITATION_TYPE_LINK
    assert result.excerpt == POINTER
    assert result.context_note == LOCAL_CONTEXT_NOTE
    assert result.title == 'Linked passage'
    assert result.source_id == ''
    assert result.locator == ''
    add_dependencies['citation_service'].save.assert_called_once()
    add_dependencies['source_service'].get.assert_not_called()

    # Activity names type and never stores the pointer as a value.
    activity_service = add_dependencies['activity_service']
    activity_service.record.assert_called_once()
    (entry,), _ = activity_service.record.call_args
    assert entry.action == CITATION_ADDED_ACTION
    assert entry.changed_fields == ['type']
    assert POINTER not in str(entry.model_dump())

# ** test: test_add_citation_link_rejects_missing_origin_and_writes_no_row
@pytest.mark.parametrize('origin_return', [None, 'link'])
def test_add_citation_link_rejects_missing_origin_and_writes_no_row(
        add_dependencies,
        origin_citation,
        source,
        origin_return,
    ):
    '''
    Adding a link to a missing citation or a link origin writes no row.
    '''

    # Point the origin getter at a missing citation or another link.
    kwargs = origin_store_kwargs(origin_citation, source)
    if origin_return is None:
        origin_citation_service = kwargs['get_project_dependency'](
            ORIGIN_PROJECT_ID,
            'kabbalah.h5',
        )('citation_service')
        origin_citation_service.get.return_value = None
    else:
        origin_citation_service = kwargs['get_project_dependency'](
            ORIGIN_PROJECT_ID,
            'kabbalah.h5',
        )('citation_service')
        origin_citation_service.get.return_value = CitationAggregate(
            id=ORIGIN_CITATION_ID,
            excerpt=f'{ORIGIN_PROJECT_ID}:other',
            type=CITATION_TYPE_LINK,
        )

    # Execute and expect origin-not-found before save.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            AddCitation,
            dependencies=add_dependencies,
            excerpt=POINTER,
            type=CITATION_TYPE_LINK,
            **kwargs,
        )
    assert exc_info.value.error_code == CITATION_LINK_ORIGIN_NOT_FOUND_ID
    add_dependencies['citation_service'].save.assert_not_called()

# ** test: test_add_citation_link_rejects_missing_project
def test_add_citation_link_rejects_missing_project(add_dependencies):
    '''
    Adding a link to a missing origin project writes no row.
    '''

    # Catalog lookup returns no project.
    project_service = mock.Mock(spec=ProjectService)
    project_service.get.return_value = None
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            AddCitation,
            dependencies=add_dependencies,
            excerpt=POINTER,
            type=CITATION_TYPE_LINK,
            project_service=project_service,
            get_project_dependency=lambda project_id, h5_file: mock.Mock(),
        )
    assert exc_info.value.error_code == CITATION_LINK_ORIGIN_NOT_FOUND_ID
    add_dependencies['citation_service'].save.assert_not_called()

# ** test: test_add_citation_link_rejects_malformed_pointer
def test_add_citation_link_rejects_malformed_pointer(add_dependencies):
    '''
    A pointer that is not project_id:citation_id is rejected.
    '''

    # Execute with a colon-less excerpt.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            AddCitation,
            dependencies=add_dependencies,
            excerpt='not-a-pointer',
            type=CITATION_TYPE_LINK,
            project_service=mock.Mock(spec=ProjectService),
            get_project_dependency=lambda project_id, h5_file: mock.Mock(),
        )
    assert exc_info.value.error_code == INVALID_CITATION_LINK_POINTER_ID
    add_dependencies['citation_service'].save.assert_not_called()

# ** test: test_add_citation_rejects_unknown_type
def test_add_citation_rejects_unknown_type(add_dependencies):
    '''
    An unknown --type value is rejected before save.
    '''

    # Execute with a type that is neither default nor link.
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            AddCitation,
            dependencies=add_dependencies,
            source_id=SOURCE_ID,
            locator='4-4',
            excerpt=ORIGIN_EXCERPT,
            type='copy',
        )
    assert exc_info.value.error_code == INVALID_CITATION_TYPE_ID
    add_dependencies['citation_service'].save.assert_not_called()

# ** test: test_update_citation_link_may_change_note_not_pointer
def test_update_citation_link_may_change_note_not_pointer():
    '''
    Update may change a link's context_note but must not retarget the pointer.
    '''

    # Start from a stored link row.
    link = CitationAggregate(
        id=LINK_CITATION_ID,
        excerpt=POINTER,
        context_note=LOCAL_CONTEXT_NOTE,
        type=CITATION_TYPE_LINK,
    )
    citation_service = mock.Mock(spec=CitationService)
    citation_service.get.return_value = link
    dependencies = {
        'citation_service': citation_service,
        'source_service': mock.Mock(spec=SourceService),
        'activity_service': mock.Mock(spec=ActivityService),
    }

    # Title/context_note updates are allowed.
    result = DomainEvent.handle(
        UpdateCitation,
        dependencies=dependencies,
        id=LINK_CITATION_ID,
        context_note='Revised local note.',
        title='Revised title',
    )
    assert result.context_note == 'Revised local note.'
    assert result.title == 'Revised title'
    assert result.excerpt == POINTER

    # Retargeting the pointer is refused and does not save.
    citation_service.save.reset_mock()
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            UpdateCitation,
            dependencies=dependencies,
            id=LINK_CITATION_ID,
            excerpt='other:citation',
        )
    assert exc_info.value.error_code == CITATION_LINK_IMMUTABLE_ID
    citation_service.save.assert_not_called()

# ** test: test_show_citation_resolves_origin_excerpt_and_keeps_local_note
def test_show_citation_resolves_origin_excerpt_and_keeps_local_note(
        origin_citation,
        source,
    ):
    '''
    Show overlays origin excerpt/locator and keeps the local context_note.
    '''

    # Show a stored link row.
    link = CitationAggregate(
        id=LINK_CITATION_ID,
        excerpt=POINTER,
        context_note=LOCAL_CONTEXT_NOTE,
        type=CITATION_TYPE_LINK,
    )
    citation_service = mock.Mock(spec=CitationService)
    citation_service.get.return_value = link
    result = DomainEvent.handle(
        ShowCitation,
        dependencies={'citation_service': citation_service},
        id=LINK_CITATION_ID,
        **origin_store_kwargs(origin_citation, source),
    )

    # Display uses origin evidence and the consumer's note; type stays link.
    assert result.type == CITATION_TYPE_LINK
    assert result.excerpt == ORIGIN_EXCERPT
    assert result.locator == '4-4'
    assert result.context_note == LOCAL_CONTEXT_NOTE
    assert result.context_note != ORIGIN_CONTEXT_NOTE
    citation_service.save.assert_not_called()

# ** test: test_render_citation_link_uses_origin_source_and_locator
def test_render_citation_link_uses_origin_source_and_locator(
        origin_citation,
        source,
    ):
    '''
    Render of a link uses the origin Source record and origin locator.
    '''

    # Render a stored link through APA-like templates.
    link = CitationAggregate(
        id=LINK_CITATION_ID,
        excerpt=POINTER,
        context_note=LOCAL_CONTEXT_NOTE,
        type=CITATION_TYPE_LINK,
    )
    citation_service = mock.Mock(spec=CitationService)
    citation_service.get.return_value = link
    citation_style_service = mock.Mock(spec=CitationStyleRuleService)
    citation_style_service.get_rule.return_value = mock.Mock(
        author_format='last_first',
        reference_template='{authors} ({year}). {title}.',
        in_text_template='({authors_short}, {year}, {locator_display})',
    )
    result = DomainEvent.handle(
        RenderCitation,
        dependencies={
            'citation_service': citation_service,
            'source_service': mock.Mock(spec=SourceService),
            'citation_style_service': citation_style_service,
        },
        citation_id=LINK_CITATION_ID,
        style_id='apa',
        **origin_store_kwargs(origin_citation, source),
    )

    # In-text and reference read origin bibliography and locator, not the pointer.
    assert 'Lattner' in result.formatted_reference
    assert '2020' in result.formatted_reference
    assert POINTER not in result.formatted_reference
    assert POINTER not in result.in_text_citation
    assert result.in_text_citation.endswith('p. 4)')
    assert result.excerpt == ORIGIN_EXCERPT

# ** test: test_render_citation_missing_origin_fails_without_quoting_pointer
def test_render_citation_missing_origin_fails_without_quoting_pointer():
    '''
    Missing origin at render time fails visibly and does not quote the pointer.
    '''

    # Origin catalog lookup misses the project.
    link = CitationAggregate(
        id=LINK_CITATION_ID,
        excerpt=POINTER,
        type=CITATION_TYPE_LINK,
    )
    citation_service = mock.Mock(spec=CitationService)
    citation_service.get.return_value = link
    project_service = mock.Mock(spec=ProjectService)
    project_service.get.return_value = None
    with pytest.raises(TiferetError) as exc_info:
        DomainEvent.handle(
            RenderCitation,
            dependencies={
                'citation_service': citation_service,
                'source_service': mock.Mock(spec=SourceService),
                'citation_style_service': mock.Mock(spec=CitationStyleRuleService),
            },
            citation_id=LINK_CITATION_ID,
            style_id='apa',
            project_service=project_service,
            get_project_dependency=lambda project_id, h5_file: mock.Mock(),
        )
    assert exc_info.value.error_code == CITATION_LINK_ORIGIN_NOT_FOUND_ID

# ** test: test_theme_show_uses_origin_excerpt_and_local_note
def test_theme_show_uses_origin_excerpt_and_local_note(origin_citation, source):
    '''
    theme show uses origin excerpt and the consumer context_note.
    '''

    # Show a theme whose only linkage is a local link citation.
    link = CitationAggregate(
        id=LINK_CITATION_ID,
        excerpt=POINTER,
        context_note=LOCAL_CONTEXT_NOTE,
        type=CITATION_TYPE_LINK,
    )
    theme = ThemeAggregate(
        id='tiferet-design',
        name='Tiferet design',
        synthesized_description='',
        linkage_count=1,
        retired_linkage_count=0,
    )
    theme_service = mock.Mock(spec=ThemeService)
    theme_service.get.return_value = theme
    linkage_service = mock.Mock(spec=LinkageService)
    linkage_service.list.return_value = [
        LinkageAggregate(citation_id=LINK_CITATION_ID, theme_id='tiferet-design'),
    ]
    citation_service = mock.Mock(spec=CitationService)
    citation_service.get.return_value = link
    result = DomainEvent.handle(
        ShowTheme,
        dependencies={
            'theme_service': theme_service,
            'linkage_service': linkage_service,
            'citation_service': citation_service,
        },
        id='tiferet-design',
        **origin_store_kwargs(origin_citation, source),
    )

    # The shown citation is origin passage plus local note.
    shown = result.citations[0]
    assert shown.excerpt == ORIGIN_EXCERPT
    assert shown.context_note == LOCAL_CONTEXT_NOTE
    assert ORIGIN_CONTEXT_NOTE not in shown.context_note
    assert shown.excerpt != POINTER

# ** test: test_copy_and_move_link_transfer_row_only
def test_copy_and_move_link_transfer_row_only(tmp_path, origin_citation):
    '''
    Copy/move of a link transfers the link row only, not the origin source.
    '''

    # Persist a link in origin and copy it into an empty dest store.
    origin_h5 = str(tmp_path / 'origin.h5')
    dest_h5 = str(tmp_path / 'dest.h5')
    origin_citation_repo = CitationH5Repository(h5_file=origin_h5)
    origin_source_repo = SourceH5Repository(h5_file=origin_h5)
    dest_citation_repo = CitationH5Repository(h5_file=dest_h5)
    dest_source_repo = SourceH5Repository(h5_file=dest_h5)
    link = CitationAggregate(
        id=LINK_CITATION_ID,
        excerpt=POINTER,
        context_note=LOCAL_CONTEXT_NOTE,
        title='Linked passage',
        type=CITATION_TYPE_LINK,
    )
    origin_citation_repo.save(link)

    # Copy writes the link row and does not create a dest source.
    copied = DomainEvent.handle(
        CopyCitation,
        dependencies={
            'citation_service': origin_citation_repo,
            'source_service': origin_source_repo,
            'activity_service': mock.Mock(spec=ActivityService),
        },
        id=LINK_CITATION_ID,
        dest_project_id=CONSUMER_PROJECT_ID,
        project_id=ORIGIN_PROJECT_ID,
        dest_citation_service=dest_citation_repo,
        dest_source_service=dest_source_repo,
        dest_activity_service=mock.Mock(spec=ActivityService),
    )
    dest = dest_citation_repo.get(LINK_CITATION_ID)
    assert copied.type == CITATION_TYPE_LINK
    assert dest.excerpt == POINTER
    assert dest.context_note == LOCAL_CONTEXT_NOTE
    assert dest_source_repo.list() == []
    assert origin_citation_repo.get(LINK_CITATION_ID) is not None

    # Move of a second link removes only the origin link row.
    move_id = 'link-move-1'
    origin_citation_repo.save(CitationAggregate(
        id=move_id,
        excerpt=POINTER,
        type=CITATION_TYPE_LINK,
    ))
    DomainEvent.handle(
        MoveCitation,
        dependencies={
            'citation_service': origin_citation_repo,
            'source_service': origin_source_repo,
            'activity_service': mock.Mock(spec=ActivityService),
        },
        id=move_id,
        dest_project_id=CONSUMER_PROJECT_ID,
        project_id=ORIGIN_PROJECT_ID,
        dest_citation_service=dest_citation_repo,
        dest_source_service=dest_source_repo,
        dest_activity_service=mock.Mock(spec=ActivityService),
    )
    assert dest_citation_repo.get(move_id).type == CITATION_TYPE_LINK
    assert origin_citation_repo.get(move_id) is None
    assert dest_source_repo.list() == []

# ** test: test_app_session_link_add_show_render_and_theme
def test_app_session_link_add_show_render_and_theme(app_home):
    '''
    End-to-end add/show/render/theme against two catalogued projects.
    '''

    # Create origin and consumer projects with a default citation on origin.
    session = build_app()
    session.run(
        'project.add',
        data={
            'id': ORIGIN_PROJECT_ID,
            'name': 'Kabbalah',
            'h5_file': str(app_home / 'kabbalah.h5'),
        },
    )
    session.run(
        'project.add',
        data={
            'id': CONSUMER_PROJECT_ID,
            'name': 'Thesis',
            'h5_file': str(app_home / 'thesis.h5'),
        },
    )
    origin_source = session.run(
        'source.add',
        data={
            'project_id': ORIGIN_PROJECT_ID,
            'medium': 'pdf',
            'authors': ['Lattner, C.'],
            'year': 2020,
            'title': 'MLIR: A Compiler Infrastructure',
        },
    )
    origin = session.run(
        'citation.add',
        data={
            'project_id': ORIGIN_PROJECT_ID,
            'source_id': origin_source.id,
            'locator': '4-4',
            'excerpt': ORIGIN_EXCERPT,
            'context_note': ORIGIN_CONTEXT_NOTE,
        },
    )
    assert origin.type == CITATION_TYPE_DEFAULT

    # Add a consumer link without local source/locator.
    link = session.run(
        'citation.add',
        data={
            'project_id': CONSUMER_PROJECT_ID,
            'type': CITATION_TYPE_LINK,
            'excerpt': f'{ORIGIN_PROJECT_ID}:{origin.id}',
            'context_note': LOCAL_CONTEXT_NOTE,
            'title': 'Linked passage',
        },
    )
    assert link.type == CITATION_TYPE_LINK
    assert link.excerpt == f'{ORIGIN_PROJECT_ID}:{origin.id}'
    listed = session.run(
        'citation.list',
        data={'project_id': CONSUMER_PROJECT_ID},
    )
    assert listed[0].type == CITATION_TYPE_LINK
    assert listed[0].excerpt == f'{ORIGIN_PROJECT_ID}:{origin.id}'

    # Show resolves origin excerpt; list stayed metadata-light.
    shown = session.run(
        'citation.show',
        data={'project_id': CONSUMER_PROJECT_ID, 'id': link.id},
    )
    assert shown.excerpt == ORIGIN_EXCERPT
    assert shown.context_note == LOCAL_CONTEXT_NOTE
    assert shown.locator == '4-4'

    # Render uses origin bibliography and locator, never the pointer string.
    rendered = session.run(
        'citation.render',
        data={
            'project_id': CONSUMER_PROJECT_ID,
            'id': link.id,
            'style': 'apa',
        },
    )
    pointer = f'{ORIGIN_PROJECT_ID}:{origin.id}'
    assert pointer not in rendered.formatted_reference
    assert pointer not in rendered.in_text_citation
    assert 'Lattner' in rendered.formatted_reference
    assert 'p. 4' in rendered.in_text_citation

    # Theme show uses origin excerpt and local context_note.
    theme = session.run(
        'theme.add',
        data={'project_id': CONSUMER_PROJECT_ID, 'name': 'Tiferet design'},
    )
    session.run(
        'theme.link',
        data={
            'project_id': CONSUMER_PROJECT_ID,
            'citation_id': link.id,
            'theme_id': theme.id,
        },
    )
    shown_theme = session.run(
        'theme.show',
        data={'project_id': CONSUMER_PROJECT_ID, 'id': theme.id},
    )
    shown_citation = shown_theme.citations[0]
    assert shown_citation.excerpt == ORIGIN_EXCERPT
    assert shown_citation.context_note == LOCAL_CONTEXT_NOTE
    assert shown_citation.context_note != ORIGIN_CONTEXT_NOTE

    # Missing origin at resolve time fails and does not quote the pointer.
    session.run(
        'project.add',
        data={
            'id': 'ghost',
            'name': 'Ghost',
            'h5_file': str(app_home / 'ghost.h5'),
        },
    )
    dangling = session.run(
        'citation.add',
        data={
            'project_id': CONSUMER_PROJECT_ID,
            'type': CITATION_TYPE_LINK,
            'excerpt': f'{ORIGIN_PROJECT_ID}:{origin.id}',
        },
    )
    # Remove the origin citation after the link exists.
    CitationH5Repository(h5_file=str(app_home / 'kabbalah.h5')).remove_for_transfer(
        origin.id,
    )
    with pytest.raises(TiferetAPIError) as exc_info:
        session.run(
            'citation.render',
            data={
                'project_id': CONSUMER_PROJECT_ID,
                'id': dangling.id,
                'style': 'apa',
            },
        )
    assert exc_info.value.error_code == CITATION_LINK_ORIGIN_NOT_FOUND_ID
    assert pointer not in (exc_info.value.kwargs.get('formatted_reference') or '')

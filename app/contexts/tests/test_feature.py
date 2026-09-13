"""Lit Review Feature Context and Project Catalog Acceptance Tests"""

# *** imports

# ** core
import shutil
from pathlib import Path
from unittest import mock

# ** infra
import pytest

# ** app
from tiferet.assets import TiferetAPIError
from tiferet.assets.error import COMMAND_PARAMETER_REQUIRED_ID
from tiferet.contexts.request import RequestContext
from tiferet.repos.feature import FeatureConfigRepository

from app.blueprints import build_app, build_cli
from app.contexts.feature import LitReviewFeatureContext
from app.events.project import PROJECT_NOT_FOUND_ID
from app.mappers.source import SourceAggregate
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

# *** fixtures

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

# *** tests

# ** test: test_attach_feature_omits_name_without_parameter_not_found
def test_attach_feature_omits_name_without_parameter_not_found():
    '''
    The real source.attach feature no longer eagerly resolves $r.name.

    Uses LitReviewFeatureContext with an explicit project_id so the new
    contract still maps omitted -n/--name without PARAMETER_NOT_FOUND.
    '''

    # Load the real source.attach feature from the checked-in configuration.
    feature_repo = FeatureConfigRepository(feature_config='app/assets/feature.yml')
    feature = feature_repo.get('source.attach')

    # Catalog lookup succeeds; step resolution returns a mocked event.
    mock_event = mock.Mock()
    project_service = mock.Mock()
    project_service.get.return_value = mock.Mock(
        id='default',
        h5_file='.lit_review/lit_review.h5',
    )

    def get_dependency(service_id, *flags):
        if service_id == 'project_service':
            return project_service
        return mock_event

    feature_context = LitReviewFeatureContext.from_domain(
        feature,
        get_dependency=get_dependency,
        get_project_dependency=lambda project_id, h5_file: get_dependency,
    )

    # Build a request as the CLI would, omitting -n/--name entirely.
    request = RequestContext(data={
        'project_id': 'default',
        'id': '4cfaeea5-869a-444a-8a51-7680812c118d',
        'file': '/tmp/2002.11054v2.pdf',
    })

    # Execute without raising PARAMETER_NOT_FOUND.
    feature_context.execute_feature(request)

    # The mapped params reached the event; no document_name key is forced.
    _, call_kwargs = mock_event.execute.call_args
    assert call_kwargs['source_id'] == '4cfaeea5-869a-444a-8a51-7680812c118d'
    assert call_kwargs['path'] == '/tmp/2002.11054v2.pdf'
    assert 'document_name' not in call_kwargs


# ** test: test_attach_feature_supplied_name_reaches_event_unchanged
def test_attach_feature_supplied_name_reaches_event_unchanged():
    '''
    A supplied -n/--name reaches AttachSourceDocument unchanged as name=.
    '''

    # Load the real source.attach feature from the checked-in configuration.
    feature_repo = FeatureConfigRepository(feature_config='app/assets/feature.yml')
    feature = feature_repo.get('source.attach')

    # Catalog lookup succeeds; step resolution returns a mocked event.
    mock_event = mock.Mock()
    project_service = mock.Mock()
    project_service.get.return_value = mock.Mock(
        id='default',
        h5_file='.lit_review/lit_review.h5',
    )

    def get_dependency(service_id, *flags):
        if service_id == 'project_service':
            return project_service
        return mock_event

    feature_context = LitReviewFeatureContext.from_domain(
        feature,
        get_dependency=get_dependency,
        get_project_dependency=lambda project_id, h5_file: get_dependency,
    )

    # Build a request as the CLI would, with -n/--name supplied.
    request = RequestContext(data={
        'project_id': 'default',
        'id': '4cfaeea5-869a-444a-8a51-7680812c118d',
        'file': '/tmp/2002.11054v2.pdf',
        'name': 'custom_name.pdf',
    })
    feature_context.execute_feature(request)

    # The raw name value reaches the event unchanged via the request merge.
    _, call_kwargs = mock_event.execute.call_args
    assert call_kwargs['name'] == 'custom_name.pdf'


# ** test: test_default_store_reachable_after_bootstrap
def test_default_store_reachable_after_bootstrap(app_home):
    '''
    An existing .lit_review/lit_review.h5 store is reachable as default.
    '''

    # Seed a source in the legacy store path before any catalog file exists.
    h5_file = app_home / '.lit_review' / 'lit_review.h5'
    h5_file.parent.mkdir(parents=True)
    source_repo = SourceH5Repository(h5_file=str(h5_file))
    source = SourceAggregate(
        id='seed-source',
        medium='pdf',
        year=2020,
        title='Seeded Source',
    )
    source.add_author('Seed, A.')
    source_repo.save(source)

    # Listing sources on default bootstraps the catalog without a manual edit.
    session = build_app()
    result = session.run('source.list', data={'project_id': 'default'})

    # The pre-existing source is visible through the default project.
    assert any(item.id == 'seed-source' for item in result)
    catalog = Path('.lit_review') / 'projects.yml'
    assert catalog.is_file()


# ** test: test_project_add_writes_catalog_and_h5
def test_project_add_writes_catalog_and_h5(app_home):
    '''
    project add writes a catalog entry and creates an empty HDF5 file.
    '''

    # Add a named project whose store lives under the isolated home.
    session = build_app()
    h5_file = str(app_home / 'stores' / 'paper.h5')
    result = session.run(
        'project.add',
        data={
            'id': 'paper',
            'name': 'Paper',
            'h5_file': h5_file,
        },
    )

    # The catalog record and the empty store file both exist.
    assert result.id == 'paper'
    assert result.name == 'Paper'
    assert result.h5_file == h5_file
    assert result.created_at
    assert Path(h5_file).is_file()


# ** test: test_project_list_and_show_do_not_open_store
def test_project_list_and_show_do_not_open_store(app_home):
    '''
    project list and project show read the catalog only.
    '''

    # Add a project, then remove its HDF5 file so a store open would fail.
    session = build_app()
    h5_file = app_home / 'stores' / 'paper.h5'
    session.run(
        'project.add',
        data={
            'id': 'paper',
            'name': 'Paper',
            'h5_file': str(h5_file),
        },
    )
    h5_file.unlink()

    # Catalog reads still succeed without opening the research-graph store.
    listed = session.run('project.list', data={})
    shown = session.run('project.show', data={'id': 'paper'})
    assert any(item.id == 'paper' for item in listed)
    assert shown.id == 'paper'
    assert shown.name == 'Paper'


# ** test: test_missing_project_id_fails_before_store_write
def test_missing_project_id_fails_before_store_write(app_home):
    '''
    A store-backed feature with no project_id fails before any store write.
    '''

    # Capture whether the default store path is created during the failed add.
    session = build_app()
    h5_file = app_home / '.lit_review' / 'lit_review.h5'

    # Execute source.add without project_id.
    with pytest.raises(TiferetAPIError) as exc_info:
        session.run(
            'source.add',
            data={
                'medium': 'pdf',
                'authors': ['Lattner, C.'],
                'year': 2020,
                'title': 'MLIR',
            },
        )

    # The missing-parameter error is raised and no store file is written.
    assert exc_info.value.error_code == COMMAND_PARAMETER_REQUIRED_ID
    assert h5_file.exists() is False


# ** test: test_unknown_project_id_fails_before_store_write
def test_unknown_project_id_fails_before_store_write(app_home):
    '''
    A store-backed feature with an unknown project_id fails before any write.
    '''

    # Bootstrap the catalog, then try a store write against a missing id.
    session = build_app()
    session.run('project.list', data={})
    h5_file = app_home / '.lit_review' / 'lit_review.h5'
    existed = h5_file.exists()
    mtime = h5_file.stat().st_mtime if existed else None

    with pytest.raises(TiferetAPIError) as exc_info:
        session.run(
            'source.add',
            data={
                'project_id': 'missing',
                'medium': 'pdf',
                'authors': ['Lattner, C.'],
                'year': 2020,
                'title': 'MLIR',
            },
        )

    # PROJECT_NOT_FOUND is raised and the default store is untouched.
    assert exc_info.value.error_code == PROJECT_NOT_FOUND_ID
    if existed:
        assert h5_file.stat().st_mtime == mtime
    else:
        assert h5_file.exists() is False


# ** test: test_source_add_is_isolated_by_project
def test_source_add_is_isolated_by_project(app_home):
    '''
    source add against project A does not appear when listing project B.
    '''

    # Create two catalogued stores.
    session = build_app()
    session.run(
        'project.add',
        data={
            'id': 'alpha',
            'name': 'Alpha',
            'h5_file': str(app_home / 'alpha.h5'),
        },
    )
    session.run(
        'project.add',
        data={
            'id': 'beta',
            'name': 'Beta',
            'h5_file': str(app_home / 'beta.h5'),
        },
    )

    # Add a source only to project alpha.
    added = session.run(
        'source.add',
        data={
            'project_id': 'alpha',
            'medium': 'pdf',
            'authors': ['Lattner, C.'],
            'year': 2020,
            'title': 'MLIR',
        },
    )

    # Alpha lists the source; beta does not.
    alpha_sources = session.run('source.list', data={'project_id': 'alpha'})
    beta_sources = session.run('source.list', data={'project_id': 'beta'})
    assert any(item.id == added.id for item in alpha_sources)
    assert beta_sources == []


# ** test: test_project_add_does_not_require_store_project_id
def test_project_add_does_not_require_store_project_id(app_home):
    '''
    project add does not require a store project_id.
    '''

    # Add a project with only catalog fields.
    session = build_app()
    result = session.run(
        'project.add',
        data={
            'id': 'side',
            'name': 'Side Inquiry',
            'h5_file': str(app_home / 'side.h5'),
        },
    )

    # The command succeeds without a store project_id on the request.
    assert result.id == 'side'


# ** test: test_app_session_uses_lit_review_feature_context
def test_app_session_uses_lit_review_feature_context(app_home):
    '''
    App session construction executes features via LitReviewFeatureContext.
    '''

    # Capture the context class the App handler actually constructs.
    constructed = []
    real_from_domain = LitReviewFeatureContext.from_domain

    def capture_from_domain(*args, **kwargs):
        context = real_from_domain(*args, **kwargs)
        constructed.append(context)
        return context

    with mock.patch(
        'app.blueprints.LitReviewFeatureContext.from_domain',
        side_effect=capture_from_domain,
    ):
        session = build_app()
        session.run('project.list', data={})

    # Stock FeatureContext is not the runtime executor for this app.
    assert constructed
    assert type(constructed[0]) is LitReviewFeatureContext
    assert constructed[0].domain.id == 'project.list'


# ** test: test_cli_session_uses_lit_review_feature_context
def test_cli_session_uses_lit_review_feature_context(app_home):
    '''
    CLI session construction executes features via LitReviewFeatureContext.
    '''

    # Capture the context class the CLI handler actually constructs.
    constructed = []
    real_from_domain = LitReviewFeatureContext.from_domain

    def capture_from_domain(*args, **kwargs):
        context = real_from_domain(*args, **kwargs)
        constructed.append(context)
        return context

    with mock.patch(
        'app.blueprints.LitReviewFeatureContext.from_domain',
        side_effect=capture_from_domain,
    ):
        build_cli(argv=['project', 'list'])

    # Stock FeatureContext is not the runtime executor for this app.
    assert constructed
    assert type(constructed[0]) is LitReviewFeatureContext
    assert constructed[0].domain.id == 'project.list'


# ** test: test_source_copy_missing_to_fails_before_store_write
def test_source_copy_missing_to_fails_before_store_write(app_home):
    '''
    source copy without --to fails before any dest store write.
    '''

    # Create origin and dest projects, then copy without dest.
    session = build_app()
    session.run(
        'project.add',
        data={
            'id': 'alpha',
            'name': 'Alpha',
            'h5_file': str(app_home / 'alpha.h5'),
        },
    )
    added = session.run(
        'source.add',
        data={
            'project_id': 'alpha',
            'medium': 'pdf',
            'authors': ['Lattner, C.'],
            'year': 2020,
            'title': 'MLIR',
        },
    )

    with pytest.raises(TiferetAPIError) as exc_info:
        session.run(
            'source.copy',
            data={
                'project_id': 'alpha',
                'id': added.id,
            },
        )

    # Missing --to is a required-parameter error; origin is unchanged.
    assert exc_info.value.error_code == COMMAND_PARAMETER_REQUIRED_ID
    assert session.run('source.list', data={'project_id': 'alpha'})


# ** test: test_source_copy_unknown_dest_fails_through_catalog
def test_source_copy_unknown_dest_fails_through_catalog(app_home):
    '''
    source copy against an unknown dest project fails through catalog lookup.
    '''

    # Create only the origin project.
    session = build_app()
    session.run(
        'project.add',
        data={
            'id': 'alpha',
            'name': 'Alpha',
            'h5_file': str(app_home / 'alpha.h5'),
        },
    )
    added = session.run(
        'source.add',
        data={
            'project_id': 'alpha',
            'medium': 'pdf',
            'authors': ['Lattner, C.'],
            'year': 2020,
            'title': 'MLIR',
        },
    )

    with pytest.raises(TiferetAPIError) as exc_info:
        session.run(
            'source.copy',
            data={
                'project_id': 'alpha',
                'id': added.id,
                'to': 'missing',
            },
        )

    # Dest lookup uses PROJECT_NOT_FOUND; origin is unchanged.
    assert exc_info.value.error_code == PROJECT_NOT_FOUND_ID
    listed = session.run('source.list', data={'project_id': 'alpha'})
    assert any(item.id == added.id for item in listed)


# ** test: test_source_copy_via_app_and_cli
def test_source_copy_via_app_and_cli(app_home):
    '''
    source copy PROJECT_ID SOURCE_ID --to DEST_PROJECT_ID writes dest only.
    '''

    # Create two catalogued stores and a source on origin.
    session = build_app()
    session.run(
        'project.add',
        data={
            'id': 'alpha',
            'name': 'Alpha',
            'h5_file': str(app_home / 'alpha.h5'),
        },
    )
    session.run(
        'project.add',
        data={
            'id': 'beta',
            'name': 'Beta',
            'h5_file': str(app_home / 'beta.h5'),
        },
    )
    added = session.run(
        'source.add',
        data={
            'project_id': 'alpha',
            'medium': 'pdf',
            'authors': ['Lattner, C.'],
            'year': 2020,
            'title': 'MLIR',
        },
    )

    # Copy through the App session, then again through CLI against a second pair.
    copied = session.run(
        'source.copy',
        data={
            'project_id': 'alpha',
            'id': added.id,
            'to': 'beta',
        },
    )
    alpha_sources = session.run('source.list', data={'project_id': 'alpha'})
    beta_sources = session.run('source.list', data={'project_id': 'beta'})
    assert copied.id == added.id
    assert any(item.id == added.id for item in alpha_sources)
    assert any(item.id == added.id for item in beta_sources)

    # CLI copy of a different source uses the same --to dest flag.
    second = session.run(
        'source.add',
        data={
            'project_id': 'alpha',
            'medium': 'book',
            'authors': ['Example, A.'],
            'year': 2021,
            'title': 'Another Work',
        },
    )
    build_cli(argv=['source', 'copy', 'alpha', second.id, '--to', 'beta'])
    beta_sources = session.run('source.list', data={'project_id': 'beta'})
    assert any(item.id == second.id for item in beta_sources)
    assert session.run('source.list', data={'project_id': 'alpha'})

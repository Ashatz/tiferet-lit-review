"""Lit Review Application Blueprint"""

# *** imports

# ** core
from typing import Any, Callable, List, Optional

# ** app
from tiferet import a
from tiferet.assets import TiferetError
from tiferet.blueprints import core
from tiferet.blueprints.cli import (
    build_cli_cache,
    cli_response_handler,
    create_cli_request_context,
    parse_cli_args_handler,
)
from tiferet.contexts.app import AppSessionContext
from tiferet.contexts.cache import CacheContext
from tiferet.contexts.cli import CliSessionContext, get_default_cli_commands
from tiferet.contexts.request import RequestContext

from .contexts.feature import LitReviewFeatureContext
from .di.project import build_project_dependency_getter

# *** constants

# ** constant: interface_id
INTERFACE_ID = 'lit_review'

# ** constant: app_config_file
APP_CONFIG_FILE = 'app/assets/app.yml'

# *** functions

# ** function: create_lit_review_feature_context
def create_lit_review_feature_context(get_dependency: Callable,
        cache: CacheContext,
        feature_id: str,
        get_project_dependency: Callable) -> LitReviewFeatureContext:
    '''
    Resolve a Feature and bind it to a LitReviewFeatureContext.

    :param get_dependency: The catalog service-resolution handler.
    :type get_dependency: Callable
    :param cache: The bootstrap cache used for lazy feature caching.
    :type cache: CacheContext
    :param feature_id: The identifier of the feature to resolve.
    :type feature_id: str
    :param get_project_dependency: Factory for project-scoped get_dependency.
    :type get_project_dependency: Callable
    :return: The lit-review feature context bound to the resolved feature.
    :rtype: LitReviewFeatureContext
    '''

    # Resolve the feature via the lazy-caching get_feature handler.
    feature = core.get_feature(cache, get_dependency)(feature_id)

    # Construct the lit-review feature context, not stock FeatureContext.
    return LitReviewFeatureContext.from_domain(
        feature,
        get_dependency=get_dependency,
        cache=cache,
        parse_parameter=core.parse_parameter,
        get_project_dependency=get_project_dependency,
    )


# ** function: create_lit_review_execute_feature_handler
def create_lit_review_execute_feature_handler(get_dependency: Callable,
        cache: CacheContext,
        resolver) -> Callable:
    '''
    Build the feature-execution handler that constructs LitReviewFeatureContext.

    :param get_dependency: The catalog service-resolution handler.
    :type get_dependency: Callable
    :param cache: The bootstrap cache used for lazy feature caching.
    :type cache: CacheContext
    :param resolver: The catalog feature-level resolver.
    :type resolver: object
    :return: A handler closure executing a feature against a request.
    :rtype: Callable
    '''

    # Build the per-project getter cache once per session.
    get_project_dependency = build_project_dependency_getter(resolver)

    # Return the handler closure bound to the catalog resolver and cache.
    def handler(feature_id: str, request: RequestContext, *flags, **kwargs) -> None:

        # Resolve the feature-bound lit-review context.
        feature_context = create_lit_review_feature_context(
            get_dependency,
            cache,
            feature_id,
            get_project_dependency,
        )

        # Drive execution; the result is accumulated on the request context.
        feature_context.execute_feature(request, *flags, **kwargs)

    # Return the closure.
    return handler


# ** function: compose_lit_review_session_context
def compose_lit_review_session_context(
        context_cls: type,
        app_session,
        cache: CacheContext,
        app_container,
        resolver,
        create_request_handler: Callable,
        response_handler: Callable,
        execute_feature_handler: Callable,
        **extra_kwargs):
    '''
    Compose a session context whose executor is LitReviewFeatureContext.

    Mirrors ``core.compose_session_context`` but places the custom execute
    handler in the handlers mapping. Passing it as extra_kwargs would raise
    because that function already unpacks a stock execute_feature_handler.

    :param context_cls: The context class to construct.
    :type context_cls: type
    :param app_session: The loaded app session domain object.
    :type app_session: object
    :param cache: The bootstrap cache.
    :type cache: CacheContext
    :param app_container: The built app service container.
    :type app_container: object
    :param resolver: The catalog feature-level resolver.
    :type resolver: object
    :param create_request_handler: The request-construction handler.
    :type create_request_handler: Callable
    :param response_handler: The response-building handler.
    :type response_handler: Callable
    :param execute_feature_handler: The lit-review feature-execution handler.
    :type execute_feature_handler: Callable
    :param extra_kwargs: Additional constructor kwargs (e.g. parse_cli_args).
    :type extra_kwargs: dict
    :return: The fully wired session context.
    :rtype: Any
    '''

    # Wire the stock logger/error/request/response handlers plus the custom executor.
    handlers = dict(
        build_logger_handler=core.build_logger_handler(
            cache,
            resolver.get_dependency,
        ),
        execute_feature_handler=execute_feature_handler,
        raise_error_handler=core.raise_error_handler(
            core.get_error(cache, resolver.get_dependency),
        ),
        response_handler=response_handler,
        create_request_handler=create_request_handler,
    )

    # Resolve any remaining injectable collaborators the context class declares.
    collaborators = core.resolve_collaborators(context_cls, app_container)

    # Construct and return the fully wired session context.
    return context_cls.from_domain(
        app_session,
        get_dependency=resolver.get_dependency,
        cache=cache,
        **handlers,
        **collaborators,
        **extra_kwargs,
    )

# *** blueprints

# ** blueprint: build_app
def build_app(app_config: str = APP_CONFIG_FILE) -> AppSessionContext:
    '''
    Build the fully wired lit_review application session context.

    Composes the session through ``compose_session_context`` and overrides
    ``execute_feature_handler`` so store-backed features run on
    ``LitReviewFeatureContext``.

    :param app_config: The app configuration file path.
    :type app_config: str
    :return: The fully wired app session context.
    :rtype: AppSessionContext
    '''

    # Build the bootstrap cache and resolve the app session.
    cache = core.build_cache()
    app_session = core.get_app_session(
        INTERFACE_ID,
        cache,
        app_config=app_config,
    )

    # Build the app container and catalog feature-level resolver.
    app_container = core.build_app_service_container(cache, app_session)
    resolver = core.build_service_resolver(app_container)

    # Override the stock handler so this app never executes via FeatureContext.
    execute_feature_handler = create_lit_review_execute_feature_handler(
        resolver.get_dependency,
        cache,
        resolver,
    )

    # Compose the session with LitReviewFeatureContext as the runtime executor.
    context = compose_lit_review_session_context(
        AppSessionContext,
        app_session,
        cache,
        app_container,
        resolver,
        create_request_handler=core.create_session_request,
        response_handler=core.response_handler,
        execute_feature_handler=execute_feature_handler,
    )

    # Verify the resolved context is a valid AppSessionContext.
    if not isinstance(context, AppSessionContext):
        TiferetError.raise_error(
            a.error.INVALID_APP_SESSION_TYPE_ID,
            interface_id=INTERFACE_ID,
        )

    # Return the validated app session context.
    return context


# ** blueprint: build_cli_session_context
def build_cli_session_context(app_session, cache: CacheContext) -> CliSessionContext:
    '''
    Build a CLI session that executes features through LitReviewFeatureContext.

    :param app_session: The resolved app session definition.
    :type app_session: object
    :param cache: The CLI cache seeded with framework defaults.
    :type cache: CacheContext
    :return: The wired CLI session context.
    :rtype: CliSessionContext
    '''

    # Build the app container and catalog feature-level resolver.
    app_container = core.build_app_service_container(cache, app_session)
    resolver = core.build_service_resolver(app_container)

    # Resolve the CLI event collaborators from the app container.
    list_commands_evt = app_container.get_dependency('list_commands_evt')
    get_parent_args_evt = app_container.get_dependency('get_parent_args_evt')

    # Build the arg-parsing closure from the resolved events and defaults.
    parse_cli_args = parse_cli_args_handler(
        list_commands_evt,
        get_parent_args_evt,
        get_default_cli_commands(cache),
    )

    # Override the stock handler so CLI dispatch uses LitReviewFeatureContext.
    execute_feature_handler = create_lit_review_execute_feature_handler(
        resolver.get_dependency,
        cache,
        resolver,
    )

    # Compose the CLI session with LitReviewFeatureContext as the runtime executor.
    return compose_lit_review_session_context(
        CliSessionContext,
        app_session,
        cache,
        app_container,
        resolver,
        create_request_handler=create_cli_request_context,
        response_handler=cli_response_handler,
        execute_feature_handler=execute_feature_handler,
        parse_cli_args=parse_cli_args,
    )


# ** blueprint: build_cli
def build_cli(argv: Optional[List[str]] = None,
        app_config: str = APP_CONFIG_FILE) -> Any:
    '''
    Build the CLI session context and dispatch argv through its pipeline.

    :param argv: The argument list; defaults to sys.argv[1:] when None.
    :type argv: Optional[List[str]]
    :param app_config: The app configuration file path.
    :type app_config: str
    :return: The response from the feature execution.
    :rtype: Any
    '''

    # Build the CLI cache and resolve the app session.
    cache = build_cli_cache()
    app_session = core.get_app_session(
        INTERFACE_ID,
        cache,
        app_config=app_config,
    )

    # Compose the wired CLI session context.
    cli_context = build_cli_session_context(app_session, cache)

    # Dispatch argv through the CLI session context.
    return cli_context.run(argv)

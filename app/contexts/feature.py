"""Lit Review Feature Context"""

# *** imports

# ** core
from typing import Callable

# ** app
from tiferet.assets import TiferetError
from tiferet.assets.error import COMMAND_PARAMETER_REQUIRED_ID
from tiferet.contexts.cache import CacheContext
from tiferet.contexts.feature import FeatureContext
from tiferet.contexts.request import RequestContext

from ..events.project import PROJECT_NOT_FOUND_ID

# *** constants

# ** constant: catalog_feature_prefix
CATALOG_FEATURE_PREFIX = 'project.'

# ** constant: project_service_id
PROJECT_SERVICE_ID = 'project_service'

# ** constant: transfer_feature_ids
TRANSFER_FEATURE_IDS = (
    'source.copy',
    'source.move',
    'citation.copy',
    'citation.move',
)

# ** constant: dest_service_ids
DEST_SERVICE_IDS = {
    'dest_source_service': 'source_service',
    'dest_citation_service': 'citation_service',
    'dest_activity_service': 'activity_service',
}

# *** contexts

# ** context: lit_review_feature_context
class LitReviewFeatureContext(FeatureContext):
    '''
    Feature executor that binds a catalog Project before store-backed steps run.

    Catalog features (``project.*``) resolve against the catalog container
    only. Every other feature requires ``project_id`` and fails before any
    store write when the id is missing or unknown.
    '''

    # * attribute: get_project_dependency
    get_project_dependency: Callable

    # * init
    def __init__(self,
            get_dependency: Callable,
            cache: CacheContext = None,
            context_data: dict = None,
            parse_parameter: Callable = None,
            get_project_dependency: Callable = None,
        ) -> None:
        '''
        Initialize the lit-review feature context.

        :param get_dependency: The catalog (stock) service-resolution handler.
        :type get_dependency: Callable
        :param cache: The shared cache context.
        :type cache: CacheContext
        :param context_data: Lowest-priority context defaults.
        :type context_data: dict
        :param parse_parameter: Callable used to parse non-$r. parameters.
        :type parse_parameter: Callable
        :param get_project_dependency: Factory returning a project-scoped
            get_dependency after a successful catalog lookup.
        :type get_project_dependency: Callable
        '''

        # Initialize the stock feature context with the catalog resolver.
        super().__init__(
            get_dependency,
            cache=cache,
            context_data=context_data,
            parse_parameter=parse_parameter,
        )

        # Store the project-scoped getter factory injected by the blueprint.
        self.get_project_dependency = get_project_dependency

    # * method: _bind_project_store
    def _bind_project_store(self, request: RequestContext, feature_id: str) -> None:
        '''
        Look up the request project and retarget store-backed resolution.

        :param request: The inbound request carrying ``project_id``.
        :type request: RequestContext
        :param feature_id: The feature identifier used in missing-parameter errors.
        :type feature_id: str
        '''

        # Require project_id before any container build or store write.
        project_id = (request.data or {}).get('project_id')
        if not isinstance(project_id, str) or not project_id.strip():
            TiferetError.raise_error(
                COMMAND_PARAMETER_REQUIRED_ID,
                f'The required parameter project_id for command {feature_id} is missing.',
                parameter='project_id',
                command=feature_id,
            )

        # Look up the catalog row through the unbound catalog container.
        project_service = self.get_dependency(PROJECT_SERVICE_ID)
        project = project_service.get(project_id)
        if project is None:
            TiferetError.raise_error(
                PROJECT_NOT_FOUND_ID,
                f'Project not found: {project_id}.',
                id=project_id,
            )

        # Resolve subsequent steps through a project-scoped h5_file override.
        self.get_dependency = self.get_project_dependency(
            project.id,
            project.h5_file,
        )

    # * method: _bind_dest_store
    def _bind_dest_store(self,
            request: RequestContext,
            feature_id: str,
            catalog_get_dependency: Callable,
        ) -> None:
        '''
        Look up the destination project and inject dest store services.

        Missing destination project fails through the same catalog lookup
        used for origin ``project_id``.

        :param request: The inbound request carrying ``to``.
        :type request: RequestContext
        :param feature_id: The feature identifier used in missing-parameter errors.
        :type feature_id: str
        :param catalog_get_dependency: The unbound catalog service getter.
        :type catalog_get_dependency: Callable
        '''

        # Require --to before any dest container build or store write.
        dest_project_id = (request.data or {}).get('to')
        if not isinstance(dest_project_id, str) or not dest_project_id.strip():
            TiferetError.raise_error(
                COMMAND_PARAMETER_REQUIRED_ID,
                f'The required parameter to for command {feature_id} is missing.',
                parameter='to',
                command=feature_id,
            )

        # Look up the dest catalog row through the unbound catalog container.
        project_service = catalog_get_dependency(PROJECT_SERVICE_ID)
        dest_project = project_service.get(dest_project_id)
        if dest_project is None:
            TiferetError.raise_error(
                PROJECT_NOT_FOUND_ID,
                f'Project not found: {dest_project_id}.',
                id=dest_project_id,
            )

        # Resolve dest store services from a project-scoped h5_file override.
        dest_get_dependency = self.get_project_dependency(
            dest_project.id,
            dest_project.h5_file,
        )
        self.context_data = dict(self.context_data or {})
        for dest_key, service_id in DEST_SERVICE_IDS.items():
            self.context_data[dest_key] = dest_get_dependency(service_id)

    # * method: execute_feature
    def execute_feature(self, request: RequestContext, *flags, **kwargs):
        '''
        Bind the project store when needed, then execute the feature.

        :param request: The request context object.
        :type request: RequestContext
        :param flags: Execution flags forwarded to the stock executor.
        :type flags: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        '''

        # Catalog commands do not bind a research store.
        feature = self.domain
        if not (feature.id or '').startswith(CATALOG_FEATURE_PREFIX):
            catalog_get_dependency = self.get_dependency
            self._bind_project_store(request, feature.id)
            self.context_data = dict(self.context_data or {})
            self.context_data['project_service'] = catalog_get_dependency(
                PROJECT_SERVICE_ID,
            )
            self.context_data['get_project_dependency'] = self.get_project_dependency
            if feature.id in TRANSFER_FEATURE_IDS:
                self._bind_dest_store(
                    request,
                    feature.id,
                    catalog_get_dependency,
                )

        # Delegate step execution to the stock feature loop.
        super().execute_feature(request, *flags, **kwargs)

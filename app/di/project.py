"""Lit Review Project-Scoped Dependency Resolution"""

# *** imports

# ** core
from typing import Callable, Dict, List

# ** app
from tiferet.di import (
    DIDynamicServiceContainer,
    DIDynamicServiceResolver,
    ServiceResolver,
)
from tiferet.domain import ServiceDependency

# *** di

# ** di: project_scoped_service_resolver
class ProjectScopedServiceResolver(DIDynamicServiceResolver):
    '''
    Feature-level resolver whose container overrides ``h5_file`` before build.

    Lookup must happen before this container is built or cached. Swapping
    ``h5_file`` on an already-cached Factory provider would leave later
    requests on the wrong file.
    '''

    # * attribute: h5_file
    h5_file: str

    # * init
    def __init__(self,
            di_service,
            h5_file: str,
            parse_parameter: Callable = None,
        ) -> None:
        '''
        Initialize the project-scoped resolver.

        :param di_service: The DI service providing registrations and constants.
        :type di_service: object
        :param h5_file: The bound project's HDF5 path.
        :type h5_file: str
        :param parse_parameter: Optional parameter parser; defaults to identity.
        :type parse_parameter: Callable | None
        '''

        # Initialize the per-flag container cache and DI service.
        super().__init__(di_service, parse_parameter=parse_parameter)

        # Store the project store path used as the h5_file constant.
        self.h5_file = h5_file

    # * method: build_container
    def build_container(self, flags: List[str] = None) -> DIDynamicServiceContainer:
        '''
        Build a container with ``h5_file`` set to this project's path.

        :param flags: The normalized flag list for this container.
        :type flags: List[str] | None
        :return: A new dynamic service container instance.
        :rtype: DIDynamicServiceContainer
        '''

        # Normalize optional flags.
        flags = flags if flags else []

        # Read the registrations and top-level constants from the DI service.
        registrations, constants = self.di_service.list_all()

        # Parse top-level constants, then override h5_file for this project.
        parsed_constants = {
            key: self.parse_parameter(value)
            for key, value in constants.items()
        }
        parsed_constants['h5_file'] = self.h5_file

        # Resolve the effective service dependency for each registration.
        services = {}
        for registration in registrations:

            # Resolve the effective dependency for these flags; skip unresolved.
            dependency = registration.resolve_service(*flags)
            if dependency is None:
                continue

            # Parse the resolved dependency's parameters and key it by id.
            services[registration.id] = ServiceDependency(
                module_path=dependency.module_path,
                class_name=dependency.class_name,
                parameters={
                    key: self.parse_parameter(value)
                    for key, value in (dependency.parameters or {}).items()
                },
            )

        # Return the loaded container with the project store path baked in.
        return DIDynamicServiceContainer(
            services=services,
            constants=parsed_constants,
        )

# *** functions

# ** function: build_project_dependency_getter
def build_project_dependency_getter(resolver: ServiceResolver) -> Callable:
    '''
    Build a cache of per-project ``get_dependency`` callables.

    :param resolver: The catalog (stock) feature-level resolver.
    :type resolver: ServiceResolver
    :return: A callable ``(project_id, h5_file) -> get_dependency``.
    :rtype: Callable
    '''

    # Cache one get_dependency closure per project id.
    project_getters: Dict[str, Callable] = {}

    # Return the lookup/build closure bound to the catalog resolver.
    def get_project_dependency(project_id: str, h5_file: str) -> Callable:
        '''
        Return a project-scoped get_dependency, building it on a cache miss.

        :param project_id: The catalog project identifier.
        :type project_id: str
        :param h5_file: The bound project's HDF5 path.
        :type h5_file: str
        :return: A get_dependency callable for that project.
        :rtype: Callable
        '''

        # Return the cached getter when this project has already been bound.
        cached = project_getters.get(project_id)
        if cached is not None:
            return cached

        # Build a resolver that injects h5_file before the container is cached.
        scoped = ProjectScopedServiceResolver(
            di_service=resolver.di_service,
            h5_file=h5_file,
            parse_parameter=resolver.parse_parameter,
        )

        # Reuse the app-level container under the 'app' flag.
        app_container = resolver.get_container('app')
        if app_container is not None:
            scoped.add_container(app_container, 'app')

        # Cache and return the project-scoped getter.
        project_getters[project_id] = scoped.get_dependency
        return scoped.get_dependency

    # Return the factory closure.
    return get_project_dependency

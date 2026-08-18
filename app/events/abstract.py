"""Lit Review Abstract Events"""

# *** imports

# ** core
from typing import List, Optional

# ** app
from tiferet import DomainEvent

from ..domain.abstract import Abstract
from ..domain.abstract_theme import AbstractTheme
from ..interfaces.abstract import AbstractService
from ..interfaces.abstract_theme import AbstractThemeService
from ..interfaces.synthesis import AbstractSynthesisService
from ..interfaces.theme import ThemeService
from ..mappers.abstract import AbstractAggregate, AbstractResponse
from ..mappers.abstract_theme import AbstractThemeAggregate
from .theme import THEME_NOT_FOUND_ID

# *** constants

# ** constant: abstract_not_found_id
ABSTRACT_NOT_FOUND_ID = 'ABSTRACT_NOT_FOUND'

# *** events

# ** event: abstract_event
class AbstractEvent(DomainEvent):
    '''
    Base event providing the shared AbstractService dependency.
    '''

    # * attribute: abstract_service
    abstract_service: AbstractService

    # * init
    def __init__(self, abstract_service: AbstractService) -> None:
        '''
        Initialize the AbstractEvent.

        :param abstract_service: The abstract service dependency.
        :type abstract_service: AbstractService
        '''

        # Set the abstract service dependency.
        self.abstract_service = abstract_service

# ** event: add_abstract
class AddAbstract(AbstractEvent):
    '''
    Register a new Abstract with an empty body until an editorial write or
    synthesis.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name'])
    def execute(self, name: str, body: Optional[str] = None, **kwargs) -> Abstract:
        '''
        Add a new abstract.

        :param name: The short label for the argument brief.
        :type name: str
        :param body: Optional initial body; empty when omitted.
        :type body: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The created abstract.
        :rtype: Abstract
        '''

        # Create and save the abstract aggregate with empty synthesis defaults.
        new_abstract = AbstractAggregate(
            name=name,
            body=body or '',
            theme_count=0,
        )
        self.abstract_service.save(new_abstract)

        # Return the newly created abstract.
        return new_abstract

# ** event: get_abstract
class GetAbstract(AbstractEvent):
    '''
    Retrieve an Abstract by its ID.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> Abstract:
        '''
        Retrieve an abstract by ID.

        :param id: The abstract identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The abstract.
        :rtype: Abstract
        '''

        # Retrieve the abstract from the service.
        abstract = self.abstract_service.get(id)

        # Verify the abstract exists.
        self.verify(
            abstract is not None,
            ABSTRACT_NOT_FOUND_ID,
            message=f'Abstract not found: {id}.',
            id=id,
        )

        # Return the abstract.
        return abstract

# ** event: list_abstracts
class ListAbstracts(AbstractEvent):
    '''
    List all abstracts.
    '''

    # * method: execute
    def execute(self, name: Optional[str] = None, **kwargs) -> List[Abstract]:
        '''
        List abstracts, optionally filtered by name.

        :param name: Optional abstract name to match exactly.
        :type name: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The matching abstracts.
        :rtype: List[Abstract]
        '''

        # Return abstracts from the service, applying the optional name filter.
        return self.abstract_service.list(name=name)

# ** event: list_abstract_themes
class ListAbstractThemes(DomainEvent):
    '''
    List all theme joins belonging to a given abstract, in insertion order.
    '''

    # * attribute: abstract_theme_service
    abstract_theme_service: AbstractThemeService

    # * init
    def __init__(self, abstract_theme_service: AbstractThemeService) -> None:
        '''
        Initialize the ListAbstractThemes event.

        :param abstract_theme_service: The abstract-theme service dependency.
        :type abstract_theme_service: AbstractThemeService
        '''

        # Set the abstract-theme service dependency.
        self.abstract_theme_service = abstract_theme_service

    # * method: execute
    @DomainEvent.parameters_required(['abstract_id'])
    def execute(self, abstract_id: str, **kwargs) -> List[AbstractTheme]:
        '''
        List all theme joins for an abstract.

        :param abstract_id: The abstract identifier to filter joins by.
        :type abstract_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The joins belonging to the abstract, in insertion order.
        :rtype: List[AbstractTheme]
        '''

        # Return the joins filtered by abstract_id.
        return self.abstract_theme_service.list(abstract_id=abstract_id)

# ** event: link_theme_to_abstract
class LinkThemeToAbstract(DomainEvent):
    '''
    Include a theme in an abstract as a structural fact.

    Default linking creates the join and increments theme_count without
    rewriting body. Synthesis runs only when include_synthesis is true. An
    existing (abstract_id, theme_id) pair is idempotent and returns the
    current abstract unchanged.
    '''

    # * attribute: abstract_service
    abstract_service: AbstractService

    # * attribute: abstract_theme_service
    abstract_theme_service: AbstractThemeService

    # * attribute: theme_service
    theme_service: ThemeService

    # * attribute: abstract_synthesis_service
    abstract_synthesis_service: AbstractSynthesisService

    # * init
    def __init__(self,
            abstract_service: AbstractService,
            abstract_theme_service: AbstractThemeService,
            theme_service: ThemeService,
            abstract_synthesis_service: AbstractSynthesisService,
        ) -> None:
        '''
        Initialize the LinkThemeToAbstract event.

        :param abstract_service: The abstract service dependency.
        :type abstract_service: AbstractService
        :param abstract_theme_service: The abstract-theme service dependency.
        :type abstract_theme_service: AbstractThemeService
        :param theme_service: The theme service dependency.
        :type theme_service: ThemeService
        :param abstract_synthesis_service: Injected synthesizer (DI-swappable).
        :type abstract_synthesis_service: AbstractSynthesisService
        '''

        # Set all injected dependencies.
        self.abstract_service = abstract_service
        self.abstract_theme_service = abstract_theme_service
        self.theme_service = theme_service
        self.abstract_synthesis_service = abstract_synthesis_service

    # * method: execute
    @DomainEvent.parameters_required(['id', 'theme_id'])
    def execute(self,
            id: str,
            theme_id: str,
            include_synthesis: bool = False,
            **kwargs,
        ) -> Abstract:
        '''
        Link a theme to an abstract; synthesize only when opted in.

        :param id: The abstract identifier.
        :type id: str
        :param theme_id: The theme to include in the abstract.
        :type theme_id: str
        :param include_synthesis: When True, re-synthesize from the full
            joined theme set after creating the join. Defaults to False.
        :type include_synthesis: bool
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The abstract after linking (unchanged on an idempotent re-link).
        :rtype: Abstract
        '''

        # Verify the abstract exists.
        abstract = self.abstract_service.get(id)
        self.verify(
            abstract is not None,
            ABSTRACT_NOT_FOUND_ID,
            message=f'Abstract not found: {id}.',
            id=id,
        )

        # Verify the theme exists.
        theme = self.theme_service.get(theme_id)
        self.verify(
            theme is not None,
            THEME_NOT_FOUND_ID,
            message=f'Theme not found: {theme_id}.',
            id=theme_id,
        )

        # Idempotent: existing (abstract_id, theme_id) returns unchanged.
        existing = self.abstract_theme_service.list(
            abstract_id=id,
            theme_id=theme_id,
        )
        if existing:
            return abstract

        # Save the new join as a structural fact.
        new_join = AbstractThemeAggregate(
            abstract_id=id,
            theme_id=theme_id,
        )
        self.abstract_theme_service.save(new_join)

        # Increment the denormalized theme count without touching the body.
        abstract.set_attribute('theme_count', abstract.theme_count + 1)

        # Opt-in: reload the full theme set and rewrite the body.
        if include_synthesis:
            themes = self._load_joined_themes(id)
            body = self.abstract_synthesis_service.synthesize(
                abstract,
                themes,
            )
            abstract.set_attribute('body', body)

        # Persist the updated abstract aggregate.
        self.abstract_service.save(abstract)

        # Return the updated abstract.
        return abstract

    # * method: _load_joined_themes
    def _load_joined_themes(self, abstract_id: str) -> List:
        '''
        Load every theme currently joined to the abstract, in insertion order.

        :param abstract_id: The abstract whose joins to resolve.
        :type abstract_id: str
        :return: The joined themes in insertion order.
        :rtype: List
        '''

        # Resolve each joined theme, skipping any that can no longer be loaded.
        themes = []
        for join in self.abstract_theme_service.list(abstract_id=abstract_id):
            joined_theme = self.theme_service.get(join.theme_id)
            if joined_theme is not None:
                themes.append(joined_theme)

        # Return the full set in join insertion order.
        return themes

# ** event: show_abstract
class ShowAbstract(AbstractEvent):
    '''
    Display an abstract's body plus each joined theme.
    '''

    # * attribute: abstract_theme_service
    abstract_theme_service: AbstractThemeService

    # * attribute: theme_service
    theme_service: ThemeService

    # * init
    def __init__(self,
            abstract_service: AbstractService,
            abstract_theme_service: AbstractThemeService,
            theme_service: ThemeService,
        ) -> None:
        '''
        Initialize the ShowAbstract event.

        :param abstract_service: The abstract service dependency.
        :type abstract_service: AbstractService
        :param abstract_theme_service: The abstract-theme service dependency.
        :type abstract_theme_service: AbstractThemeService
        :param theme_service: The theme service dependency.
        :type theme_service: ThemeService
        '''

        # Initialize the shared abstract service dependency.
        super().__init__(abstract_service)

        # Set the remaining show dependencies.
        self.abstract_theme_service = abstract_theme_service
        self.theme_service = theme_service

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> Abstract:
        '''
        Show an abstract and its joined themes.

        :param id: The abstract identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The abstract response, including joined themes.
        :rtype: Abstract
        '''

        # Retrieve the abstract and verify it exists.
        abstract = self.abstract_service.get(id)
        self.verify(
            abstract is not None,
            ABSTRACT_NOT_FOUND_ID,
            message=f'Abstract not found: {id}.',
            id=id,
        )

        # Load each joined theme aggregate in join insertion order.
        themes = []
        for join in self.abstract_theme_service.list(abstract_id=id):
            theme = self.theme_service.get(join.theme_id)
            if theme is not None:
                themes.append(theme)

        # Map the abstract aggregate into a response that includes the themes.
        return AbstractResponse.from_aggregate(abstract, themes=themes)

# ** event: update_abstract
class UpdateAbstract(AbstractEvent):
    '''
    Apply an editorial write to an abstract's name and/or body.

    Lets a researcher curate the brief without requiring themes or invoking
    the synthesizer.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self,
            id: str,
            name: Optional[str] = None,
            body: Optional[str] = None,
            **kwargs,
        ) -> Abstract:
        '''
        Update an abstract's name and/or body.

        :param id: The abstract identifier.
        :type id: str
        :param name: The updated abstract name, if provided.
        :type name: Optional[str]
        :param body: The updated brief text, if provided.
        :type body: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated abstract.
        :rtype: Abstract
        '''

        # Retrieve the abstract and verify it exists.
        abstract = self.abstract_service.get(id)
        self.verify(
            abstract is not None,
            ABSTRACT_NOT_FOUND_ID,
            message=f'Abstract not found: {id}.',
            id=id,
        )

        # Apply an editorial name write when provided.
        if name is not None:
            abstract.set_attribute('name', name)

        # Apply an editorial body write when provided.
        if body is not None:
            abstract.set_attribute('body', body)

        # Persist the updated abstract aggregate.
        self.abstract_service.save(abstract)

        # Return the updated abstract.
        return abstract

# ** event: synthesize_abstract
class SynthesizeAbstract(DomainEvent):
    '''
    Rebuild an abstract's body from its current joined theme set.

    Synthesis is an explicit editorial/computational act, not a side effect of
    forming a join.
    '''

    # * attribute: abstract_service
    abstract_service: AbstractService

    # * attribute: abstract_theme_service
    abstract_theme_service: AbstractThemeService

    # * attribute: theme_service
    theme_service: ThemeService

    # * attribute: abstract_synthesis_service
    abstract_synthesis_service: AbstractSynthesisService

    # * init
    def __init__(self,
            abstract_service: AbstractService,
            abstract_theme_service: AbstractThemeService,
            theme_service: ThemeService,
            abstract_synthesis_service: AbstractSynthesisService,
        ) -> None:
        '''
        Initialize the SynthesizeAbstract event.

        :param abstract_service: The abstract service dependency.
        :type abstract_service: AbstractService
        :param abstract_theme_service: The abstract-theme service dependency.
        :type abstract_theme_service: AbstractThemeService
        :param theme_service: The theme service dependency.
        :type theme_service: ThemeService
        :param abstract_synthesis_service: Injected synthesizer (DI-swappable).
        :type abstract_synthesis_service: AbstractSynthesisService
        '''

        # Set all injected dependencies.
        self.abstract_service = abstract_service
        self.abstract_theme_service = abstract_theme_service
        self.theme_service = theme_service
        self.abstract_synthesis_service = abstract_synthesis_service

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> Abstract:
        '''
        Re-synthesize an abstract from all currently joined themes.

        :param id: The abstract identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The abstract after synthesis.
        :rtype: Abstract
        '''

        # Retrieve the abstract and verify it exists.
        abstract = self.abstract_service.get(id)
        self.verify(
            abstract is not None,
            ABSTRACT_NOT_FOUND_ID,
            message=f'Abstract not found: {id}.',
            id=id,
        )

        # Load joins and resolve each theme in insertion order.
        themes = []
        for join in self.abstract_theme_service.list(abstract_id=id):
            theme = self.theme_service.get(join.theme_id)
            if theme is not None:
                themes.append(theme)

        # Run the injected synthesizer and write the body.
        body = self.abstract_synthesis_service.synthesize(abstract, themes)
        abstract.set_attribute('body', body)
        self.abstract_service.save(abstract)

        # Return the updated abstract.
        return abstract

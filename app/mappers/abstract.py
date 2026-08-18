"""Lit Review Abstract Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict, List, Optional

# ** infra
from pydantic import Field
from tiferet_h5 import NodeObject

# ** app
from tiferet.mappers.core import Aggregate, TransferObject

from ..domain.abstract import Abstract, AbstractTheme
from ..domain.theme import Theme

# *** mappers

# ** mapper: abstract_aggregate
class AbstractAggregate(Abstract, Aggregate):
    '''
    Mutable aggregate for the Abstract domain object.
    '''

    # * method: add_theme
    def add_theme(self, theme_id: str) -> bool:
        '''
        Include a theme in this abstract.

        Idempotent: an already-joined theme_id is left unchanged.

        :param theme_id: The theme identifier to include.
        :type theme_id: str
        :return: True when a new join was added, otherwise False.
        :rtype: bool
        '''

        # Leave an existing join unchanged.
        if any(theme.theme_id == theme_id for theme in self.themes):
            return False

        # Create the value object as part of this abstract's lifecycle.
        join = AbstractTheme(theme_id=theme_id)

        # Append through validated mutation so the parent owns the collection.
        self.set_attribute('themes', [*self.themes, join])
        self.set_attribute('theme_count', self.theme_count + 1)

        # Report that a new join was formed.
        return True

    # * method: rename
    def rename(self, name: str) -> None:
        '''
        Apply an editorial write to the abstract name.

        :param name: The updated abstract name.
        :type name: str
        '''

        # Assign the new name through validated mutation.
        self.set_attribute('name', name)

    # * method: set_body
    def set_body(self, body: str) -> None:
        '''
        Apply an editorial or synthesized write to the abstract body.

        :param body: The updated brief text.
        :type body: str
        '''

        # Assign the new body through validated mutation.
        self.set_attribute('body', body)


# ** mapper: abstract_node_object
class AbstractNodeObject(Abstract, NodeObject):
    '''
    HDF5 node mapper for Abstract: one HDF5 group per abstract, with abstract
    fields stored as node attributes. Owned theme joins are stored as theme
    identifier strings.
    '''

    # * method: to_attrs
    def to_attrs(self, role: str = 'to_h5.attrs', **overrides) -> Dict[str, Any]:
        '''
        Serialize abstract attributes, storing themes as theme-id strings.

        :param role: Serialization role forwarded to ``to_primitive``.
        :type role: str
        :param overrides: Additional key-value pairs merged into the result.
        :type overrides: dict
        :return: A flat dict of attribute name to value pairs.
        :rtype: Dict[str, Any]
        '''

        # Serialize through the node-object base, then flatten owned joins.
        attrs = super().to_attrs(role=role, **overrides)
        attrs['themes'] = [theme.theme_id for theme in self.themes]
        return attrs

    # * method: from_attrs (static)
    @classmethod
    def from_attrs(cls, attrs: Dict[str, Any], **overrides) -> 'AbstractNodeObject':
        '''
        Reconstruct an abstract node object, mapping stored ids to AbstractTheme.

        :param attrs: HDF5 node attribute name-value pairs.
        :type attrs: Dict[str, Any]
        :param overrides: Additional key-value pairs that take priority.
        :type overrides: dict
        :return: The abstract node object.
        :rtype: AbstractNodeObject
        '''

        # Map stored theme-id strings onto the value-object field shape.
        data = dict(attrs)
        themes = data.get('themes', [])
        if hasattr(themes, 'tolist'):
            themes = themes.tolist()
        mapped: List[Any] = []
        for theme in themes or []:
            if isinstance(theme, bytes):
                theme = theme.decode('utf-8')
            elif hasattr(theme, 'item'):
                theme = theme.item()
                if isinstance(theme, bytes):
                    theme = theme.decode('utf-8')
            mapped.append({'theme_id': str(theme)})
        data['themes'] = mapped

        # Delegate bytes and numpy-scalar normalization to the node-object base.
        return super().from_attrs(data, **overrides)

    # * method: map
    def map(self, target: type, **overrides) -> AbstractAggregate:
        '''
        Map this node object onto an abstract aggregate via add_theme.

        :param target: The aggregate class to construct.
        :type target: type
        :param overrides: Additional keyword arguments merged into the data.
        :type overrides: dict
        :return: The rehydrated abstract aggregate.
        :rtype: AbstractAggregate
        '''

        # Build the aggregate without joins, then restore each owned theme.
        themes = list(self.themes)
        abstract = super().map(target, themes=[], theme_count=0, **overrides)
        for theme in themes:
            abstract.add_theme(theme.theme_id)

        # Return the rehydrated aggregate.
        return abstract


# ** mapper: abstract_response
class AbstractResponse(Abstract, TransferObject):
    '''
    Transfer object for abstract CLI/API responses.

    Extends Abstract so the brief and owned joins serialize natively; adds
    the resolved Theme objects when a show/display needs more than the
    join identifiers.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_data': {
            'exclude': {'created_at'},
        },
    }

    # * attribute: linked_themes
    linked_themes: List[Theme] = Field(
        default_factory=list,
        description='Resolved Theme objects included on show/display responses.',
    )

    # * method: from_aggregate (static)
    @staticmethod
    def from_aggregate(
            abstract: AbstractAggregate,
            themes: Optional[List[Theme]] = None,
        ) -> 'AbstractResponse':
        '''
        Map an AbstractAggregate into an AbstractResponse.

        :param abstract: The abstract aggregate to map.
        :type abstract: AbstractAggregate
        :param themes: Optional resolved themes to include on the response.
        :type themes: Optional[List[Theme]]
        :return: The abstract response transfer object.
        :rtype: AbstractResponse
        '''

        # Delegate to TransferObject.from_model, attaching themes when given.
        return AbstractResponse.from_model(
            abstract,
            linked_themes=themes or [],
        )

"""Lit Review Citation Style Configuration Repository"""

# *** imports

# ** core
from typing import TYPE_CHECKING, Optional

# ** app
from tiferet.repos.core import ConfigurationRepository

from ..interfaces.citation_style import CitationStyleRuleService
from ..mappers.citation_style import CitationStyleRuleConfigObject

if TYPE_CHECKING:
    from ..domain.citation_style import CitationStyleRule

# *** repos

# ** repo: citation_style_config_repository
class CitationStyleConfigRepository(CitationStyleRuleService, ConfigurationRepository):
    '''
    YAML-backed repository for declared citation-style rulebooks.
    '''

    # * init
    def __init__(self, citation_style_config: str, encoding: str = 'utf-8') -> None:
        '''
        Initialize the citation style configuration repository.

        :param citation_style_config: Path to the citation styles YAML file.
        :type citation_style_config: str
        :param encoding: File encoding.
        :type encoding: str
        '''

        # Initialize the configuration repository base.
        ConfigurationRepository.__init__(
            self,
            config_file=citation_style_config,
            encoding=encoding,
        )

    # * method: get_rule
    def get_rule(self, style_id: str) -> Optional['CitationStyleRule']:
        '''
        Retrieve a citation style rule by its style identifier.

        :param style_id: The citation style identifier.
        :type style_id: str
        :return: The citation style rule, or None if not declared.
        :rtype: Optional[CitationStyleRule]
        '''

        # Load the declared styles mapping.
        styles_data = self._load(
            start_node=lambda data: data.get('citation_styles', {})
        )

        # Return None when the style is not declared.
        style_data = styles_data.get(style_id)
        if not style_data:
            return None

        # Map the YAML entry, injecting the mapping key as style_id.
        return CitationStyleRuleConfigObject.model_validate(
            {**style_data, 'style_id': style_id}
        ).map()

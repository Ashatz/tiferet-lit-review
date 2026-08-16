"""Lit Review Citation Style Rule Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict

# ** app
from tiferet.mappers.core import TransferObject

from ..domain.citation_style import CitationStyleRule

# *** mappers

# ** mapper: citation_style_rule_config_object
class CitationStyleRuleConfigObject(CitationStyleRule, TransferObject):
    '''
    YAML configuration representation of a CitationStyleRule.

    style_id is the YAML mapping key, so it is excluded from to_data.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_data': {
            'exclude': {'style_id'},
        },
    }

    # * method: map
    def map(self, **overrides) -> CitationStyleRule:
        '''
        Map the configuration data to a CitationStyleRule domain object.

        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The citation style rule.
        :rtype: CitationStyleRule
        '''

        # Map to the read-only rulebook domain object.
        return super().map(CitationStyleRule, **overrides)

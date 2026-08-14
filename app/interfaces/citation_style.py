"""Lit Review Citation Style Rule Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import Optional

# ** app
from tiferet.interfaces.core import Service

from ..domain.citation_style import CitationStyleRule

# *** interfaces

# ** interface: citation_style_rule_service
class CitationStyleRuleService(Service):
    '''
    Vertical interface for loading declared citation-style rulebooks.
    '''

    # * method: get_rule
    @abstractmethod
    def get_rule(self, style_id: str) -> Optional[CitationStyleRule]:
        '''
        Retrieve a citation style rule by its style identifier.

        :param style_id: The citation style identifier.
        :type style_id: str
        :return: The citation style rule, or None if not declared.
        :rtype: Optional[CitationStyleRule]
        '''
        raise NotImplementedError()

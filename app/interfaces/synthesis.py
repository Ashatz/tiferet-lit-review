"""Lit Review Synthesis Interfaces"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List

# ** app
from tiferet.interfaces.core import Service

from ..domain.abstract import Abstract
from ..domain.citation import Citation
from ..domain.theme import Theme

# *** interfaces

# ** interface: theme_synthesis_service
class ThemeSynthesisService(Service):
    '''
    Vertical interface for synthesizing a theme description from its linked
    citations. Declared separately from ThemeService so implementations
    (naive concat, LLM, etc.) can be swapped via DI without touching
    persistence.
    '''

    # * method: synthesize
    @abstractmethod
    def synthesize(self, theme: Theme, citations: List[Citation]) -> str:
        '''
        Produce a new synthesized_description for a theme given its full
        citation set.

        :param theme: The theme being synthesized (read-oriented).
        :type theme: Theme
        :param citations: All citations currently linked to the theme.
        :type citations: List[Citation]
        :return: The new synthesized description text.
        :rtype: str
        '''
        raise NotImplementedError()


# ** interface: abstract_synthesis_service
class AbstractSynthesisService(Service):
    '''
    Vertical interface for synthesizing an abstract body from its joined
    themes. Sibling of ThemeSynthesisService: a different service and a
    different prompt, swapped via DI without touching persistence.
    '''

    # * method: synthesize
    @abstractmethod
    def synthesize(self, abstract: Abstract, themes: List[Theme]) -> str:
        '''
        Produce a new body for an abstract given its full theme set.

        :param abstract: The abstract being synthesized (read-oriented).
        :type abstract: Abstract
        :param themes: All themes currently joined to the abstract.
        :type themes: List[Theme]
        :return: The new abstract body text.
        :rtype: str
        '''
        raise NotImplementedError()

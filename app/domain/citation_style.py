"""Lit Review Citation Style Rule Domain Model"""

# *** imports

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: citation_style_rule
class CitationStyleRule(DomainObject):
    '''
    The declared rulebook a bibliographic record and locator are rendered
    through to produce an in-text citation and a reference-list entry.
    '''

    # * attribute: style_id
    style_id: str = Field(
        ...,
        description='The citation style identifier (e.g. "apa").',
    )

    # * attribute: author_format
    author_format: str = Field(
        ...,
        description='The author-format formatter name looked up at render time.',
    )

    # * attribute: reference_template
    reference_template: str = Field(
        ...,
        description='Named-placeholder template for the reference-list entry.',
    )

    # * attribute: in_text_template
    in_text_template: str = Field(
        ...,
        description='Named-placeholder template for the in-text citation.',
    )

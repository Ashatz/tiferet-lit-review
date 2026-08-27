"""Lit Review Citation Style Rendering Event Tests"""

# *** imports

# ** infra
import pytest
from unittest import mock

# ** app
from tiferet import DomainEvent

from app.domain.citation_style import CitationStyleRule
from app.events.citation_style import RenderCitation
from app.interfaces.citation import CitationService
from app.interfaces.citation_style import CitationStyleRuleService
from app.interfaces.source import SourceService
from app.mappers.citation import CitationAggregate
from app.mappers.source import SourceAggregate

# *** constants

# ** constant: source_id
SOURCE_ID = 'source-1'

# ** constant: citation_id
CITATION_ID = 'citation-1'

# ** constant: style_id
STYLE_ID = 'apa'

# *** fixtures

# ** fixture: source
@pytest.fixture
def source() -> SourceAggregate:
    '''
    Build a source used for rendering.

    :return: A minimal PDF source.
    :rtype: SourceAggregate
    '''

    # Return a source with one author for the render pipeline.
    source = SourceAggregate(
        id=SOURCE_ID,
        medium='pdf',
        year=2020,
        title='MLIR: A Compiler Infrastructure',
    )
    source.add_author('Lattner, C.')
    return source

# ** fixture: rule
@pytest.fixture
def rule() -> CitationStyleRule:
    '''
    Build an APA-like rendering rulebook.

    :return: A citation style rule.
    :rtype: CitationStyleRule
    '''

    # Return a rulebook that only ever references source and locator fields.
    return CitationStyleRule(
        style_id=STYLE_ID,
        author_format='last_first',
        reference_template='{authors} ({year}). {title}.',
        in_text_template='({authors_short}, {year}, p. {locator})',
    )

# *** tests

# ** test: test_render_citation_is_unaffected_by_title
def test_render_citation_is_unaffected_by_title(source, rule):
    '''
    RenderCitation output is byte-identical whether or not the citation
    carries a title (AC #10) -- rendering reads only Source fields and the
    citation's locator, never the citation title.

    :param source: The source fixture.
    :type source: SourceAggregate
    :param rule: The citation style rule fixture.
    :type rule: CitationStyleRule
    '''

    # Build one dependency set shared by both renders.
    def dependencies() -> dict:
        citation_service = mock.Mock(spec=CitationService)
        source_service = mock.Mock(spec=SourceService)
        citation_style_service = mock.Mock(spec=CitationStyleRuleService)
        source_service.get.return_value = source
        citation_style_service.get_rule.return_value = rule
        return {
            'citation_service': citation_service,
            'source_service': source_service,
            'citation_style_service': citation_style_service,
        }

    # Render a title-less citation.
    untitled_deps = dependencies()
    untitled_deps['citation_service'].get.return_value = CitationAggregate(
        id=CITATION_ID,
        source_id=SOURCE_ID,
        locator='4-4',
        excerpt='Operations are the unit.',
    )
    without_title = DomainEvent.handle(
        RenderCitation,
        dependencies=untitled_deps,
        citation_id=CITATION_ID,
        style_id=STYLE_ID,
    )

    # Render the same citation, now carrying a title.
    titled_deps = dependencies()
    titled_deps['citation_service'].get.return_value = CitationAggregate(
        id=CITATION_ID,
        source_id=SOURCE_ID,
        locator='4-4',
        excerpt='Operations are the unit.',
        title='Operations as the unit of compilation',
    )
    with_title = DomainEvent.handle(
        RenderCitation,
        dependencies=titled_deps,
        citation_id=CITATION_ID,
        style_id=STYLE_ID,
    )

    # Both renderings are byte-identical; only the title field itself differs.
    assert without_title.formatted_reference == with_title.formatted_reference
    assert without_title.in_text_citation == with_title.in_text_citation
    assert without_title.title is None
    assert with_title.title == 'Operations as the unit of compilation'

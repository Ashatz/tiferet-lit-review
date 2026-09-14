"""Lit Review Citation Style Rendering Events"""

# *** imports

# ** core
from collections import defaultdict
import re
from typing import Callable, Dict, Optional

# ** app
from tiferet import DomainEvent

from ..interfaces.citation import CitationService
from ..interfaces.citation_style import CitationStyleRuleService
from ..interfaces.project import ProjectService
from ..interfaces.source import SourceService
from ..mappers.citation import CitationResponse
from .citation import CITATION_NOT_FOUND_ID, citation_for_read, source_for_read

# *** constants

# ** constant: citation_style_not_found_id
CITATION_STYLE_NOT_FOUND_ID = 'CITATION_STYLE_NOT_FOUND'

# *** functions

# ** function: format_template
def format_template(template: str, fields: dict) -> str:
    '''
    Substitute named placeholders, treating missing or None values as empty.

    :param template: A format string with named placeholders.
    :type template: str
    :param fields: The field mapping to substitute.
    :type fields: dict
    :return: The collapsed, stripped rendering.
    :rtype: str
    '''

    # Default missing and None values to an empty string.
    values: Dict[str, str] = defaultdict(str)
    for key, value in fields.items():
        values[key] = '' if value is None else str(value)

    # Substitute, then collapse whitespace and empty-field punctuation.
    rendered = template.format_map(values)
    rendered = re.sub(r'\s+', ' ', rendered)
    while '. .' in rendered:
        rendered = rendered.replace('. .', '.')
    rendered = re.sub(r' \.', '.', rendered)
    return rendered.strip()

# *** events

# ** event: render_citation
class RenderCitation(DomainEvent):
    '''
    Render a citation's source record and locator through a declared style rulebook.
    '''

    # * attribute: citation_service
    citation_service: CitationService

    # * attribute: source_service
    source_service: SourceService

    # * attribute: citation_style_service
    citation_style_service: CitationStyleRuleService

    # * init
    def __init__(self,
            citation_service: CitationService,
            source_service: SourceService,
            citation_style_service: CitationStyleRuleService,
        ) -> None:
        '''
        Initialize the RenderCitation event.

        :param citation_service: The citation service dependency.
        :type citation_service: CitationService
        :param source_service: The source service dependency.
        :type source_service: SourceService
        :param citation_style_service: The citation style rule service.
        :type citation_style_service: CitationStyleRuleService
        '''

        # Set all injected dependencies.
        self.citation_service = citation_service
        self.source_service = source_service
        self.citation_style_service = citation_style_service

    # * method: execute
    @DomainEvent.parameters_required(['citation_id', 'style_id'])
    def execute(self,
            citation_id: str,
            style_id: str,
            project_service: Optional[ProjectService] = None,
            get_project_dependency: Optional[Callable] = None,
            **kwargs,
        ) -> CitationResponse:
        '''
        Render a citation in the requested style.

        :param citation_id: The citation identifier.
        :type citation_id: str
        :param style_id: The citation style identifier.
        :type style_id: str
        :param project_service: The catalog project service.
        :type project_service: Optional[ProjectService]
        :param get_project_dependency: Factory for a project-scoped get_dependency.
        :type get_project_dependency: Optional[Callable]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The citation response with both renderings.
        :rtype: CitationResponse
        '''

        # Resolve the citation.
        citation = self.citation_service.get(citation_id)
        self.verify(
            citation is not None,
            CITATION_NOT_FOUND_ID,
            message=f'Citation not found: {citation_id}.',
            id=citation_id,
        )

        # Follow a live pointer to origin excerpt, locator, and Source.
        display = citation_for_read(
            self,
            citation,
            project_service,
            get_project_dependency,
        )
        source = source_for_read(
            self,
            citation,
            self.source_service,
            project_service,
            get_project_dependency,
        )

        # Resolve the style rulebook.
        rule = self.citation_style_service.get_rule(style_id)
        self.verify(
            rule is not None,
            CITATION_STYLE_NOT_FOUND_ID,
            message=f'Citation style not found: {style_id}.',
            id=style_id,
        )

        # Ask the source and citation for derived bibliographic form.
        fields = {
            'authors': source.format_authors(rule.author_format),
            'authors_short': source.authors_short(),
            'year': source.year,
            'title': source.title,
            'container_title': source.container_title or '',
            'publisher': source.publisher or '',
            'locator': display.normalize_locator(),
            'locator_display': display.locator_display(source.locator_convention),
            'medium': source.medium,
        }

        # Apply both templates through the event-local substitution helper.
        formatted_reference = format_template(rule.reference_template, fields)
        in_text_citation = format_template(rule.in_text_template, fields)

        # Return origin excerpt/locator so a link pointer is never quoted.
        return CitationResponse.from_aggregate(
            display,
            formatted_reference=formatted_reference,
            in_text_citation=in_text_citation,
        )

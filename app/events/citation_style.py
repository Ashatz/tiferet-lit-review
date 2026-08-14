"""Lit Review Citation Style Rendering Events"""

# *** imports

# ** core
from collections import defaultdict
import re
from typing import Callable, Dict, List

# ** app
from tiferet import DomainEvent

from ..interfaces.citation import CitationService
from ..interfaces.citation_style import CitationStyleRuleService
from ..interfaces.source import SourceService
from ..mappers.citation import CitationResponse
from .citation import CITATION_NOT_FOUND_ID
from .source import SOURCE_NOT_FOUND_ID

# *** constants

# ** constant: citation_style_not_found_id
CITATION_STYLE_NOT_FOUND_ID = 'CITATION_STYLE_NOT_FOUND'

# ** constant: page_range_locator_pattern
PAGE_RANGE_LOCATOR_PATTERN = re.compile(r'^(\d+)-(\d+)$')

# *** functions

# ** function: last_name
def last_name(author: str) -> str:
    '''
    Extract the family name from a stored author string.

    :param author: A stored author value (``Last, F.`` or ``First Last``).
    :type author: str
    :return: The family name, or an empty string.
    :rtype: str
    '''

    # Treat empty or whitespace-only input as no name.
    stripped = author.strip()
    if not stripped:
        return ''

    # Comma form: family name is the substring before the first comma.
    if ',' in stripped:
        return stripped.split(',', 1)[0].strip()

    # Unpunctuated form: family name is the last whitespace token.
    return stripped.split()[-1]


# ** function: initials
def initials(author: str) -> str:
    '''
    Extract given-name initials from a stored author string.

    :param author: A stored author value (``Last, F.`` or ``First Last``).
    :type author: str
    :return: Space-joined initials (e.g. ``J.``), or an empty string.
    :rtype: str
    '''

    # Treat empty or whitespace-only input as no given name.
    stripped = author.strip()
    if not stripped:
        return ''

    # Comma form: given names sit after the first comma.
    if ',' in stripped:
        given_side = stripped.split(',', 1)[1].strip()
        tokens = given_side.split() if given_side else []
    else:
        tokens = stripped.split()[:-1]

    # Emit one initial per alphabetic given-name token.
    rendered: List[str] = []
    for token in tokens:
        letters = [char for char in token if char.isalpha()]
        if letters:
            rendered.append(f'{letters[0]}.')

    # Join initials with a single space.
    return ' '.join(rendered)


# ** function: format_last_first
def format_last_first(author: str) -> str:
    '''
    Format one author as ``Last, F.``.

    :param author: A stored author value.
    :type author: str
    :return: The last-first rendering, or an empty string.
    :rtype: str
    '''

    # Split into family name and initials.
    last = last_name(author)
    init = initials(author)

    # Combine whichever parts are present.
    if last and init:
        return f'{last}, {init}'
    if last:
        return last
    return ''


# ** function: join_authors
def join_authors(formatted: List[str]) -> str:
    '''
    Join formatted author names with commas and a final ampersand.

    :param formatted: Already-formatted author strings.
    :type formatted: List[str]
    :return: The joined author list, or an empty string.
    :rtype: str
    '''

    # Empty and singleton lists need no joiner.
    if not formatted:
        return ''
    if len(formatted) == 1:
        return formatted[0]

    # Comma-separate all but the last; ampersand before the last.
    return f'{", ".join(formatted[:-1])} & {formatted[-1]}'


# ** function: authors_short
def authors_short(authors: List[str]) -> str:
    '''
    Build the short in-text author form.

    :param authors: Stored author values in source order.
    :type authors: List[str]
    :return: The short author string.
    :rtype: str
    '''

    # Zero, one, two, and three-or-more authors each have a fixed shape.
    if not authors:
        return ''
    if len(authors) == 1:
        return last_name(authors[0])
    if len(authors) == 2:
        return f'{last_name(authors[0])} & {last_name(authors[1])}'
    return f'{last_name(authors[0])} et al.'


# ** function: normalize_locator
def normalize_locator(locator: str) -> str:
    '''
    Collapse a same-page page-range locator to a single page number.

    :param locator: The stored locator (e.g. ``12-12`` or ``12-14``).
    :type locator: str
    :return: The display locator.
    :rtype: str
    '''

    # Collapse equal start/end page-range pairs; leave everything else.
    match = PAGE_RANGE_LOCATOR_PATTERN.match(locator)
    if match and match.group(1) == match.group(2):
        return match.group(1)
    return locator


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


# ** function: identity_author
def identity_author(author: str) -> str:
    '''
    Return an author string unchanged.

    :param author: A stored author value.
    :type author: str
    :return: The author string as given.
    :rtype: str
    '''

    # Unknown author formats fall back to the stored value.
    return author


# *** constants (formatters)

# ** constant: author_formatters
AUTHOR_FORMATTERS: Dict[str, Callable[[str], str]] = {
    'last_first': format_last_first,
}

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
    def execute(self, citation_id: str, style_id: str, **kwargs) -> CitationResponse:
        '''
        Render a citation in the requested style.

        :param citation_id: The citation identifier.
        :type citation_id: str
        :param style_id: The citation style identifier.
        :type style_id: str
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

        # Resolve the parent source.
        source = self.source_service.get(citation.source_id)
        self.verify(
            source is not None,
            SOURCE_NOT_FOUND_ID,
            message=f'Source not found: {citation.source_id}.',
            id=citation.source_id,
        )

        # Resolve the style rulebook.
        rule = self.citation_style_service.get_rule(style_id)
        self.verify(
            rule is not None,
            CITATION_STYLE_NOT_FOUND_ID,
            message=f'Citation style not found: {style_id}.',
            id=style_id,
        )

        # Look up the author formatter; unknown formats pass authors through.
        formatter = AUTHOR_FORMATTERS.get(rule.author_format, identity_author)

        # Build the template field mapping from the bibliographic record.
        fields = {
            'authors': join_authors([formatter(author) for author in source.authors]),
            'authors_short': authors_short(source.authors),
            'year': source.year,
            'title': source.title,
            'container_title': source.container_title or '',
            'publisher': source.publisher or '',
            'locator': normalize_locator(citation.locator),
            'medium': source.medium,
        }

        # Apply both templates through the same substitution helper.
        formatted_reference = format_template(rule.reference_template, fields)
        in_text_citation = format_template(rule.in_text_template, fields)

        # Return the composed, unpersisted response.
        return CitationResponse.from_aggregate(
            citation,
            formatted_reference=formatted_reference,
            in_text_citation=in_text_citation,
        )

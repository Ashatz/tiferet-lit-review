"""Lit Review Source Domain Model"""

# *** imports

# ** core
from time import time
from typing import Any, Dict, List, Optional
from uuid import uuid4
import re

# ** infra
from pydantic import Field, model_validator

# ** app
from tiferet.domain.core import DomainObject

# *** constants

# ** constant: page_range_locator_convention
PAGE_RANGE_LOCATOR_CONVENTION = 'page_range'

# ** constant: source_medium_locator_conventions
SOURCE_MEDIUM_LOCATOR_CONVENTIONS: Dict[str, str] = {
    'pdf': PAGE_RANGE_LOCATOR_CONVENTION,
    'book': PAGE_RANGE_LOCATOR_CONVENTION,
}

# ** constant: locator_convention_patterns
LOCATOR_CONVENTION_PATTERNS: Dict[str, str] = {
    PAGE_RANGE_LOCATOR_CONVENTION: r'^\d+-\d+$',
}

# *** functions

# ** function: is_valid_locator
def is_valid_locator(locator_convention: str, locator: str) -> bool:
    '''
    Check whether a locator's shape matches a given locator convention.

    Adding a new medium only requires a new entry in
    SOURCE_MEDIUM_LOCATOR_CONVENTIONS and, if its locator shape is new, a new
    entry in LOCATOR_CONVENTION_PATTERNS -- never a branch here.

    :param locator_convention: The locator convention name (e.g. "page_range").
    :type locator_convention: str
    :param locator: The locator value to validate.
    :type locator: str
    :return: True if the locator matches the convention's expected shape.
    :rtype: bool
    '''

    # Look up the pattern for the given convention; unknown conventions never validate.
    pattern = LOCATOR_CONVENTION_PATTERNS.get(locator_convention)
    if pattern is None:
        return False

    # Match the locator against the convention's pattern.
    return bool(re.match(pattern, locator))

# *** models

# ** model: source_author
class SourceAuthor(DomainObject):
    '''
    The author name copied onto a Source's bibliographic record.

    This is not an Author entity: it carries no identity, publisher id, or
    life-cycle of its own. It exists so a source can be cited without the
    domain taking on author management.
    '''

    # * attribute: display_name
    display_name: str = Field(
        ...,
        description='The author name as captured on the source (e.g. "Smith, J.").',
    )

    # * method: from_value (static)
    @staticmethod
    def from_value(value: Any) -> 'SourceAuthor':
        '''
        Coerce a stored or supplied author value into a SourceAuthor.

        :param value: A SourceAuthor, a display-name string, or a mapping.
        :type value: Any
        :return: The source author value object.
        :rtype: SourceAuthor
        '''

        # Pass through an already-constructed value object.
        if isinstance(value, SourceAuthor):
            return value

        # Treat a mapping with display_name as a reconstructed value object.
        if isinstance(value, dict) and value.get('display_name') is not None:
            return SourceAuthor(display_name=str(value['display_name']))

        # Treat any other value as a captured display name.
        return SourceAuthor(display_name=str(value))

    # * method: last_name
    def last_name(self) -> str:
        '''
        Extract the family name from the captured display name.

        :return: The family name, or an empty string.
        :rtype: str
        '''

        # Treat empty or whitespace-only input as no name.
        stripped = self.display_name.strip()
        if not stripped:
            return ''

        # Comma form: family name is the substring before the first comma.
        if ',' in stripped:
            return stripped.split(',', 1)[0].strip()

        # Unpunctuated form: family name is the last whitespace token.
        return stripped.split()[-1]

    # * method: initials
    def initials(self) -> str:
        '''
        Extract given-name initials from the captured display name.

        :return: Space-joined initials (e.g. ``J.``), or an empty string.
        :rtype: str
        '''

        # Treat empty or whitespace-only input as no given name.
        stripped = self.display_name.strip()
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

    # * method: format_last_first
    def format_last_first(self) -> str:
        '''
        Format this source author as ``Last, F.``.

        :return: The last-first rendering, or an empty string.
        :rtype: str
        '''

        # Split into family name and initials.
        last = self.last_name()
        init = self.initials()

        # Combine whichever parts are present.
        if last and init:
            return f'{last}, {init}'
        if last:
            return last
        return ''

    # * method: format_name
    def format_name(self, author_format: str) -> str:
        '''
        Format this source author for a named author-format token.

        Unknown tokens fall back to the captured display name so a future
        formatter is an addition here, not a branch in RenderCitation.

        :param author_format: The rulebook author-format token.
        :type author_format: str
        :return: The formatted author name.
        :rtype: str
        '''

        # Dispatch known format tokens; otherwise keep the captured name.
        if author_format == 'last_first':
            return self.format_last_first()
        return self.display_name


# ** model: source
class Source(DomainObject):
    '''
    A work being read: a PDF, a book, or another medium added later, together
    with the bibliographic record needed to cite it correctly.
    '''

    # * attribute: id
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='The unique source identifier, generated if absent.',
    )

    # * attribute: medium
    medium: str = Field(
        ...,
        description='The source medium (e.g. "pdf", "book"), validated against a declared, extensible set.',
    )

    # * attribute: authors
    authors: List[SourceAuthor] = Field(
        ...,
        min_length=1,
        description='The source authors copied onto this record; at least one is required.',
    )

    # * attribute: year
    year: int = Field(
        ...,
        description='The source publication year.',
    )

    # * attribute: title
    title: str = Field(
        ...,
        description='The source title.',
    )

    # * attribute: container_title
    container_title: Optional[str] = Field(
        default=None,
        description='The journal or collection title, where applicable.',
    )

    # * attribute: publisher
    publisher: Optional[str] = Field(
        default=None,
        description='The source publisher, where applicable.',
    )

    # * attribute: locator_convention
    locator_convention: str = Field(
        default='',
        description='The locator shape convention, derived from medium at creation time.',
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )

    # * method: _coerce_authors (validator)
    @model_validator(mode='before')
    @classmethod
    def _coerce_authors(cls, values: dict) -> dict:
        '''
        Coerce supplied author values into SourceAuthor value objects.

        :param values: The raw field values before construction.
        :type values: dict
        :return: The updated field values dict.
        :rtype: dict
        '''

        # Leave missing authors to field validation.
        authors = values.get('authors')
        if authors is None:
            return values

        # Accept strings, mappings, or SourceAuthor instances at the boundary.
        values['authors'] = [SourceAuthor.from_value(author) for author in authors]
        return values

    # * method: _derive_locator_convention (validator)
    @model_validator(mode='before')
    @classmethod
    def _derive_locator_convention(cls, values: dict) -> dict:
        '''
        Validate the medium and derive locator_convention from it when absent.

        :param values: The raw field values before construction.
        :type values: dict
        :return: The updated field values dict.
        :rtype: dict
        '''

        # Verify the medium is one of the declared, supported mediums.
        medium = values.get('medium')
        if medium not in SOURCE_MEDIUM_LOCATOR_CONVENTIONS:
            raise ValueError(
                f'Unsupported source medium {medium!r}; must be one of '
                f'{sorted(SOURCE_MEDIUM_LOCATOR_CONVENTIONS)}.'
            )

        # Derive the locator convention from the medium when not explicitly provided.
        if not values.get('locator_convention'):
            values['locator_convention'] = SOURCE_MEDIUM_LOCATOR_CONVENTIONS[medium]

        # Return the updated values.
        return values

    # * method: join_authors
    def join_authors(self, formatted: List[str]) -> str:
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
        return ', '.join(formatted[:-1]) + ' & ' + formatted[-1]

    # * method: authors_short
    def authors_short(self) -> str:
        '''
        Build the short in-text author form from this source's authors.

        :return: The short author string.
        :rtype: str
        '''

        # Zero, one, two, and three-or-more authors each have a fixed shape.
        if not self.authors:
            return ''
        if len(self.authors) == 1:
            return self.authors[0].last_name()
        if len(self.authors) == 2:
            return f'{self.authors[0].last_name()} & {self.authors[1].last_name()}'
        return f'{self.authors[0].last_name()} et al.'

    # * method: format_authors
    def format_authors(self, author_format: str) -> str:
        '''
        Format every source author for a named author-format token.

        :param author_format: The rulebook author-format token.
        :type author_format: str
        :return: The joined formatted author list.
        :rtype: str
        '''

        # Format each copied author, then join in source order.
        return self.join_authors(
            [author.format_name(author_format) for author in self.authors]
        )

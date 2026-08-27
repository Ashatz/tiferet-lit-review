"""Lit Review Source Domain Model"""

# *** imports

# ** core
from pathlib import Path
from time import time
from typing import Dict, List, Optional
from urllib.parse import urlparse
from uuid import uuid4
import re

# ** infra
from pydantic import Field, field_validator, model_validator

# ** app
from tiferet.domain.core import DomainObject

# *** constants

# ** constant: page_range_locator_convention
PAGE_RANGE_LOCATOR_CONVENTION = 'page_range'
# ** constant: web_locator_convention
WEB_LOCATOR_CONVENTION = 'web_locator'

# ** constant: document_title_slug_max_length
DOCUMENT_TITLE_SLUG_MAX_LENGTH = 32

# ** constant: source_medium_locator_conventions
SOURCE_MEDIUM_LOCATOR_CONVENTIONS: Dict[str, str] = {
    'pdf': PAGE_RANGE_LOCATOR_CONVENTION,
    'book': PAGE_RANGE_LOCATOR_CONVENTION,
    'web': WEB_LOCATOR_CONVENTION,
}

# ** constant: locator_convention_patterns
LOCATOR_CONVENTION_PATTERNS: Dict[str, str] = {
    PAGE_RANGE_LOCATOR_CONVENTION: r'^\d+-\d+$',
    WEB_LOCATOR_CONVENTION: r'^\S(?:.*\S)?$',
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

# ** function: is_valid_source_url
def is_valid_source_url(source_url: str) -> bool:
    '''
    Check whether a source URL is an absolute HTTP(S) URL with a host.

    This is a local syntax check only. It never resolves, fetches, or otherwise
    verifies the URL over the network.

    :param source_url: The researcher-supplied source URL.
    :type source_url: str
    :return: True when the URL has a supported scheme and a host.
    :rtype: bool
    '''

    # Reject whitespace so the persisted URL remains exactly the validated value.
    if any(character.isspace() for character in source_url):
        return False

    # Parse only the URL structure; no network access is involved.
    try:
        parsed = urlparse(source_url)
        return parsed.scheme in {'http', 'https'} and bool(parsed.hostname)
    except ValueError:
        return False

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
        default_factory=list,
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
    # * attribute: source_url
    source_url: Optional[str] = Field(
        default=None,
        description='The optional HTTP(S) location of this source or online edition.',
    )

    # * attribute: locator_convention
    locator_convention: str = Field(
        default='',
        description='The locator shape convention, derived from medium at creation time.',
    )

    # * attribute: document_name
    document_name: Optional[str] = Field(
        default=None,
        description='The API / download filename when a source document is attached.',
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )
    # * method: _validate_source_url (validator)
    @field_validator('source_url')
    @classmethod
    def _validate_source_url(cls, source_url: Optional[str]) -> Optional[str]:
        '''
        Normalize an absent URL and validate a supplied URL locally.

        :param source_url: The optional source URL.
        :type source_url: Optional[str]
        :return: The validated URL, or None when it is absent.
        :rtype: Optional[str]
        '''

        # Collapse blank input to the single absent-url representation.
        if source_url is None or not source_url.strip():
            return None

        # Accept only a syntactically valid HTTP(S) URL; never contact it.
        if not is_valid_source_url(source_url):
            raise ValueError(
                'Source URL must be an absolute HTTP(S) URL with a host and no whitespace.'
            )
        return source_url

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

    # * method: slugify_document_token
    def slugify_document_token(self, value: str) -> str:
        '''
        Build a filesystem-safe underscore slug from a bibliographic token.

        :param value: The raw token to slugify.
        :type value: str
        :return: A lowercase underscore slug, or an empty string.
        :rtype: str
        '''

        # Collapse non-alphanumeric runs to a single underscore and trim edges.
        return re.sub(r'[^a-z0-9]+', '_', value.strip().lower()).strip('_')

    # * method: document_extension
    def document_extension(self, path: Optional[str] = None) -> str:
        '''
        Resolve the download extension from an upload path or this medium.

        :param path: Optional upload path whose suffix takes priority.
        :type path: Optional[str]
        :return: The extension without a leading dot.
        :rtype: str
        '''

        # Prefer the uploaded file's suffix when one is present.
        if path:
            suffix = Path(path).suffix.lstrip('.').strip().lower()
            if suffix:
                return suffix

        # Fall back to the source medium (e.g. pdf -> pdf).
        return self.medium

    # * method: derive_document_name
    def derive_document_name(self, path: Optional[str] = None) -> str:
        '''
        Derive the default API / download name for an attached document.

        :param path: Optional upload path used only for the file extension.
        :type path: Optional[str]
        :return: The derived document name, including extension.
        :rtype: str
        '''

        # Slug the first author's family name; fall back when none is present.
        if self.authors:
            first_author_slug = self.slugify_document_token(self.authors[0].last_name())
        else:
            first_author_slug = ''
        first_author_slug = first_author_slug or 'source'

        # Include et_al only when more than one author is on the record.
        et_al = '_et_al' if len(self.authors) > 1 else ''

        # Shorten the title slug on an underscore boundary when it is long.
        title_slug = self.slugify_document_token(self.title) or 'untitled'
        if len(title_slug) > DOCUMENT_TITLE_SLUG_MAX_LENGTH:
            title_slug = title_slug[:DOCUMENT_TITLE_SLUG_MAX_LENGTH].rstrip('_')
            if '_' in title_slug:
                title_slug = title_slug.rsplit('_', 1)[0]

        # Compose the API name from author, year, title, and extension.
        extension = self.document_extension(path=path)
        return f'{first_author_slug}{et_al}_{self.year}_{title_slug}.{extension}'

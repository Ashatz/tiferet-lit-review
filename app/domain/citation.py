"""Lit Review Citation Domain Model"""

# *** imports

# ** core
from time import time
from typing import Optional, Tuple
from uuid import uuid4
import re

# ** infra
from pydantic import Field, model_validator

# ** app
from tiferet.domain.core import DomainObject

# *** constants

# ** constant: page_range_locator_pattern
PAGE_RANGE_LOCATOR_PATTERN = re.compile(r'^(\d+)-(\d+)$')

# ** constant: citation_type_default
CITATION_TYPE_DEFAULT = 'default'

# ** constant: citation_type_link
CITATION_TYPE_LINK = 'link'

# ** constant: allowed_citation_types
ALLOWED_CITATION_TYPES = (
    CITATION_TYPE_DEFAULT,
    CITATION_TYPE_LINK,
)

# ** constant: citation_type_col_bytes
CITATION_TYPE_COL_BYTES = 16

# ** constant: slide_range_locator_convention
# Not imported from app.domain.source: the domain layer does not import
# across sibling domain modules, so the convention name is duplicated here
# as the shared string identifier the event layer passes in.
SLIDE_RANGE_LOCATOR_CONVENTION = 'slide_range'

# ** constant: max_title_bytes
MAX_TITLE_BYTES = 256

# ** constant: max_excerpt_bytes
MAX_EXCERPT_BYTES = 10_000_000

# ** constant: max_context_note_bytes
MAX_CONTEXT_NOTE_BYTES = 10_000_000

# *** functions

# ** function: parse_citation_link_pointer
def parse_citation_link_pointer(excerpt: str) -> Tuple[str, str]:
    '''
    Split a link citation excerpt into origin project id and citation id.

    :param excerpt: The stored pointer, exactly ``project_id:citation_id``.
    :type excerpt: str
    :return: The origin catalog id and origin citation id.
    :rtype: Tuple[str, str]
    :raises ValueError: If the pointer is not exactly one colon-separated pair.
    '''

    # A pointer is exactly one colon between two non-empty ids.
    if not isinstance(excerpt, str) or excerpt.count(':') != 1:
        raise ValueError(
            'A link citation excerpt must be exactly project_id:citation_id.'
        )
    project_id, citation_id = excerpt.split(':')
    if not project_id or not citation_id:
        raise ValueError(
            'A link citation excerpt must be exactly project_id:citation_id.'
        )

    # Return the origin catalog id and origin citation id.
    return project_id, citation_id

# *** models

# ** model: citation
class Citation(DomainObject):
    '''
    An excerpt or paraphrase pulled from a source, or a live pointer to one,
    together with its locator and enough surrounding context to be understood
    on its own. The atomic unit of evidence in this domain.
    '''

    # * attribute: id
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='The unique citation identifier, generated if absent.',
    )

    # * attribute: source_id
    source_id: str = Field(
        default='',
        description='The identifier of the source this citation was pulled from.',
    )

    # * attribute: locator
    locator: str = Field(
        default='',
        description='The precise locator of the excerpt within its source (e.g. a page range).',
    )

    # * attribute: excerpt
    excerpt: str = Field(
        ...,
        description='The quoted or paraphrased text, or a live origin pointer.',
    )

    # * attribute: type
    type: str = Field(
        default=CITATION_TYPE_DEFAULT,
        description=(
            'Citation capture shape: default stores local evidence; '
            'link stores a live project_id:citation_id pointer in excerpt.'
        ),
    )

    # * attribute: context_note
    context_note: Optional[str] = Field(
        default=None,
        description="An optional note describing the excerpt's surrounding context.",
    )

    # * attribute: title
    title: Optional[str] = Field(
        default=None,
        description=(
            'An optional researcher-authored label for this excerpt, distinct '
            "from the source's bibliographic title."
        ),
    )

    # * attribute: created_at
    created_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix creation timestamp (UTC seconds since epoch).',
    )

    # * method: _normalize_type (validator)
    @model_validator(mode='before')
    @classmethod
    def _normalize_type(cls, values: dict) -> dict:
        '''
        Migrate omit/blank/legacy-missing type to default; reject unknowns.

        :param values: The raw field values before construction.
        :type values: dict
        :return: The updated field values dict.
        :rtype: dict
        '''

        # Only inspect a plain values dict for this construction/assignment call.
        if not isinstance(values, dict):
            return values

        # Decode a stored StringCol value and strip padding before classifying.
        citation_type = values.get('type')
        if isinstance(citation_type, bytes):
            citation_type = citation_type.decode('utf-8')
        if isinstance(citation_type, str):
            citation_type = citation_type.rstrip('\x00').strip()

        # Omit, blank, or legacy-missing type is the default capture shape.
        if citation_type is None or citation_type == '':
            values['type'] = CITATION_TYPE_DEFAULT
            return values

        # Unknown values are rejected rather than coerced.
        if citation_type not in ALLOWED_CITATION_TYPES:
            raise ValueError(
                f'Unknown citation type {citation_type!r}; '
                f'allowed values are {ALLOWED_CITATION_TYPES}.'
            )
        values['type'] = citation_type

        # Return the (possibly updated) values.
        return values

    # * method: _normalize_title (validator)
    @model_validator(mode='before')
    @classmethod
    def _normalize_title(cls, values: dict) -> dict:
        '''
        Treat a blank or whitespace-only title as absent; reject an overlong one.

        :param values: The raw field values before construction.
        :type values: dict
        :return: The updated field values dict.
        :rtype: dict
        '''

        # Only inspect a string title supplied in this construction call.
        if not isinstance(values, dict):
            return values
        title = values.get('title')
        if not isinstance(title, str):
            return values

        # Blank or whitespace-only input carries no title.
        if not title.strip():
            values['title'] = None
            return values

        # A present title is persisted exactly as supplied, within the byte cap.
        if len(title.encode('utf-8')) > MAX_TITLE_BYTES:
            raise ValueError(
                f'Citation title exceeds {MAX_TITLE_BYTES} UTF-8 bytes.'
            )

        # Return the (possibly updated) values.
        return values

    # * method: _validate_text_capacity (validator)
    @model_validator(mode='before')
    @classmethod
    def _validate_text_capacity(cls, values: dict) -> dict:
        '''
        Reject an excerpt or context note exceeding its declared byte capacity.

        Capacity is measured in encoded UTF-8 bytes, matching the fixed-width
        PyTables StringCol storage at the persistence boundary. A value at or
        below the cap round-trips exactly; an over-capacity value is rejected
        here, before persistence, rather than silently truncated.

        :param values: The raw field values before construction.
        :type values: dict
        :return: The unchanged field values dict.
        :rtype: dict
        '''

        # Only inspect a plain values dict for this construction/assignment call.
        if not isinstance(values, dict):
            return values

        # Reject an over-capacity excerpt.
        excerpt = values.get('excerpt')
        if isinstance(excerpt, str) and len(excerpt.encode('utf-8')) > MAX_EXCERPT_BYTES:
            raise ValueError(
                f'Citation excerpt exceeds {MAX_EXCERPT_BYTES} UTF-8 bytes.'
            )

        # Reject an over-capacity context note.
        context_note = values.get('context_note')
        if isinstance(context_note, str) and \
                len(context_note.encode('utf-8')) > MAX_CONTEXT_NOTE_BYTES:
            raise ValueError(
                f'Citation context note exceeds {MAX_CONTEXT_NOTE_BYTES} UTF-8 bytes.'
            )

        # Return the unchanged values.
        return values

    # * method: _validate_citation_shape (validator)
    @model_validator(mode='after')
    def _validate_citation_shape(self):
        '''
        Enforce default capture fields or a well-formed link pointer.

        :return: The validated citation.
        :rtype: Citation
        '''

        # A link stores a live pointer in excerpt; local source/locator unused.
        if self.type == CITATION_TYPE_LINK:
            parse_citation_link_pointer(self.excerpt)
            return self

        # A default citation still requires local source, locator, and excerpt.
        if not self.source_id or not self.locator or not self.excerpt:
            raise ValueError(
                'A default citation requires source_id, locator, and excerpt.'
            )

        # Return the validated citation.
        return self

    # * method: is_link (property)
    @property
    def is_link(self) -> bool:
        '''
        Whether this citation is a live origin pointer rather than local evidence.

        :return: True when type is link.
        :rtype: bool
        '''

        # Link citations resolve excerpt, locator, and Source from origin.
        return self.type == CITATION_TYPE_LINK

    # * method: normalize_locator
    def normalize_locator(self) -> str:
        '''
        Collapse a same-page page-range locator to a single page number.

        :return: The display locator.
        :rtype: str
        '''

        # Collapse equal start/end page-range pairs; leave everything else.
        match = PAGE_RANGE_LOCATOR_PATTERN.match(self.locator)
        if match and match.group(1) == match.group(2):
            return match.group(1)
        return self.locator

    # * method: locator_display
    def locator_display(self, locator_convention: str) -> str:
        '''
        Build this citation's medium-appropriate locator display for rendering.

        Adding a new convention only requires a new branch here, selected by
        the source's declared locator_convention -- never a source.medium
        branch in RenderCitation.

        :param locator_convention: The parent source's declared locator convention.
        :type locator_convention: str
        :return: The formatted locator display (e.g. "p. 9", "Slides 9-11").
        :rtype: str
        '''

        # A presentation slide range reads as "Slide N" or "Slides N-M",
        # never with a page prefix.
        if locator_convention == SLIDE_RANGE_LOCATOR_CONVENTION:
            match = PAGE_RANGE_LOCATOR_PATTERN.match(self.locator)
            if match and match.group(1) != match.group(2):
                return f'Slides {self.locator}'
            return f'Slide {self.normalize_locator()}'

        # Every other convention keeps the existing page-prefixed display.
        return f'p. {self.normalize_locator()}'

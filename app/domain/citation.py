"""Lit Review Citation Domain Model"""

# *** imports

# ** core
from time import time
from typing import Optional
from uuid import uuid4
import re

# ** infra
from pydantic import Field, model_validator

# ** app
from tiferet.domain.core import DomainObject

# *** constants

# ** constant: page_range_locator_pattern
PAGE_RANGE_LOCATOR_PATTERN = re.compile(r'^(\d+)-(\d+)$')

# ** constant: slide_range_locator_convention
# Not imported from app.domain.source: the domain layer does not import
# across sibling domain modules, so the convention name is duplicated here
# as the shared string identifier the event layer passes in.
SLIDE_RANGE_LOCATOR_CONVENTION = 'slide_range'

# ** constant: max_title_bytes
MAX_TITLE_BYTES = 256

# ** constant: max_excerpt_bytes
MAX_EXCERPT_BYTES = 16384

# ** constant: max_context_note_bytes
MAX_CONTEXT_NOTE_BYTES = 16384

# *** models

# ** model: citation
class Citation(DomainObject):
    '''
    An excerpt or paraphrase pulled from a source, together with its locator
    and enough surrounding context to be understood on its own. The atomic
    unit of evidence in this domain.
    '''

    # * attribute: id
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='The unique citation identifier, generated if absent.',
    )

    # * attribute: source_id
    source_id: str = Field(
        ...,
        description='The identifier of the source this citation was pulled from.',
    )

    # * attribute: locator
    locator: str = Field(
        ...,
        description='The precise locator of the excerpt within its source (e.g. a page range).',
    )

    # * attribute: excerpt
    excerpt: str = Field(
        ...,
        description='The quoted or paraphrased text pulled from the source.',
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

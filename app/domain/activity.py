"""Lit Review Activity Domain Model"""

# *** imports

# ** core
from time import time
from typing import List, Optional
from uuid import uuid4

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** constants

# ** constant: source_subject_type
SOURCE_SUBJECT_TYPE = 'source'
# ** constant: citation_subject_type
CITATION_SUBJECT_TYPE = 'citation'
# ** constant: theme_subject_type
THEME_SUBJECT_TYPE = 'theme'

# ** constant: source_added_action
SOURCE_ADDED_ACTION = 'source.added'
# ** constant: source_updated_action
SOURCE_UPDATED_ACTION = 'source.updated'
# ** constant: source_document_attached_action
SOURCE_DOCUMENT_ATTACHED_ACTION = 'source.document_attached'
# ** constant: citation_added_action
CITATION_ADDED_ACTION = 'citation.added'
# ** constant: citation_updated_action
CITATION_UPDATED_ACTION = 'citation.updated'
# ** constant: theme_added_action
THEME_ADDED_ACTION = 'theme.added'
# ** constant: theme_updated_action
THEME_UPDATED_ACTION = 'theme.updated'
# ** constant: theme_synthesized_action
THEME_SYNTHESIZED_ACTION = 'theme.synthesized'
# ** constant: linkage_created_action
LINKAGE_CREATED_ACTION = 'linkage.created'
# ** constant: linkage_retired_action
LINKAGE_RETIRED_ACTION = 'linkage.retired'
# ** constant: linkage_reinstated_action
LINKAGE_REINSTATED_ACTION = 'linkage.reinstated'

# *** models

# ** model: activity_entry
class ActivityEntry(DomainObject):
    '''
    An immutable record of one successful, state-changing act on a Source,
    Citation, Theme, or citation-theme Linkage. Activity history is a
    researcher-facing projection of what happened and when -- never a copy
    of the values that changed, and never a substitute for runtime logging.
    '''

    # * attribute: id
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='The unique activity entry identifier, generated if absent.',
    )

    # * attribute: occurred_at
    occurred_at: int = Field(
        default_factory=lambda: int(time()),
        description='The unix timestamp when the recorded act occurred.',
    )

    # * attribute: action
    action: str = Field(
        ...,
        description='The stable action token (e.g. "source.added").',
    )

    # * attribute: subject_type
    subject_type: str = Field(
        ...,
        description='The primary artifact type this activity is about (e.g. "source").',
    )

    # * attribute: subject_id
    subject_id: str = Field(
        ...,
        description='The primary artifact identifier this activity is about.',
    )

    # * attribute: related_type
    related_type: Optional[str] = Field(
        default=None,
        description='An optional secondary artifact type involved in this activity.',
    )

    # * attribute: related_id
    related_id: Optional[str] = Field(
        default=None,
        description='An optional secondary artifact identifier involved in this activity.',
    )

    # * attribute: changed_fields
    changed_fields: List[str] = Field(
        default_factory=list,
        description='The names only of fields that changed; never their values.',
    )

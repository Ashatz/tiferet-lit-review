"""Lit Review Paper Mappers"""

# *** imports

# ** core
import json
from typing import Any, ClassVar, Dict, List, Optional

# ** infra
from pydantic import Field
from tiferet_h5 import NodeObject

# ** app
from tiferet.mappers.core import Aggregate, TransferObject

from ..domain.citation import Citation
from ..domain.paper import (
    Paper,
    PaperAbstract,
    PaperCitation,
    PaperSection,
    PaperSectionTheme,
)
from ..domain.theme import Theme

# *** mappers

# ** mapper: paper_aggregate
class PaperAggregate(Paper, Aggregate):
    '''
    Mutable aggregate for the Paper domain object.
    '''

    # * method: add_section
    def add_section(
            self,
            title: str,
            theme_ids: Optional[List[str]] = None,
            id: Optional[str] = None,
            content: str = '',
            context: str = '',
        ) -> PaperSection:
        '''
        Append a named section to this paper.

        Themes are copied at create. Content and context start empty unless
        an explicit restore value is supplied.

        :param title: The human heading for this section.
        :type title: str
        :param theme_ids: Optional theme identifiers to include at create.
        :type theme_ids: Optional[List[str]]
        :param id: Optional section identifier to restore.
        :type id: Optional[str]
        :param content: Optional drafted prose to restore.
        :type content: str
        :param context: Optional context note to restore.
        :type context: str
        :return: The newly owned section.
        :rtype: PaperSection
        '''

        # Create the named section as part of this paper's lifecycle.
        kwargs: Dict[str, Any] = {
            'title': title,
            'content': content,
            'context': context,
            'position': self.section_count,
        }
        if id is not None:
            kwargs['id'] = id
        section = PaperSection(**kwargs)

        # Append through validated mutation so the parent owns the collection.
        self.set_attribute('sections', [*self.sections, section])
        self.set_attribute('section_count', self.section_count + 1)

        # Include any initial themes through the same join lifecycle.
        for theme_id in theme_ids or []:
            self.add_theme(section.id, theme_id)

        # Return the owned section, including any themes just joined.
        return self.get_section(section.id)

    # * method: add_theme
    def add_theme(self, section_id: str, theme_id: str) -> bool:
        '''
        Include a theme in an owned section.

        Idempotent per section: an already-joined theme_id is left unchanged.
        A missing section is left unchanged and reported as False.

        :param section_id: The section identifier to join the theme to.
        :type section_id: str
        :param theme_id: The theme identifier to include.
        :type theme_id: str
        :return: True when a new join was added, otherwise False.
        :rtype: bool
        '''

        # Leave a missing section unchanged.
        section = self.get_section(section_id)
        if section is None:
            return False

        # Leave an existing join unchanged.
        if section.has_theme(theme_id):
            return False

        # Replace the owned section with one that includes the new join.
        join = PaperSectionTheme(
            theme_id=theme_id,
            position=section.theme_count,
        )
        updated = PaperSection(
            id=section.id,
            title=section.title,
            content=section.content,
            context=section.context,
            themes=[*section.themes, join],
            theme_count=section.theme_count + 1,
            position=section.position,
            created_at=section.created_at,
        )
        self.set_attribute('sections', [
            updated if item.id == section_id else item
            for item in self.sections
        ])

        # Report that a new join was formed.
        return True

    # * method: update_section
    def update_section(
            self,
            section_id: str,
            content: Optional[str] = None,
            context: Optional[str] = None,
            title: Optional[str] = None,
        ) -> bool:
        '''
        Apply an editorial write to an owned section.

        A missing section is left unchanged and reported as False.

        :param section_id: The section identifier to update.
        :type section_id: str
        :param content: The updated drafted prose, if provided.
        :type content: Optional[str]
        :param context: The updated context note, if provided.
        :type context: Optional[str]
        :param title: The updated heading, if provided.
        :type title: Optional[str]
        :return: True when the section was found and updated.
        :rtype: bool
        '''

        # Leave a missing section unchanged.
        section = self.get_section(section_id)
        if section is None:
            return False

        # Replace the owned section with the editorial writes applied.
        updated = PaperSection(
            id=section.id,
            title=section.title if title is None else title,
            content=section.content if content is None else content,
            context=section.context if context is None else context,
            themes=list(section.themes),
            theme_count=section.theme_count,
            position=section.position,
            created_at=section.created_at,
        )
        self.set_attribute('sections', [
            updated if item.id == section_id else item
            for item in self.sections
        ])

        # Report that the owned section was rewritten.
        return True

    # * method: set_abstract
    def set_abstract(
            self,
            body: str,
            source_abstract_id: Optional[str] = None,
        ) -> None:
        '''
        Set the owned paper brief.

        :param body: The paper brief text.
        :type body: str
        :param source_abstract_id: Optional origin KB Abstract identifier.
        :type source_abstract_id: Optional[str]
        '''

        # Own the brief as part of this paper's lifecycle.
        self.set_attribute(
            'abstract',
            PaperAbstract(
                body=body,
                source_abstract_id=source_abstract_id,
            ),
        )

    # * method: add_citation
    def add_citation(
            self,
            citation_id: str,
            section_id: Optional[str] = None,
        ) -> bool:
        '''
        Record that a KB citation is used in this manuscript.

        Idempotent per citation and optional section scope.

        :param citation_id: The KB citation identifier to include.
        :type citation_id: str
        :param section_id: Optional section this citation is used in.
        :type section_id: Optional[str]
        :return: True when a new join was added, otherwise False.
        :rtype: bool
        '''

        # Leave an existing manuscript join unchanged.
        if self.has_citation(citation_id, section_id=section_id):
            return False

        # Create the value object as part of this paper's lifecycle.
        join = PaperCitation(
            citation_id=citation_id,
            section_id=section_id,
        )
        self.set_attribute('citations', [*self.citations, join])
        self.set_attribute('citation_count', self.citation_count + 1)

        # Report that a new join was formed.
        return True


# ** mapper: paper_node_object
class PaperNodeObject(Paper, NodeObject):
    '''
    HDF5 node mapper for Paper: one HDF5 group per paper, with paper
    fields stored as node attributes. Owned children are stored as JSON
    records so each section keeps its identity, draft, and theme joins.
    '''

    # * method: to_attrs
    def to_attrs(self, role: str = 'to_h5.attrs', **overrides) -> Dict[str, Any]:
        '''
        Serialize paper attributes, storing children as JSON records.

        :param role: Serialization role forwarded to ``to_primitive``.
        :type role: str
        :param overrides: Additional key-value pairs merged into the result.
        :type overrides: dict
        :return: A flat dict of attribute name to value pairs.
        :rtype: Dict[str, Any]
        '''

        # Serialize through the node-object base, then flatten owned children.
        attrs = super().to_attrs(role=role, **overrides)
        attrs['sections'] = [
            json.dumps({
                'id': section.id,
                'title': section.title,
                'content': section.content,
                'context': section.context,
                'theme_ids': [theme.theme_id for theme in section.themes],
            })
            for section in self.sections
        ]
        attrs['citations'] = [
            json.dumps({
                'citation_id': item.citation_id,
                'section_id': item.section_id,
            })
            for item in self.citations
        ]
        if self.abstract is None:
            attrs['abstract'] = ''
        else:
            attrs['abstract'] = json.dumps({
                'body': self.abstract.body,
                'source_abstract_id': self.abstract.source_abstract_id,
            })
        if self.outline_id is None:
            attrs['outline_id'] = ''
        return attrs

    # * method: from_attrs (static)
    @classmethod
    def from_attrs(cls, attrs: Dict[str, Any], **overrides) -> 'PaperNodeObject':
        '''
        Reconstruct a paper node object, mapping stored records to children.

        :param attrs: HDF5 node attribute name-value pairs.
        :type attrs: Dict[str, Any]
        :param overrides: Additional key-value pairs that take priority.
        :type overrides: dict
        :return: The paper node object.
        :rtype: PaperNodeObject
        '''

        # Map stored JSON records onto the value-object field shape.
        data = dict(attrs)
        sections = data.get('sections', [])
        if hasattr(sections, 'tolist'):
            sections = sections.tolist()
        mapped_sections: List[Any] = []
        for position, record in enumerate(sections or []):
            payload = _decode_json_record(record)
            theme_ids = payload.get('theme_ids', [])
            mapped_sections.append({
                'id': payload['id'],
                'title': payload['title'],
                'content': payload.get('content', ''),
                'context': payload.get('context', ''),
                'themes': [
                    {'theme_id': theme_id, 'position': index}
                    for index, theme_id in enumerate(theme_ids)
                ],
                'theme_count': len(theme_ids),
                'position': position,
            })
        data['sections'] = mapped_sections

        # Restore manuscript citation joins.
        citations = data.get('citations', [])
        if hasattr(citations, 'tolist'):
            citations = citations.tolist()
        mapped_citations: List[Any] = []
        for record in citations or []:
            payload = _decode_json_record(record)
            mapped_citations.append({
                'citation_id': payload['citation_id'],
                'section_id': payload.get('section_id'),
            })
        data['citations'] = mapped_citations

        # Restore the optional owned brief and origin outline id.
        abstract = data.get('abstract', '')
        if hasattr(abstract, 'item'):
            abstract = abstract.item()
        if isinstance(abstract, bytes):
            abstract = abstract.decode('utf-8')
        if abstract:
            payload = json.loads(str(abstract))
            data['abstract'] = {
                'body': payload.get('body', ''),
                'source_abstract_id': payload.get('source_abstract_id'),
            }
        else:
            data['abstract'] = None
        outline_id = data.get('outline_id', '')
        if hasattr(outline_id, 'item'):
            outline_id = outline_id.item()
        if isinstance(outline_id, bytes):
            outline_id = outline_id.decode('utf-8')
        data['outline_id'] = outline_id or None

        # Delegate bytes and numpy-scalar normalization to the node-object base.
        return super().from_attrs(data, **overrides)

    # * method: map
    def map(self, target: type, **overrides) -> PaperAggregate:
        '''
        Map this node object onto a paper aggregate via add_section.

        :param target: The aggregate class to construct.
        :type target: type
        :param overrides: Additional keyword arguments merged into the data.
        :type overrides: dict
        :return: The rehydrated paper aggregate.
        :rtype: PaperAggregate
        '''

        # Build the aggregate without children, then restore each owned grouping.
        sections = list(self.sections)
        citations = list(self.citations)
        abstract = self.abstract
        paper = super().map(
            target,
            sections=[],
            section_count=0,
            citations=[],
            citation_count=0,
            abstract=None,
            **overrides,
        )
        for section in sections:
            paper.add_section(
                section.title,
                theme_ids=[theme.theme_id for theme in section.themes],
                id=section.id,
                content=section.content,
                context=section.context,
            )
        if abstract is not None:
            paper.set_abstract(
                abstract.body,
                source_abstract_id=abstract.source_abstract_id,
            )
        for item in citations:
            paper.add_citation(item.citation_id, section_id=item.section_id)

        # Return the rehydrated aggregate.
        return paper


# ** mapper: paper_response
class PaperResponse(Paper, TransferObject):
    '''
    Transfer object for paper CLI/API responses.

    Extends Paper so the title and owned children serialize natively; adds
    the resolved Theme and Citation objects when a show/display needs more
    than the join identifiers.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_data': {
            'exclude': {'created_at'},
        },
    }

    # * attribute: linked_themes
    linked_themes: List[Theme] = Field(
        default_factory=list,
        description='Resolved Theme objects in section-then-join order.',
    )

    # * attribute: linked_citations
    linked_citations: List[Citation] = Field(
        default_factory=list,
        description='Resolved KB Citation objects used in this manuscript.',
    )

    # * method: from_aggregate (static)
    @staticmethod
    def from_aggregate(
            paper: PaperAggregate,
            themes: Optional[List[Theme]] = None,
            citations: Optional[List[Citation]] = None,
        ) -> 'PaperResponse':
        '''
        Map a PaperAggregate into a PaperResponse.

        :param paper: The paper aggregate to map.
        :type paper: PaperAggregate
        :param themes: Optional resolved themes to include on the response.
        :type themes: Optional[List[Theme]]
        :param citations: Optional resolved citations to include on the response.
        :type citations: Optional[List[Citation]]
        :return: The paper response transfer object.
        :rtype: PaperResponse
        '''

        # Delegate to TransferObject.from_model, attaching show payload when given.
        return PaperResponse.from_model(
            paper,
            linked_themes=themes or [],
            linked_citations=citations or [],
        )


# *** helpers

# ** function: decode_json_record
def _decode_json_record(record: Any) -> Dict[str, Any]:
    '''
    Normalize a stored JSON record from HDF5 attributes.

    :param record: A JSON string or HDF5 scalar holding one.
    :type record: Any
    :return: The decoded record payload.
    :rtype: Dict[str, Any]
    '''

    # Coerce bytes and numpy scalars before parsing the JSON payload.
    if isinstance(record, bytes):
        record = record.decode('utf-8')
    elif hasattr(record, 'item'):
        record = record.item()
        if isinstance(record, bytes):
            record = record.decode('utf-8')
    return json.loads(str(record))

"""Lit Review Source Mappers"""

# *** imports

# ** core
from typing import Any, Dict, List, Optional

# ** infra
from pydantic import Field
from tiferet_h5 import NodeObject

# ** app
from tiferet.mappers.core import Aggregate, TransferObject

from ..domain.source import Source, SourceAuthor

# *** mappers

# ** mapper: source_aggregate
class SourceAggregate(Source, Aggregate):
    '''
    Mutable aggregate for the Source domain object.
    '''

    # * method: add_author
    def add_author(self, display_name: str) -> None:
        '''
        Copy an author name onto this source's bibliographic record.

        :param display_name: The author name as printed on the source.
        :type display_name: str
        '''

        # Create the value object as part of this source's lifecycle.
        author = SourceAuthor(display_name=display_name)

        # Append through validated mutation so the parent owns the collection.
        self.set_attribute('authors', [*self.authors, author])

    # * method: attach_document
    def attach_document(self, document_name: str) -> None:
        '''
        Set the API / download name for the attached source document.

        :param document_name: The filename used on download, including extension.
        :type document_name: str
        '''

        # Store the name on the source; bytes live in the repository array.
        self.set_attribute('document_name', document_name)

    # * method: update_record
    def update_record(self,
            authors: Optional[List[str]] = None,
            year: Optional[int] = None,
            title: Optional[str] = None,
            container_title: Optional[str] = None,
            publisher: Optional[str] = None,
            source_url: Optional[str] = None,
            overview_note: Optional[str] = None,
            *,
            clear_container_title: bool = False,
            clear_publisher: bool = False,
            clear_source_url: bool = False,
            clear_overview_note: bool = False,
        ) -> None:
        '''
        Update mutable bibliographic fields on the source.

        Identity fields (id, medium, locator_convention, created_at) are not
        mutable through this method. Optional clears for nullable fields are
        explicit so ``None`` defaults never wipe existing values accidentally.
        An author-list update clears the copied names, then re-adds each one.

        :param authors: The updated author display names, if provided.
        :type authors: Optional[List[str]]
        :param year: The updated publication year, if provided.
        :type year: Optional[int]
        :param title: The updated title, if provided.
        :type title: Optional[str]
        :param container_title: The updated container title, if provided.
        :type container_title: Optional[str]
        :param publisher: The updated publisher, if provided.
        :type publisher: Optional[str]
        :param source_url: The updated source URL, if provided.
        :type source_url: Optional[str]
        :param overview_note: The updated overview note, if provided.
        :type overview_note: Optional[str]
        :param clear_container_title: When True, set container_title to None.
        :type clear_container_title: bool
        :param clear_publisher: When True, set publisher to None.
        :type clear_publisher: bool
        :param clear_source_url: When True, set source_url to None.
        :type clear_source_url: bool
        :param clear_overview_note: When True, set overview_note to None.
        :type clear_overview_note: bool
        '''

        # Replace copied authors through the same add-author lifecycle.
        if authors is not None:
            self.set_attribute('authors', [])
            for display_name in authors:
                self.add_author(display_name)
        if year is not None:
            self.year = year
        if title is not None:
            self.title = title

        # Apply optional field updates or explicit clears.
        if clear_container_title:
            self.container_title = None
        elif container_title is not None:
            self.container_title = container_title
        if clear_publisher:
            self.publisher = None
        elif publisher is not None:
            self.publisher = publisher
        if clear_source_url:
            self.source_url = None
        elif source_url is not None and source_url.strip():
            self.source_url = source_url
        if clear_overview_note:
            self.overview_note = None
        elif overview_note is not None:
            self.overview_note = overview_note if overview_note.strip() else None


# ** mapper: source_node_object
class SourceNodeObject(Source, NodeObject):
    '''
    HDF5 node mapper for Source: one HDF5 group per source, with the
    bibliographic fields stored as node attributes.
    '''

    # * method: to_attrs
    def to_attrs(self, role: str = 'to_h5.attrs', **overrides) -> Dict[str, Any]:
        '''
        Serialize source attributes, storing authors as display-name strings.

        :param role: Serialization role forwarded to ``to_primitive``.
        :type role: str
        :param overrides: Additional key-value pairs merged into the result.
        :type overrides: dict
        :return: A flat dict of attribute name to value pairs.
        :rtype: Dict[str, Any]
        '''

        # Serialize through the node-object base, then flatten authors.
        attrs = super().to_attrs(role=role, **overrides)
        attrs['authors'] = [author.display_name for author in self.authors]
        return attrs

    # * method: from_attrs (static)
    @classmethod
    def from_attrs(cls, attrs: Dict[str, Any], **overrides) -> 'SourceNodeObject':
        '''
        Reconstruct a source node object, mapping stored names to SourceAuthor.

        :param attrs: HDF5 node attribute name-value pairs.
        :type attrs: Dict[str, Any]
        :param overrides: Additional key-value pairs that take priority.
        :type overrides: dict
        :return: The source node object.
        :rtype: SourceNodeObject
        '''

        # Map stored display-name strings onto the value-object field shape.
        data = dict(attrs)
        authors = data.get('authors', [])
        if hasattr(authors, 'tolist'):
            authors = authors.tolist()
        mapped: List[Any] = []
        for author in authors or []:
            if isinstance(author, bytes):
                author = author.decode('utf-8')
            elif hasattr(author, 'item'):
                author = author.item()
                if isinstance(author, bytes):
                    author = author.decode('utf-8')
            mapped.append({'display_name': str(author)})
        data['authors'] = mapped

        # Delegate bytes and numpy-scalar normalization to the node-object base.
        return super().from_attrs(data, **overrides)

    # * method: map
    def map(self, target: type, **overrides) -> SourceAggregate:
        '''
        Map this node object onto a source aggregate via add_author.

        :param target: The aggregate class to construct.
        :type target: type
        :param overrides: Additional keyword arguments merged into the data.
        :type overrides: dict
        :return: The rehydrated source aggregate.
        :rtype: SourceAggregate
        '''

        # Build the aggregate without authors, then restore each copied name.
        authors = list(self.authors)
        source = super().map(target, authors=[], **overrides)
        for author in authors:
            source.add_author(author.display_name)

        # Return the rehydrated aggregate.
        return source


# ** mapper: source_document_response
class SourceDocumentResponse(Source, TransferObject):
    '''
    Transfer object for a retrieved source document: bibliographic name plus bytes.
    '''

    # * attribute: content
    content: bytes = Field(
        default=b'',
        description='The attached source document body.',
    )

    # * method: from_aggregate (static)
    @staticmethod
    def from_aggregate(
            source: SourceAggregate,
            content: bytes,
        ) -> 'SourceDocumentResponse':
        '''
        Map a SourceAggregate and document bytes into a response.

        :param source: The source whose document was retrieved.
        :type source: SourceAggregate
        :param content: The attached document bytes.
        :type content: bytes
        :return: The source document response.
        :rtype: SourceDocumentResponse
        '''

        # Delegate to TransferObject.from_model with the retrieved body.
        return SourceDocumentResponse.from_model(
            source,
            content=content,
        )

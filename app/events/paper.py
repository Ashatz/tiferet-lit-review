"""Lit Review Paper Events"""

# *** imports

# ** core
from typing import List, Optional

# ** app
from tiferet import DomainEvent

from ..domain.paper import Paper
from ..domain.theme import Theme
from ..interfaces.abstract import AbstractService
from ..interfaces.citation import CitationService
from ..interfaces.outline import OutlineService
from ..interfaces.paper import PaperService
from ..interfaces.theme import ThemeService
from ..mappers.paper import PaperAggregate, PaperResponse
from .abstract import ABSTRACT_NOT_FOUND_ID
from .citation import CITATION_NOT_FOUND_ID
from .outline import OUTLINE_NOT_FOUND_ID

# *** constants

# ** constant: paper_not_found_id
PAPER_NOT_FOUND_ID = 'PAPER_NOT_FOUND'

# ** constant: paper_section_not_found_id
PAPER_SECTION_NOT_FOUND_ID = 'PAPER_SECTION_NOT_FOUND'

# *** events

# ** event: paper_event
class PaperEvent(DomainEvent):
    '''
    Base event providing the shared PaperService dependency.
    '''

    # * attribute: paper_service
    paper_service: PaperService

    # * init
    def __init__(self, paper_service: PaperService) -> None:
        '''
        Initialize the PaperEvent.

        :param paper_service: The paper service dependency.
        :type paper_service: PaperService
        '''

        # Set the paper service dependency.
        self.paper_service = paper_service

# ** event: open_paper_from_outline
class OpenPaperFromOutline(DomainEvent):
    '''
    Fork an Outline into a Paper.

    Each outline slot becomes a Paper Section with the slot's themes
    already joined and empty content/context. The outline is origin
    history only and is not written back to.
    '''

    # * attribute: paper_service
    paper_service: PaperService

    # * attribute: outline_service
    outline_service: OutlineService

    # * init
    def __init__(self,
            paper_service: PaperService,
            outline_service: OutlineService,
        ) -> None:
        '''
        Initialize the OpenPaperFromOutline event.

        :param paper_service: The paper service dependency.
        :type paper_service: PaperService
        :param outline_service: The outline service dependency.
        :type outline_service: OutlineService
        '''

        # Set all injected dependencies.
        self.paper_service = paper_service
        self.outline_service = outline_service

    # * method: execute
    @DomainEvent.parameters_required(['outline_id'])
    def execute(self,
            outline_id: str,
            title: Optional[str] = None,
            **kwargs,
        ) -> Paper:
        '''
        Open a paper from an existing outline.

        :param outline_id: The origin outline identifier.
        :type outline_id: str
        :param title: Optional manuscript title; defaults to the outline title.
        :type title: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The created paper.
        :rtype: Paper
        '''

        # Verify the origin outline exists before writing a paper.
        outline = self.outline_service.get(outline_id)
        self.verify(
            outline is not None,
            OUTLINE_NOT_FOUND_ID,
            message=f'Outline not found: {outline_id}.',
            id=outline_id,
        )

        # Create the manuscript as a fork of the named slots.
        paper = PaperAggregate(
            title=title or outline.title,
            outline_id=outline.id,
        )
        for slot in outline.slots:
            paper.add_section(
                slot.title,
                theme_ids=[theme.theme_id for theme in slot.themes],
            )
        self.paper_service.save(paper)

        # Return the newly opened paper.
        return paper

# ** event: get_paper
class GetPaper(PaperEvent):
    '''
    Retrieve a Paper by its ID.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> Paper:
        '''
        Retrieve a paper by ID.

        :param id: The paper identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The paper.
        :rtype: Paper
        '''

        # Retrieve the paper from the service.
        paper = self.paper_service.get(id)

        # Verify the paper exists.
        self.verify(
            paper is not None,
            PAPER_NOT_FOUND_ID,
            message=f'Paper not found: {id}.',
            id=id,
        )

        # Return the paper.
        return paper

# ** event: list_papers
class ListPapers(PaperEvent):
    '''
    List all papers.
    '''

    # * method: execute
    def execute(self,
            title: Optional[str] = None,
            outline_id: Optional[str] = None,
            **kwargs,
        ) -> List[Paper]:
        '''
        List papers, optionally filtered by title or origin outline.

        :param title: Optional paper title to match exactly.
        :type title: Optional[str]
        :param outline_id: Optional origin outline identifier.
        :type outline_id: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The matching papers.
        :rtype: List[Paper]
        '''

        # Return papers from the service, applying the optional filters.
        return self.paper_service.list(title=title, outline_id=outline_id)

# ** event: show_paper
class ShowPaper(PaperEvent):
    '''
    Display a paper's sections, themes, and used citations.
    '''

    # * attribute: theme_service
    theme_service: ThemeService

    # * attribute: citation_service
    citation_service: CitationService

    # * init
    def __init__(self,
            paper_service: PaperService,
            theme_service: ThemeService,
            citation_service: CitationService,
        ) -> None:
        '''
        Initialize the ShowPaper event.

        :param paper_service: The paper service dependency.
        :type paper_service: PaperService
        :param theme_service: The theme service dependency.
        :type theme_service: ThemeService
        :param citation_service: The citation service dependency.
        :type citation_service: CitationService
        '''

        # Initialize the shared paper service dependency.
        super().__init__(paper_service)

        # Set the remaining show dependencies.
        self.theme_service = theme_service
        self.citation_service = citation_service

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> Paper:
        '''
        Show a paper and its joined themes.

        :param id: The paper identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The paper response, including joined themes.
        :rtype: Paper
        '''

        # Retrieve the paper and verify it exists.
        paper = self.paper_service.get(id)
        self.verify(
            paper is not None,
            PAPER_NOT_FOUND_ID,
            message=f'Paper not found: {id}.',
            id=id,
        )

        # Resolve each owned join from the loaded aggregate.
        themes = self._load_section_themes(paper)
        citations = []
        for item in paper.citations:
            citation = self.citation_service.get(item.citation_id)
            if citation is not None:
                citations.append(citation)

        # Map the paper aggregate into a response that includes the joins.
        return PaperResponse.from_aggregate(
            paper,
            themes=themes,
            citations=citations,
        )

    # * method: _load_section_themes
    def _load_section_themes(self, paper: PaperAggregate) -> List[Theme]:
        '''
        Resolve every Theme currently joined to the paper's sections.

        :param paper: The paper whose owned sections to resolve.
        :type paper: PaperAggregate
        :return: The section themes in section-then-join order.
        :rtype: List[Theme]
        '''

        # Resolve each owned join, skipping any theme that can no longer be loaded.
        themes = []
        for section in paper.sections:
            for join in section.themes:
                theme = self.theme_service.get(join.theme_id)
                if theme is not None:
                    themes.append(theme)

        # Return the full set in section-then-join order.
        return themes

# ** event: update_paper_section
class UpdatePaperSection(PaperEvent):
    '''
    Apply an editorial write to an owned paper section.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id', 'section_id'])
    def execute(self,
            id: str,
            section_id: str,
            content: Optional[str] = None,
            context: Optional[str] = None,
            title: Optional[str] = None,
            **kwargs,
        ) -> Paper:
        '''
        Update an owned paper section.

        :param id: The paper identifier.
        :type id: str
        :param section_id: The section identifier to update.
        :type section_id: str
        :param content: The updated drafted prose, if provided.
        :type content: Optional[str]
        :param context: The updated context note, if provided.
        :type context: Optional[str]
        :param title: The updated heading, if provided.
        :type title: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The paper after the section write.
        :rtype: Paper
        '''

        # Retrieve the paper and verify it exists.
        paper = self.paper_service.get(id)
        self.verify(
            paper is not None,
            PAPER_NOT_FOUND_ID,
            message=f'Paper not found: {id}.',
            id=id,
        )

        # Verify the named section belongs to this paper.
        self.verify(
            paper.has_section(section_id),
            PAPER_SECTION_NOT_FOUND_ID,
            message=f'Paper section not found: {section_id}.',
            id=section_id,
        )

        # Apply the editorial write and persist the manuscript.
        paper.update_section(
            section_id,
            content=content,
            context=context,
            title=title,
        )
        self.paper_service.save(paper)

        # Return the updated paper.
        return paper

# ** event: set_paper_abstract
class SetPaperAbstract(DomainEvent):
    '''
    Set the owned paper brief, optionally copied from a KB Abstract.
    '''

    # * attribute: paper_service
    paper_service: PaperService

    # * attribute: abstract_service
    abstract_service: AbstractService

    # * init
    def __init__(self,
            paper_service: PaperService,
            abstract_service: AbstractService,
        ) -> None:
        '''
        Initialize the SetPaperAbstract event.

        :param paper_service: The paper service dependency.
        :type paper_service: PaperService
        :param abstract_service: The KB abstract service dependency.
        :type abstract_service: AbstractService
        '''

        # Set all injected dependencies.
        self.paper_service = paper_service
        self.abstract_service = abstract_service

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self,
            id: str,
            body: Optional[str] = None,
            abstract_id: Optional[str] = None,
            **kwargs,
        ) -> Paper:
        '''
        Set the owned paper brief.

        :param id: The paper identifier.
        :type id: str
        :param body: Optional editorial body.
        :type body: Optional[str]
        :param abstract_id: Optional KB Abstract to copy from.
        :type abstract_id: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The paper after the abstract write.
        :rtype: Paper
        '''

        # Retrieve the paper and verify it exists.
        paper = self.paper_service.get(id)
        self.verify(
            paper is not None,
            PAPER_NOT_FOUND_ID,
            message=f'Paper not found: {id}.',
            id=id,
        )

        # Copy from a KB Abstract when requested; do not delete that abstract.
        source_abstract_id = None
        copied_body = body or ''
        if abstract_id is not None:
            abstract = self.abstract_service.get(abstract_id)
            self.verify(
                abstract is not None,
                ABSTRACT_NOT_FOUND_ID,
                message=f'Abstract not found: {abstract_id}.',
                id=abstract_id,
            )
            copied_body = body if body is not None else abstract.body
            source_abstract_id = abstract.id

        # Own the brief on the paper and persist.
        paper.set_abstract(copied_body, source_abstract_id=source_abstract_id)
        self.paper_service.save(paper)

        # Return the updated paper.
        return paper

# ** event: add_paper_citation
class AddPaperCitation(DomainEvent):
    '''
    Record that a KB citation is used in this manuscript.
    '''

    # * attribute: paper_service
    paper_service: PaperService

    # * attribute: citation_service
    citation_service: CitationService

    # * init
    def __init__(self,
            paper_service: PaperService,
            citation_service: CitationService,
        ) -> None:
        '''
        Initialize the AddPaperCitation event.

        :param paper_service: The paper service dependency.
        :type paper_service: PaperService
        :param citation_service: The citation service dependency.
        :type citation_service: CitationService
        '''

        # Set all injected dependencies.
        self.paper_service = paper_service
        self.citation_service = citation_service

    # * method: execute
    @DomainEvent.parameters_required(['id', 'citation_id'])
    def execute(self,
            id: str,
            citation_id: str,
            section_id: Optional[str] = None,
            **kwargs,
        ) -> Paper:
        '''
        Add a KB citation to this paper.

        :param id: The paper identifier.
        :type id: str
        :param citation_id: The KB citation identifier to include.
        :type citation_id: str
        :param section_id: Optional section this citation is used in.
        :type section_id: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The paper after adding (unchanged on an idempotent re-add).
        :rtype: Paper
        '''

        # Retrieve the paper and verify it exists.
        paper = self.paper_service.get(id)
        self.verify(
            paper is not None,
            PAPER_NOT_FOUND_ID,
            message=f'Paper not found: {id}.',
            id=id,
        )

        # Verify an optional section belongs to this paper.
        if section_id is not None:
            self.verify(
                paper.has_section(section_id),
                PAPER_SECTION_NOT_FOUND_ID,
                message=f'Paper section not found: {section_id}.',
                id=section_id,
            )

        # Verify the KB citation exists before forming the join.
        citation = self.citation_service.get(citation_id)
        self.verify(
            citation is not None,
            CITATION_NOT_FOUND_ID,
            message=f'Citation not found: {citation_id}.',
            id=citation_id,
        )

        # Idempotent: an already-used citation returns the paper unchanged.
        added = paper.add_citation(citation_id, section_id=section_id)
        if not added:
            return paper

        # Persist the updated paper aggregate.
        self.paper_service.save(paper)

        # Return the updated paper.
        return paper

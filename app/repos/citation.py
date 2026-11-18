"""Lit Review Citation H5 Repository"""

# *** imports

# ** core
from typing import Any, Dict, List, Optional

# ** infra
import numpy as np
import tables
from tiferet_h5 import H5Repository

# ** app
from ..interfaces.citation import CitationService
from ..mappers.citation import (
    CitationAggregate,
    CitationNodeObject,
    CitationTableObject,
)

# *** constants

# ** constant: citations_root_path
CITATIONS_ROOT_PATH = '/lit_review'

# ** constant: citations_node_leaf
CITATIONS_NODE_LEAF = 'citations'

# ** constant: citations_node_path
CITATIONS_NODE_PATH = f'{CITATIONS_ROOT_PATH}/{CITATIONS_NODE_LEAF}'

# ** constant: citations_table_leaf
# Same path as the group. The name remains for callers that still say "table".
CITATIONS_TABLE_LEAF = CITATIONS_NODE_LEAF

# ** constant: citations_table_path
CITATIONS_TABLE_PATH = CITATIONS_NODE_PATH

# ** constant: citations_staging_leaf
CITATIONS_STAGING_LEAF = 'citations_node_staging'

# ** constant: citations_staging_path
CITATIONS_STAGING_PATH = f'{CITATIONS_ROOT_PATH}/{CITATIONS_STAGING_LEAF}'

# ** constant: citations_table_backup_leaf
CITATIONS_TABLE_BACKUP_LEAF = 'citations_table_retired'

# ** constant: citations_table_backup_path
CITATIONS_TABLE_BACKUP_PATH = f'{CITATIONS_ROOT_PATH}/{CITATIONS_TABLE_BACKUP_LEAF}'

# ** constant: excerpt_array_name
EXCERPT_ARRAY_NAME = 'excerpt'

# ** constant: context_note_array_name
CONTEXT_NOTE_ARRAY_NAME = 'context_note'

# ** constant: citation_order_attr
CITATION_ORDER_ATTR = 'citation_order'

# ** constant: citation_text_filters
CITATION_TEXT_FILTERS = tables.Filters(complib='zlib', complevel=5)

# ** constant: citations_table_filters
# Kept for callers that named the old table filter. Text arrays use the same filter.
CITATIONS_TABLE_FILTERS = CITATION_TEXT_FILTERS

# *** functions

# ** function: stripped_text
def stripped_text(value: Any) -> str:
    '''
    Decode a stored cell and drop StringCol NUL padding.

    :param value: A table cell or attribute value.
    :type value: Any
    :return: UTF-8 text without trailing NUL bytes.
    :rtype: str
    '''

    # Absent cells contribute no characters.
    if value is None:
        return ''

    # Decode fixed-width bytes, then drop padding that is not content.
    if isinstance(value, bytes):
        value = value.decode('utf-8')
    if isinstance(value, str):
        return value.rstrip('\x00')
    return str(value)


# ** function: text_to_array
def text_to_array(text: str) -> np.ndarray:
    '''
    Encode citation text as a uint8 array sized to those bytes.

    :param text: The text to store.
    :type text: str
    :return: A uint8 array of the UTF-8 bytes.
    :rtype: np.ndarray
    '''

    # The array length is the stored byte length, not the validation ceiling.
    return np.frombuffer(text.encode('utf-8'), dtype=np.uint8)


# ** function: array_to_text
def array_to_text(data: Any) -> str:
    '''
    Decode a uint8 citation array back to text.

    :param data: Array contents from ``array.read()``.
    :type data: Any
    :return: The stored text.
    :rtype: str
    '''

    # Empty and non-empty arrays both decode without padding.
    return np.asarray(data, dtype=np.uint8).tobytes().decode('utf-8')


# ** function: normalize_order
def normalize_order(raw: Any) -> List[str]:
    '''
    Normalize a stored citation-order attribute to a list of ids.

    :param raw: The attribute value, or None when it is absent.
    :type raw: Any
    :return: Citation ids in stored order.
    :rtype: List[str]
    '''

    # A missing attribute is an empty order, not an error.
    if raw is None:
        return []
    if isinstance(raw, (str, bytes)):
        raw = [raw]

    # Decode each id. HDF5 may return bytes or a numpy scalar.
    order = []
    for item in list(raw):
        if isinstance(item, bytes):
            item = item.decode('utf-8')
        elif hasattr(item, 'item') and not isinstance(item, str):
            item = item.item()
            if isinstance(item, bytes):
                item = item.decode('utf-8')
        order.append(str(item))
    return order


# ** function: aggregate_from_table_row
def aggregate_from_table_row(row: Dict[str, Any]) -> CitationAggregate:
    '''
    Build a citation aggregate from one pre-migration table row.

    Blank title is omitted so it stays absent. A present empty context note
    stays an empty string. A missing type becomes the domain default.

    :param row: One row dict from ``H5Client.read_rows``.
    :type row: Dict[str, Any]
    :return: The citation those cells describe.
    :rtype: CitationAggregate
    '''

    # Small fields are stripped of StringCol padding before validation.
    data = {
        'id': stripped_text(row.get('id')),
        'source_id': stripped_text(row.get('source_id')),
        'locator': stripped_text(row.get('locator')),
        'excerpt': stripped_text(row.get('excerpt')),
        'created_at': int(row.get('created_at') or 0),
    }
    if 'context_note' in row:
        data['context_note'] = stripped_text(row.get('context_note'))
    title = stripped_text(row.get('title')) if 'title' in row else ''
    if title:
        data['title'] = title
    citation_type = stripped_text(row.get('type')) if 'type' in row else ''
    if citation_type:
        data['type'] = citation_type

    # Domain validation supplies default type and rejects an unknown one.
    return CitationAggregate.model_validate(data)


# *** repos

# ** repo: citation_h5_repository
class CitationH5Repository(CitationService, H5Repository):
    '''
    HDF5 repository for Citation domain objects.

    A fresh store keeps one group per citation at
    ``/lit_review/citations/<citation_id>``. Small fields are attributes.
    Excerpt and context note are compressed arrays sized to the stored text.
    An unmigrated ``/lit_review/citations`` table is still readable and
    writable in place. ``save`` does not convert that table. Call
    ``migrate_table_to_groups`` on purpose.
    '''

    # * init
    def __init__(self, h5_file: str, mode: str = 'a') -> None:
        '''
        Initialize the citation H5 repository.

        :param h5_file: Path to the shared lit_review HDF5 file.
        :type h5_file: str
        :param mode: Default PyTables open mode.
        :type mode: str
        '''

        # Initialize the H5 repository base.
        H5Repository.__init__(self, h5_file=h5_file, mode=mode)

    # * method: exists
    def exists(self, id: str) -> bool:
        '''
        Check whether a citation with the given ID exists.

        :param id: The citation identifier.
        :type id: str
        :return: True if the citation exists, otherwise False.
        :rtype: bool
        '''

        # A group presence check does not read text arrays.
        with self.client() as h5:
            kind = self._citations_kind(h5)
            if kind == 'group':
                return h5.node_exists(self._citation_path(id))
            if kind == 'table':
                return self._get_from_table(h5, id) is not None
            return False

    # * method: get
    def get(self, id: str) -> Optional[CitationAggregate]:
        '''
        Retrieve a Citation by its ID.

        A group store is a path lookup plus that citation's arrays. Other
        citations stay closed. An unmigrated table is still read in full;
        that path goes away when ``migrate_table_to_groups`` has run.

        :param id: The citation identifier.
        :type id: str
        :return: The citation aggregate, or None if not found.
        :rtype: Optional[CitationAggregate]
        '''

        # Dispatch on the citations node. Do not migrate here.
        with self.client() as h5:
            kind = self._citations_kind(h5)
            if kind == 'absent':
                return None
            if kind == 'table':
                return self._get_from_table(h5, id)
            return self._read_group(h5, self._citation_path(id))

    # * method: list
    def list(self, **filters) -> List[CitationAggregate]:
        '''
        List citations, optionally filtered by source_id and IDs.

        :param filters: Optional source_id and ids criteria, combined by
            intersection. ids=None selects all IDs; an empty collection
            selects none.
        :type filters: dict
        :return: The matching citation aggregates, in insertion order.
        :rtype: List[CitationAggregate]
        '''

        # An empty selection has no reason to open the file.
        ids = filters.get('ids')
        selected_ids = set(ids) if ids is not None else None
        if selected_ids is not None and not selected_ids:
            return []

        # Group list reads an array only for a citation that remains selected.
        source_id = filters.get('source_id')
        with self.client() as h5:
            kind = self._citations_kind(h5)
            if kind == 'absent':
                return []
            if kind == 'table':
                return self._list_from_table(h5, selected_ids, source_id)
            return self._list_groups(h5, selected_ids, source_id)

    # * method: remove_for_transfer
    def remove_for_transfer(self, id: str) -> None:
        '''
        Remove an origin citation as the last step of a move.

        This helper is repository-private. It is not part of CitationService
        and is not a general-purpose delete API.

        :param id: The origin citation identifier to remove.
        :type id: str
        '''

        # Drop one citation. Sibling groups, including the parent sources, stay.
        with self.client() as h5:
            kind = self._citations_kind(h5)
            if kind == 'table':
                self._remove_table_row(h5, id)
                return
            if kind != 'group':
                return
            path = self._citation_path(id)
            if h5.node_exists(path):
                h5.h5file.remove_node(path, recursive=True)
            order = [
                citation_id for citation_id in self._read_order(h5, CITATIONS_NODE_PATH)
                if citation_id != id
            ]
            self._write_order(h5, CITATIONS_NODE_PATH, order)

    # * method: save
    def save(self, citation: CitationAggregate) -> None:
        '''
        Persist a Citation aggregate.

        A fresh store, or a store already converted to groups, writes one
        group and sized text arrays. An existing citations table is updated
        in place and is not converted. Call ``migrate_table_to_groups`` for
        that conversion.

        :param citation: The citation aggregate to persist.
        :type citation: CitationAggregate
        '''

        # Never migrate from save. Capture must not rewrite the table.
        with self.client() as h5:
            if self._citations_kind(h5) == 'table':
                self._save_table(h5, citation)
                return
            self._save_group(h5, citation)

    # * method: migrate_table_to_groups
    def migrate_table_to_groups(self) -> int:
        '''
        Copy a citations table into sized groups, then remove only that table.

        Copies every row into a staging group and verifies count, ids,
        locators, types, and text before the table is renamed aside. A failed
        check removes the staging group and leaves the table. Themes, sources,
        linkages, and activities are not opened.

        Already-grouped stores are left unchanged. This method is not called
        from ``save``, ``get``, or ``list``.

        :return: The number of citation rows copied. Zero when there was no table.
        :rtype: int
        :raises RuntimeError: If the staged groups do not match the table.
        '''

        # Refuse to run when there is nothing to convert.
        with self.client() as h5:
            if self._citations_kind(h5) != 'table':
                return 0
            rows = h5.read_rows(CITATIONS_NODE_PATH)
            expected = [aggregate_from_table_row(row) for row in rows]

            # A leftover staging group is not citation content. Replace it.
            if h5.node_exists(CITATIONS_STAGING_PATH):
                h5.h5file.remove_node(CITATIONS_STAGING_PATH, recursive=True)

            # Verify before the table path is touched.
            try:
                self._write_groups(h5, CITATIONS_STAGING_PATH, expected)
                self._assert_groups_match(h5, CITATIONS_STAGING_PATH, expected)
            except Exception:
                if h5.node_exists(CITATIONS_STAGING_PATH):
                    h5.h5file.remove_node(CITATIONS_STAGING_PATH, recursive=True)
                raise

            # Move the table aside, promote the verified group, then drop the table.
            h5.h5file.rename_node(CITATIONS_NODE_PATH, CITATIONS_TABLE_BACKUP_LEAF)
            h5.h5file.rename_node(CITATIONS_STAGING_PATH, CITATIONS_NODE_LEAF)
            try:
                self._assert_groups_match(h5, CITATIONS_NODE_PATH, expected)
            except Exception:
                if h5.node_exists(CITATIONS_NODE_PATH):
                    h5.h5file.remove_node(CITATIONS_NODE_PATH, recursive=True)
                if h5.node_exists(CITATIONS_TABLE_BACKUP_PATH):
                    h5.h5file.rename_node(
                        CITATIONS_TABLE_BACKUP_PATH,
                        CITATIONS_NODE_LEAF,
                    )
                raise
            h5.h5file.remove_node(CITATIONS_TABLE_BACKUP_PATH)
            return len(expected)

    # * method: _citations_kind
    def _citations_kind(self, h5: Any) -> str:
        '''
        Classify the citations node as absent, table, or group.

        :param h5: The open H5 client.
        :type h5: Any
        :return: ``absent``, ``table``, or ``group``.
        :rtype: str
        '''

        # A missing node is not a reason to create either shape.
        if not h5.node_exists(CITATIONS_NODE_PATH):
            return 'absent'
        node = h5.h5file.get_node(CITATIONS_NODE_PATH)
        if isinstance(node, tables.Table):
            return 'table'
        return 'group'

    # * method: _citation_path
    def _citation_path(self, citation_id: str) -> str:
        '''
        Build the group path for one citation.

        :param citation_id: The citation identifier.
        :type citation_id: str
        :return: The absolute HDF5 group path.
        :rtype: str
        '''

        # Text arrays live under this group.
        return f'{CITATIONS_NODE_PATH}/{citation_id}'

    # * method: _array_path
    def _array_path(self, group_path: str, name: str) -> str:
        '''
        Build an array path under a citation group.

        :param group_path: The citation group path.
        :type group_path: str
        :param name: The array node name.
        :type name: str
        :return: The absolute HDF5 array path.
        :rtype: str
        '''

        # Excerpt and context note are siblings under the citation group.
        return f'{group_path}/{name}'

    # * method: _read_order
    def _read_order(self, h5: Any, group_path: str) -> List[str]:
        '''
        Read stored insertion order, then any group children missing from it.

        :param h5: The open H5 client.
        :type h5: Any
        :param group_path: The citations group whose order to read.
        :type group_path: str
        :return: Citation ids in insertion order.
        :rtype: List[str]
        '''

        # The attribute is the insertion order written by save and migration.
        if not h5.node_exists(group_path):
            return []
        order = normalize_order(h5.get_node_attrs(group_path).get(CITATION_ORDER_ATTR))
        known = set(order)
        group = h5.get_group(group_path)
        for name, child in group._v_children.items():
            if isinstance(child, tables.Group) and name not in known:
                order.append(name)
        return order

    # * method: _write_order
    def _write_order(self, h5: Any, group_path: str, citation_ids: List[str]) -> None:
        '''
        Store citation ids in insertion order on the parent group.

        :param h5: The open H5 client.
        :type h5: Any
        :param group_path: The citations group to annotate.
        :type group_path: str
        :param citation_ids: Ids in insertion order.
        :type citation_ids: List[str]
        '''

        # A parent attribute is not a citation and is not a text array.
        h5.set_node_attr(group_path, CITATION_ORDER_ATTR, list(citation_ids))

    # * method: _write_text_array
    def _write_text_array(self, h5: Any, path: str, text: str) -> None:
        '''
        Replace a text array with one sized to the stored bytes.

        :param h5: The open H5 client.
        :type h5: Any
        :param path: The absolute array path.
        :type path: str
        :param text: The text to store.
        :type text: str
        '''

        # create_array cannot overwrite, and a CArray cannot have a zero shape.
        if h5.node_exists(path):
            h5.h5file.remove_node(path)
        data = text_to_array(text)
        if data.size == 0:
            h5.create_array(path, np.array([], dtype=np.uint8))
            return
        h5.create_array(path, data, filters=CITATION_TEXT_FILTERS)

    # * method: _remove_text_array
    def _remove_text_array(self, h5: Any, path: str) -> None:
        '''
        Remove a text array when the field is absent.

        :param h5: The open H5 client.
        :type h5: Any
        :param path: The absolute array path.
        :type path: str
        '''

        # An absent note is no array, not an empty column.
        if h5.node_exists(path):
            h5.h5file.remove_node(path)

    # * method: _read_text_array
    def _read_text_array(self, h5: Any, path: str) -> Optional[str]:
        '''
        Read one text array, or None when the array is absent.

        :param h5: The open H5 client.
        :type h5: Any
        :param path: The absolute array path.
        :type path: str
        :return: The stored text, or None when there is no array.
        :rtype: Optional[str]
        '''

        # node_exists avoids opening a sibling citation's array.
        if not h5.node_exists(path):
            return None
        return array_to_text(h5.get_array(path).read())

    # * method: _write_attrs
    def _write_attrs(self, h5: Any, path: str, citation: CitationAggregate) -> None:
        '''
        Write citation attributes, omitting an absent title.

        :param h5: The open H5 client.
        :type h5: Any
        :param path: The citation group path.
        :type path: str
        :param citation: The citation to store.
        :type citation: CitationAggregate
        '''

        # to_attrs drops excerpt, context note, and a None title.
        attrs = CitationNodeObject.from_model(citation).to_attrs()
        for name, value in attrs.items():
            h5.set_node_attr(path, name, value)

        # A cleared title must not remain from an earlier save.
        node = h5.h5file.get_node(path)
        if citation.title is None and 'title' in node._v_attrs:
            del node._v_attrs.title

    # * method: _write_one_group
    def _write_one_group(self,
            h5: Any,
            parent_path: str,
            citation: CitationAggregate,
        ) -> None:
        '''
        Write one citation group and its text arrays under a parent group.

        :param h5: The open H5 client.
        :type h5: Any
        :param parent_path: The citations group that owns this citation.
        :type parent_path: str
        :param citation: The citation to store.
        :type citation: CitationAggregate
        '''

        # Attributes first, then arrays sized to the text that is present.
        path = f'{parent_path}/{citation.id}'
        if not h5.node_exists(path):
            h5.create_group(path)
        self._write_attrs(h5, path, citation)
        self._write_text_array(
            h5,
            self._array_path(path, EXCERPT_ARRAY_NAME),
            citation.excerpt,
        )
        note_path = self._array_path(path, CONTEXT_NOTE_ARRAY_NAME)
        if citation.context_note is None:
            self._remove_text_array(h5, note_path)
            return
        self._write_text_array(h5, note_path, citation.context_note)

    # * method: _write_groups
    def _write_groups(self,
            h5: Any,
            parent_path: str,
            citations: List[CitationAggregate],
        ) -> None:
        '''
        Write a citations group and every citation under it.

        :param h5: The open H5 client.
        :type h5: Any
        :param parent_path: The group path to create.
        :type parent_path: str
        :param citations: Citations in insertion order.
        :type citations: List[CitationAggregate]
        '''

        # Order is an attribute on the parent, not a citation child.
        h5.create_group(parent_path)
        for citation in citations:
            self._write_one_group(h5, parent_path, citation)
        self._write_order(h5, parent_path, [citation.id for citation in citations])

    # * method: _read_group
    def _read_group(self, h5: Any, path: str) -> Optional[CitationAggregate]:
        '''
        Read one citation group. Does not open sibling groups.

        :param h5: The open H5 client.
        :type h5: Any
        :param path: The citation group path.
        :type path: str
        :return: The citation aggregate, or None when the group is absent.
        :rtype: Optional[CitationAggregate]
        '''

        # A missing group is a missing citation, not an error.
        if not h5.node_exists(path):
            return None
        attrs = {
            name: value
            for name, value in h5.get_node_attrs(path).items()
            if name != CITATION_ORDER_ATTR
        }
        excerpt = self._read_text_array(h5, self._array_path(path, EXCERPT_ARRAY_NAME))
        note = self._read_text_array(h5, self._array_path(path, CONTEXT_NOTE_ARRAY_NAME))
        data = dict(attrs)
        data['excerpt'] = '' if excerpt is None else excerpt
        if note is not None:
            data['context_note'] = note
        return CitationAggregate.model_validate(data)

    # * method: _list_groups
    def _list_groups(self,
            h5: Any,
            selected_ids: Optional[set],
            source_id: Optional[str],
        ) -> List[CitationAggregate]:
        '''
        Walk citation groups and read arrays only for selected citations.

        :param h5: The open H5 client.
        :type h5: Any
        :param selected_ids: Ids to keep, or None for every citation.
        :type selected_ids: Optional[set]
        :param source_id: Optional source filter applied before array reads.
        :type source_id: Optional[str]
        :return: Matching citations in insertion order.
        :rtype: List[CitationAggregate]
        '''

        # Unselected ids are skipped before any text array is opened.
        citations = []
        for citation_id in self._read_order(h5, CITATIONS_NODE_PATH):
            if selected_ids is not None and citation_id not in selected_ids:
                continue
            path = self._citation_path(citation_id)
            if not h5.node_exists(path):
                continue
            if source_id is not None:
                attrs = h5.get_node_attrs(path)
                if attrs.get('source_id') != source_id:
                    continue
            citation = self._read_group(h5, path)
            if citation is not None:
                citations.append(citation)
        return citations

    # * method: _save_group
    def _save_group(self, h5: Any, citation: CitationAggregate) -> None:
        '''
        Insert or replace one citation group. Does not read other citations' text.

        :param h5: The open H5 client.
        :type h5: Any
        :param citation: The citation to persist.
        :type citation: CitationAggregate
        '''

        # The parent group is created once. An update does not change order.
        if not h5.node_exists(CITATIONS_NODE_PATH):
            h5.create_group(CITATIONS_NODE_PATH)
            self._write_order(h5, CITATIONS_NODE_PATH, [])
        is_new = not h5.node_exists(self._citation_path(citation.id))
        self._write_one_group(h5, CITATIONS_NODE_PATH, citation)
        if not is_new:
            return

        # Persist insertion order. Do not treat a child walk as already stored.
        order = normalize_order(
            h5.get_node_attrs(CITATIONS_NODE_PATH).get(CITATION_ORDER_ATTR)
        )
        if citation.id not in order:
            order.append(citation.id)
            self._write_order(h5, CITATIONS_NODE_PATH, order)

    # * method: _assert_groups_match
    def _assert_groups_match(self,
            h5: Any,
            parent_path: str,
            expected: List[CitationAggregate],
        ) -> None:
        '''
        Verify staged or promoted groups match the citations copied from a table.

        :param h5: The open H5 client.
        :type h5: Any
        :param parent_path: The citations group to read.
        :type parent_path: str
        :param expected: Citations in table insertion order.
        :type expected: List[CitationAggregate]
        :raises RuntimeError: If count, order, or a stored field does not match.
        '''

        # Count and order are checked before field text, so a short copy fails closed.
        order = self._read_order(h5, parent_path)
        if len(order) != len(expected):
            raise RuntimeError(
                'Citation group migration failed parity check: '
                f'expected {len(expected)} citation(s), found {len(order)}.'
            )
        for index, citation in enumerate(expected):
            if order[index] != citation.id:
                raise RuntimeError(
                    'Citation group migration failed parity check: '
                    f'insertion order mismatch at index {index}: '
                    f'expected id {citation.id!r}, found {order[index]!r}.'
                )
            actual = self._read_group(h5, f'{parent_path}/{citation.id}')
            if actual is None:
                raise RuntimeError(
                    'Citation group migration failed parity check: '
                    f'missing group for id {citation.id!r}.'
                )
            self._assert_same_citation(actual, citation, index)

    # * method: _assert_same_citation
    def _assert_same_citation(self,
            actual: CitationAggregate,
            expected: CitationAggregate,
            index: int,
        ) -> None:
        '''
        Compare the fields migration is required to preserve.

        :param actual: The citation read back from a group.
        :type actual: CitationAggregate
        :param expected: The citation copied from the table row.
        :type expected: CitationAggregate
        :param index: The table row index, for the error message.
        :type index: int
        :raises RuntimeError: If a preserved field differs.
        '''

        # Text, locator, type, and title are the migration contract.
        checks = {
            'id': actual.id == expected.id,
            'source_id': actual.source_id == expected.source_id,
            'locator': actual.locator == expected.locator,
            'type': actual.type == expected.type,
            'excerpt': actual.excerpt == expected.excerpt,
            'context_note': actual.context_note == expected.context_note,
            'title': actual.title == expected.title,
            'created_at': actual.created_at == expected.created_at,
        }
        for field_name, matched in checks.items():
            if matched:
                continue
            raise RuntimeError(
                'Citation group migration failed parity check: '
                f'field {field_name!r} mismatch at index {index} '
                f'(id {expected.id!r}).'
            )

    # * method: _get_from_table
    def _get_from_table(self, h5: Any, citation_id: str) -> Optional[CitationAggregate]:
        '''
        Read one citation from an unmigrated table.

        This scans the table. It exists so a store that has not been migrated
        still answers get. It is not used after the node is a group.

        :param h5: The open H5 client.
        :type h5: Any
        :param citation_id: The citation identifier.
        :type citation_id: str
        :return: The citation, or None if the id is absent.
        :rtype: Optional[CitationAggregate]
        '''

        # Find the row in memory. Do not convert the table.
        rows = h5.read_rows(CITATIONS_NODE_PATH)
        match = next((row for row in rows if row.get('id') == citation_id), None)
        if match is None:
            return None
        return CitationTableObject.from_row(match).map(CitationAggregate)

    # * method: _list_from_table
    def _list_from_table(self,
            h5: Any,
            selected_ids: Optional[set],
            source_id: Optional[str],
        ) -> List[CitationAggregate]:
        '''
        List citations from an unmigrated table.

        :param h5: The open H5 client.
        :type h5: Any
        :param selected_ids: Ids to keep, or None for every row.
        :type selected_ids: Optional[set]
        :param source_id: Optional source filter.
        :type source_id: Optional[str]
        :return: Matching citations in table order.
        :rtype: List[CitationAggregate]
        '''

        # One table read, then filter before mapping unselected rows.
        rows = h5.read_rows(CITATIONS_NODE_PATH)
        if selected_ids is not None:
            rows = [row for row in rows if row.get('id') in selected_ids]
        if source_id is not None:
            rows = [row for row in rows if row.get('source_id') == source_id]
        return [
            CitationTableObject.from_row(row).map(CitationAggregate)
            for row in rows
        ]

    # * method: _save_table
    def _save_table(self, h5: Any, citation: CitationAggregate) -> None:
        '''
        Update or append one row on an unmigrated table.

        Does not widen columns and does not convert the table to groups.
        A table missing a current column must be migrated explicitly.

        :param h5: The open H5 client.
        :type h5: Any
        :param citation: The citation to persist.
        :type citation: CitationAggregate
        :raises RuntimeError: If the table is missing a column this write needs.
        '''

        # A stale narrow table is not rewritten into a 10,000,000-byte row.
        table = h5.get_table(CITATIONS_NODE_PATH)
        missing = [
            name for name in CitationTableObject._H5_TYPES
            if name not in table.colnames
        ]
        if missing:
            raise RuntimeError(
                'Citation table is missing columns '
                f'{missing}. Run migrate_table_to_groups(); '
                'save does not rewrite the table.'
            )

        # In-place upsert by id. This still scans an unmigrated table.
        data = CitationTableObject.from_model(citation).model_dump(by_alias=True)
        target_id = CitationTableObject.encode_value(
            citation.id,
            CitationTableObject._H5_TYPES['id'],
        )
        for index in range(table.nrows):
            if table.cols.id[index] != target_id:
                continue
            for name, col in CitationTableObject._H5_TYPES.items():
                getattr(table.cols, name)[index] = CitationTableObject.encode_value(
                    data.get(name),
                    col,
                )
            table.flush()
            return
        CitationTableObject.from_model(citation).to_row(table)
        table.flush()

    # * method: _remove_table_row
    def _remove_table_row(self, h5: Any, citation_id: str) -> None:
        '''
        Remove one row from an unmigrated citations table.

        :param h5: The open H5 client.
        :type h5: Any
        :param citation_id: The citation identifier to remove.
        :type citation_id: str
        '''

        # Drop only the matching row. The table node stays a table.
        table = h5.get_table(CITATIONS_NODE_PATH)
        target_id = CitationTableObject.encode_value(
            citation_id,
            CitationTableObject._H5_TYPES['id'],
        )
        for index in range(table.nrows):
            if table.cols.id[index] != target_id:
                continue
            table.remove_rows(index, index + 1)
            table.flush()
            return

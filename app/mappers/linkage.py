"""Lit Review Linkage Mappers"""

# *** imports

# ** core
from time import time
from typing import Any, ClassVar, Dict, Optional, Type

# ** infra
import tables
from pydantic import model_validator
from tiferet_h5 import TableObject

# ** app
from tiferet.mappers.core import Aggregate

from ..domain.linkage import Linkage

# *** mappers

# ** mapper: linkage_aggregate
class LinkageAggregate(Linkage, Aggregate):
    '''
    Mutable aggregate for the Linkage domain object.

    Retirement is state, not deletion: retire/reinstate stamp or clear
    retired_at/retirement_reason through validated mutation. Both are
    idempotent -- each returns False and makes no change when the linkage
    is already in the requested state -- so a researcher can retire or
    reinstate freely without checking current state first.

    set_relevancy_weight and clear_relevancy_weight are the same kind of
    idempotent judgment. Neither retires, reinstates, or rewrites a theme.
    '''

    # * method: retire
    def retire(self, reason: Optional[str] = None) -> bool:
        '''
        Retire this linkage, excluding it from synthesis and default views.

        :param reason: Optional free-text reason for the retirement.
        :type reason: Optional[str]
        :return: True if the linkage was retired, False if already retired.
        :rtype: bool
        '''

        # Idempotent no-op: do not restamp an already-retired linkage.
        if not self.is_active():
            return False

        # Stamp the retirement timestamp and optional reason.
        self.set_attribute('retired_at', int(time()))
        self.set_attribute('retirement_reason', reason)
        return True

    # * method: reinstate
    def reinstate(self) -> bool:
        '''
        Reinstate this linkage, returning it to the active set.

        :return: True if the linkage was reinstated, False if already active.
        :rtype: bool
        '''

        # Idempotent no-op: an already-active linkage is unchanged.
        if self.is_active():
            return False

        # Clear the retirement timestamp and reason.
        self.set_attribute('retired_at', None)
        self.set_attribute('retirement_reason', None)
        return True

    # * method: set_relevancy_weight
    def set_relevancy_weight(self, weight: int) -> bool:
        '''
        Record a researcher-confirmed relevancy weight on this mapping.

        :param weight: The judged thematic novelty, an integer from 1 to 100.
        :type weight: int
        :return: True if the weight changed, False if it was already set.
        :rtype: bool
        '''

        # Idempotent no-op: do not rewrite an unchanged judgment.
        if self.relevancy_weight == weight:
            return False

        # Stamp the weight. Validation rejects 0, out of range, and bools.
        self.set_attribute('relevancy_weight', weight)
        return True

    # * method: clear_relevancy_weight
    def clear_relevancy_weight(self) -> bool:
        '''
        Clear a recorded relevancy weight, returning the mapping to unjudged.

        :return: True if a weight was cleared, False if it was already absent.
        :rtype: bool
        '''

        # Idempotent no-op: an unjudged mapping is already clear.
        if self.relevancy_weight is None:
            return False

        # Absent is unjudged, not weight 0.
        self.set_attribute('relevancy_weight', None)
        return True


# ** mapper: linkage_table_object
class LinkageTableObject(Linkage, TableObject):
    '''
    HDF5 table mapper for Linkage: one PyTables row per linkage, stored in
    a single table at /lit_review/linkages.
    '''

    # * attribute: _H5_TYPES
    _H5_TYPES: ClassVar[Dict[str, Any]] = {
        'id': tables.StringCol(64),
        'citation_id': tables.StringCol(64),
        'theme_id': tables.StringCol(64),
        'created_at': tables.Int64Col(),
        'retired_at': tables.Int64Col(),
        'retirement_reason': tables.StringCol(1000),
        'relevancy_weight': tables.Int64Col(),
    }

    # * method: _restore_relevancy_weight_sentinel (model validator)
    @model_validator(mode='before')
    @classmethod
    def _restore_relevancy_weight_sentinel(cls, values: Any) -> Any:
        '''
        Restore a stored absent weight before the 1-100 rule runs.

        HDF5 stores an unjudged weight as 0. That sentinel must become
        None before Linkage validation, or a read of an unjudged row would
        be rejected as weight 0.

        :param values: The raw row or constructor values.
        :type values: Any
        :return: Values with a stored 0 restored to None.
        :rtype: Any
        '''

        # Only a mapping can carry the stored sentinel.
        if not isinstance(values, dict):
            return values

        # A stored 0 is unjudged, never a judged weight of 0.
        if values.get('relevancy_weight') == 0:
            values = dict(values)
            values['relevancy_weight'] = None

        # Return the restored values.
        return values

    # * method: map
    def map(self, target: Type[Aggregate], **overrides) -> Aggregate:
        '''
        Map this row to a LinkageAggregate, restoring absent sentinels.

        HDF5's Int64Col has no null representation, so encode_value stores
        an absent retired_at or relevancy_weight as 0. A stored 0 is
        normalized back to None here so a loaded linkage without a real
        retirement is active, and a stored 0 never surfaces as weight 0.

        :param target: The aggregate class to construct.
        :type target: Type[Aggregate]
        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The mapped aggregate.
        :rtype: Aggregate
        '''

        # Restore the retirement sentinel unless the caller already supplied one.
        if self.retired_at == 0:
            overrides.setdefault('retired_at', None)

        # Restore the unjudged-weight sentinel beside retired_at.
        if self.relevancy_weight == 0:
            overrides.setdefault('relevancy_weight', None)

        # Delegate to the base row-to-aggregate mapping.
        return super().map(target, **overrides)

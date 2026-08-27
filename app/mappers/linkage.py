"""Lit Review Linkage Mappers"""

# *** imports

# ** core
from time import time
from typing import Any, ClassVar, Dict, Optional, Type

# ** infra
import tables
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
    }

    # * method: map
    def map(self, target: Type[Aggregate], **overrides) -> Aggregate:
        '''
        Map this row to a LinkageAggregate, restoring the active sentinel.

        HDF5's Int64Col has no null representation, so encode_value stores
        an absent retired_at as 0. A stored 0 is normalized back to None
        here so a loaded linkage without a real retirement is active, not
        mistakenly retired at the epoch.

        :param target: The aggregate class to construct.
        :type target: Type[Aggregate]
        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The mapped aggregate.
        :rtype: Aggregate
        '''

        # Restore the None sentinel unless the caller already supplied one.
        if self.retired_at == 0:
            overrides.setdefault('retired_at', None)

        # Delegate to the base row-to-aggregate mapping.
        return super().map(target, **overrides)

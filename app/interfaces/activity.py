"""Lit Review Activity Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional

# ** app
from tiferet.interfaces.core import Service

from ..mappers.activity import ActivityAggregate

# *** interfaces

# ** interface: activity_service
class ActivityService(Service):
    '''
    Vertical interface for recording and querying ActivityEntry aggregates.

    Deliberately exposes no update or delete: activity history is
    append-only, so the only mutation is adding a new entry.
    '''

    # * method: record
    @abstractmethod
    def record(self, entry: ActivityAggregate) -> None:
        '''
        Append a new activity entry. Never updates or deletes an entry.

        :param entry: The activity entry to append.
        :type entry: ActivityAggregate
        '''
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self,
            action: Optional[str] = None,
            subject_type: Optional[str] = None,
            subject_id: Optional[str] = None,
            related_id: Optional[str] = None,
        ) -> List[ActivityAggregate]:
        '''
        List activity entries, newest first, with optional filters.

        :param action: Optional action token to match exactly.
        :type action: Optional[str]
        :param subject_type: Optional subject type to match exactly.
        :type subject_type: Optional[str]
        :param subject_id: Optional subject identifier to match exactly.
        :type subject_id: Optional[str]
        :param related_id: Optional related identifier to match exactly.
        :type related_id: Optional[str]
        :return: The matching activity entries, newest-insertion-first.
        :rtype: List[ActivityAggregate]
        '''
        raise NotImplementedError()

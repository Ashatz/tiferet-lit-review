"""Lit Review Activity Events"""

# *** imports

# ** core
import logging
from typing import List, Optional

# ** app
from tiferet import DomainEvent

from ..interfaces.activity import ActivityService
from ..mappers.activity import ActivityAggregate

# *** functions

# ** function: record_activity
def record_activity(activity_service: ActivityService, entry: ActivityAggregate) -> None:
    '''
    Append an activity entry as best-effort researcher history.

    A failed append must never undo, change, or fail the domain operation
    that already succeeded, so the failure is reported through operational
    logging instead of being raised.

    :param activity_service: The activity service dependency.
    :type activity_service: ActivityService
    :param entry: The activity entry to append.
    :type entry: ActivityAggregate
    '''

    # Attempt the append; swallow and log any failure rather than raise.
    try:
        activity_service.record(entry)
    except Exception:
        logging.getLogger(__name__).exception(
            'Failed to record activity entry for action %s on %s %s.',
            entry.action,
            entry.subject_type,
            entry.subject_id,
        )

# *** events

# ** event: activity_event
class ActivityEvent(DomainEvent):
    '''
    Base event providing the shared ActivityService dependency.
    '''

    # * attribute: activity_service
    activity_service: ActivityService

    # * init
    def __init__(self, activity_service: ActivityService) -> None:
        '''
        Initialize the ActivityEvent.

        :param activity_service: The activity service dependency.
        :type activity_service: ActivityService
        '''

        # Set the activity service dependency.
        self.activity_service = activity_service

# ** event: list_activities
class ListActivities(ActivityEvent):
    '''
    List recorded activity entries, newest first, with optional filters.
    '''

    # * method: execute
    def execute(self,
            action: Optional[str] = None,
            subject_type: Optional[str] = None,
            subject_id: Optional[str] = None,
            related_id: Optional[str] = None,
            **kwargs,
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
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The matching activity entries, newest-insertion-first.
        :rtype: List[ActivityAggregate]
        '''

        # Return the filtered, newest-first activity entries from the service.
        return self.activity_service.list(
            action=action,
            subject_type=subject_type,
            subject_id=subject_id,
            related_id=related_id,
        )

"""Lit Review System Events"""

# *** imports

# ** app
from tiferet import DomainEvent

# *** events

# ** event: ping
class Ping(DomainEvent):
    '''
    Smoke-test event proving the application skeleton loads, resolves its
    dependency injection container, and executes a feature step end-to-end.
    '''

    # * method: execute
    def execute(self, **kwargs) -> str:
        '''
        Execute the ping smoke test.

        :param kwargs: Additional keyword arguments (unused).
        :type kwargs: dict
        :return: The literal string 'pong'.
        :rtype: str
        '''

        # Return the smoke-test response.
        return 'pong'

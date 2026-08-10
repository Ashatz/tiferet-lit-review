#!/usr/bin/env python
"""Lit Review CLI Entrypoint"""

# *** imports

# ** core
import sys

# ** app
from tiferet import CLI

from app.blueprints import INTERFACE_ID, APP_CONFIG_FILE

# *** functions

# ** function: main
def main(argv: list = None) -> None:
    '''
    Dispatch CLI arguments through the lit_review CLI blueprint.

    :param argv: Optional argument list; defaults to sys.argv[1:] when None.
    :type argv: list
    :return: None
    :rtype: None
    '''

    # Dispatch argv through the framework's CLI blueprint, pinned to this
    # application's interface id and configuration file.
    CLI(INTERFACE_ID, argv=argv, app_config=APP_CONFIG_FILE)

if __name__ == '__main__':
    main(sys.argv[1:])

#!/usr/bin/env python
"""Lit Review CLI Entrypoint"""

# *** imports

# ** core
import sys

# ** app
from app.blueprints import APP_CONFIG_FILE, build_cli

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

    # Dispatch argv through the app CLI blueprint so LitReviewFeatureContext runs.
    build_cli(argv=argv, app_config=APP_CONFIG_FILE)

if __name__ == '__main__':
    main(sys.argv[1:])

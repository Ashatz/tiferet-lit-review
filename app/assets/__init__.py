"""Lit Review Assets Package

This package also holds the application's configuration YAML files
(app.yml, di.yml, feature.yml, error.yml, cli.yml) -- configs can be
stored here until a more permanent location is decided.
"""

# *** exports

__all__ = [
    'error',
]

# ** app
from . import constants as error

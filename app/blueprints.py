"""Lit Review Application Blueprint"""

# *** imports

# ** app
from tiferet import App as build_tiferet_app

# *** constants

# ** constant: interface_id
INTERFACE_ID = 'lit_review'

# ** constant: app_config_file
APP_CONFIG_FILE = 'app/assets/app.yml'

# *** blueprints

# ** blueprint: build_app
def build_app(app_config: str = APP_CONFIG_FILE):
    '''
    Build the fully wired lit_review application session context.

    Thin composition entrypoint per tiferet-code-blueprints: delegates to the
    framework's own build_app, pinned to this application's interface id and
    configuration file. No business logic lives here.

    :param app_config: The app configuration file path.
    :type app_config: str
    :return: The fully wired app session context.
    :rtype: AppSessionContext
    '''

    # Delegate to the framework's core build_app entrypoint.
    return build_tiferet_app(INTERFACE_ID, app_config=app_config)

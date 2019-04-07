import datetime
from typing import Callable, Dict, Union

import voluptuous as vol
from appdaemon.plugins.hass.hassapi import Hass

from house_config import HOUSE, MODES
import voloptuous_helper as vol_help

CONF_CLASS = 'class'
CONF_MODULE = 'module'
CONF_DEPENDENCIES = 'dependencies'

CONF_DISABLED_STATES = 'disabled_states'
CONF_PRESENCE = 'presence'
CONF_DAYS = 'days'
CONF_MODES = 'modes'
CONF_CLEANING_MODE = 'cleaning_mode'
CONF_GUEST_MODE = 'guest_mode'
CONF_SLEEP_MODE = 'sleep_mode'

APP_SCHEMA = vol.Schema({
    vol.Required(CONF_MODULE): str,
    vol.Required(CONF_CLASS): str,
    vol.Optional(CONF_DEPENDENCIES): vol_help.ensure_list,
    vol.Optional(CONF_DISABLED_STATES): vol.Schema({
        vol.Optional(CONF_PRESENCE): str,
        vol.Optional(CONF_DAYS): str,
        vol.Optional(CONF_MODES): vol.Schema({
            vol.Optional(CONF_CLEANING_MODE): str,
            vol.Optional(CONF_GUEST_MODE): str,
            vol.Optional(CONF_SLEEP_MODE): str,
        }),
    }),
}, extra=vol.ALLOW_EXTRA)


##############################################################################
# App Base configuration
#
# Adds the following dictionaries to the app, these dicts can be added to the
# app configuration file:
#   - disabled_states: dict of states in which the app should be disabled
#   - entities: entities to use in the app
#   - handles: handles to use in the app
#   - notifications: dict for configuration for notifications, target etc.
#   - properties: dict for different properties to be used by the app
# Registers a constraint for disabled states:
#   - The following argument must be added to each listener for the disabled
#     states to trigger:
#       constrain_app_enabled=1
#   - If device/mode which is in disabled states list is 'on' the automation
#     will not trigger, multiple entries in one category must be separated with
#     a comma and no whitespace after the comma
#   - Categories:
#       - presence: house in mode: noone/everyone/vacation/someone
#       - mode: mode is state:
#           cleaning_mode: 'on'
#       - days: day is today: Monday/Tuesday...
#   - In addition there is an input boolean for each app which will disable
#     the app when turned off, if 'enable' is specified in properties then the
#     name of the input boolean will be taken from there otherwise it will be
#     the name of the app
# Creates a reference to each app that is listed in the dependencies list in
# the app configuration
#   - like this the app can use methods or variables from the dependent app
#   - e.g. dependency 'presence_app' this means you can use methods/variables
#     from the app 'presence_app.py' with self.presence_app.'method/variable'
##############################################################################


class AppBase(Hass):
    """Define a base for an automation object."""

    APP_SCHEMA = APP_SCHEMA
    
    def initialize(self) -> None:
        """Initialize."""

        # Check if the app configuration is correct:
        try:
            self.APP_SCHEMA(self.args)
        except vol.Invalid as err:
            self.error(f"Ungültiges Format: {err}", level='ERROR')
            return

        # Define holding place for various configurations
        self.disabled_states = self.args.get('disabled_states', {})
        self.entities = self.args.get('entities', {})
        self.handles = {}
        self.notifications = self.args.get('notifications', {})
        self.properties = self.args.get('properties', {})

        # Register the constraint for the app to be enabled
        self.register_constraint('constrain_app_enabled')

        # Create a reference to every dependency in the configuration
        for app in self.args.get('dependencies', {}):
            if not getattr(self, app, None):
                setattr(self, app, self.get_app(app))

        # Define the input boolean to enable/disable app
        if 'enable' in self.properties:
            self.enable_input_boolean = f"input_boolean.{self.properties['enable']}"
        else:
            self.enable_input_boolean = f"input_boolean.{self.name}"

    def constrain_app_enabled(self, value: str) -> bool:
        """Define enable constraint for automation object."""

        # Disable callback if house state is in the disabled presence config
        if 'presence' in self.disabled_states:
            presence_disable = [
                self.presence_app.HouseState[disabled_state].value
                for disabled_state in self.disabled_states['presence'].split(',')
            ]
            if self.get_state(HOUSE['presence_state']) in presence_disable:
                return False

        # Disable callback if mode state is equal to state the disable modes config
        if 'modes' in self.disabled_states:
            for mode, state in self.disabled_states['modes'].items():
                if self.get_state(MODES[mode]) == state:
                    return False

        # Disable callback if today is in the disable days config
        if 'days' in self.disabled_states:
            disabled_days = self.disabled_states['days'].split(',')
            if datetime.datetime.today().strftime('%A') in disabled_days:
                return False

        if self.get_state(self.enable_input_boolean) == 'off':
            return False
            
        return True

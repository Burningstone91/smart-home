import datetime

from appdaemon.plugins.hass.hassapi import Hass

from house_config import HOUSE, MODES


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
#       - mode: mode is on: cleaning_mode/sleep_mode/guest_mode
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
    def initialize(self) -> None:
        self.disabled_states = self.args.get('disabled_states', {})
        self.entities = self.args.get('entities', {})
        self.handles = {}
        self.notifications = self.args.get('notifications', {})
        self.properties = self.args.get('properties', {})
        
        self.register_constraint('constrain_app_enabled')

        for app in self.args.get('dependencies', {}):
            if not getattr(self, app, None):
                setattr(self, app, self.get_app(app))

        if 'enable' in self.properties:
            self.enable_input_boolean = f"input_boolean.{self.properties['enable']}"
        else:
            self.enable_input_boolean = f"input_boolean.{self.name}"

    def constrain_app_enabled(self, value: str) -> bool:
        if 'presence' in self.disabled_states:
            presence_disable = [
                self.presence_app.HouseState[disabled_state].value
                for disabled_state in self.disabled_states['presence'].split(',')
            ]
            if self.get_state(HOUSE['presence_state']) in presence_disable:
                return False

        if 'modes' in self.disabled_states:
            disabled_modes = self.disabled_states['modes'].split(',')
            for mode, entity in MODES.items():
                if self.get_state(entity) == 'on' and mode in disabled_modes:
                    return False

        if 'days' in self.disabled_states:
            disabled_days = self.disabled_states['days'].split(',')
            if datetime.datetime.today().strftime('%A') in disabled_days:
                return False

        if self.get_state(self.enable_input_boolean) == 'off':
            return False
            
        return True

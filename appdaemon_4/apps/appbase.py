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
#      - mqtt_api: enables or disables the MQTT API, enabled or disabled, defaults to disabled
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
# Creates a reference to the manager app if defined
# the app can then be used like self.manager.'method/variable'
##############################################################################

"""Define a generic object which  all apps/automations inherit from."""
from datetime import datetime as dt
from typing import Union, Optional
import adbase as ad
import voluptuous as vol

from house import HOUSE
from helpers import voluptuous_helper as vol_help


APP_SCHEMA = vol.Schema(
    {
        vol.Required("module"): str,
        vol.Required("class"): str,
        vol.Optional("dependencies"): vol_help.ensure_list,
        vol.Optional("manager"): str,
    },
    extra=vol.ALLOW_EXTRA,
)


class AppBase(ad.ADBase):
    """Define a base automation object."""

    APP_SCHEMA = APP_SCHEMA

    def initialize(self) -> None:
        """Initialize."""
        self.adbase = self.get_ad_api()
        self.hass = self.get_plugin_api("HASS")
        self.mqtt = self.get_plugin_api("MQTT")

        # Validate app configuration
        try:
            self.APP_SCHEMA(self.args)
        except vol.Invalid as err:
            self.adbase.log(
                f"Invalid configuration: {err}", log="error_log"
            )
            return

        # Define holding place for various configurations
        self.app_data = {}

        # Create a reference to every dependency in the configuration
        for app in self.args.get("dependencies", {}):
            if not getattr(self, app, None):
                setattr(self, app, self.adbase.get_app(app))
        
        # Create a reference to the manager app
        if self.args.get('manager'):
            self.manager = getattr(self, self.args['manager'])

        # Register custom constraints
        self.register_constraint("constrain_enabled")
        self.register_constraint("constrain_sleeping")
        self.register_constraint("constrain_presence")
        self.register_constraint("constrain_mode_on")
        self.register_constraint("constrain_mode_off")
        self.register_constraint("constrain_days")

        # Run the app configuration if specified
        if hasattr(self, "configure"):
            self.configure()

        # Define the input boolean to enable/disable app
        if "enable_input_boolean" in self.args:
            self.enable_input_boolean = self.args['enable_input_boolean']
        else:
            self.enable_input_boolean = f"input_boolean.{self.name}"

        @property
        def enabled(self) -> bool:
            """Return whether app is enabled."""
            if not self.hass.entity_exists(self.enable_input_boolean):
                return True
            return self.hass.get_state(self.enable_input_boolean) == "on"

        def constrain_enabled(self, value: bool) -> bool:
            """Execute only if app is enabled."""
            if value:
                return self.enabled
            return False

        def constrain_sleeping(self, value: bool) -> bool:
            """Execute only if app is enabled."""
            return value and self.hass.get_state(HOUSE["sleep_boolean"]) == "on"

        # def constrain_presence(self, house_states: Union[list, str]) -> bool:
        #     """Execute only if house is in specified states."""
        #     if not value:
        #         return True

        #     return getattr(self.presence_app, "house_in_state")(
        #         [self.presence_app.HouseState[s].value for s in house_states.split(",")]
        #     )

        def constrain_mode_on(self, mode: str) -> bool:
            """Execute only if mode is on."""
            return self.hass.get_state(f"input_boolean.{mode}") == "on"

        def constrain_mode_off(self, mode: str) -> bool:
            """Execute only if mode is off."""
            return self.hass.get_state(f"input_boolean.{mode}") == "off"

        def constrain_days(self, mode: str) -> bool:
            """Execute only if today is in specified days."""
            return dt.today().strftime("%A") in mode.split(",")

    # def constrain_app_enabled(self, value: str) -> bool:
    #     """Define enable constraint for automation object. Returns True if app
    #     schould be enabled."""

    #     # Disable callback if house state is in disabled presence config
    #     if "presence" in self.disabled_states:
    #         presence_disable = [
    #             self.presence_app.HouseState[disabled_state].value
    #             for disabled_state in self.disabled_states["presence"]
    #         ]
    #         if self.hass.get_state(HOUSE["presence_state"]) in presence_disable:
    #             return False

    #     # Disable callback if mode state is equal to state in disabled mode config
    #     if "modes" in self.disabled_states:
    #         for mode, state in self.disabled_states["modes"].items():
    #             if self.hass.get_state(MODES[mode]) == state:
    #                 return False

    #     # Disable callback if today is in the disable days config
    #     if "days" in self.disabled_states:
    #         if dt.today().strftime("%A") in self.disabled_states["days"]:
    #             return False

    #     if self.hassget_state(self.enable_input_boolean) == "off":
    #         return False

    #     return True


    # def check_condition(
    #     self, 
    #     entity: str,
    #     state: Union[str, int, float],
    #     operator: Optional[str] = None
    # ) -> bool:
    #     """Check if entity is in state."""
    #     value = self.hass.get_state("entitiy")

    #     if value in ["unavailable", "unknown"]:
    #         return False
        
    #     if not operator and value != state:
    #         return False

    #     if operator == "above" and float(value) <= float(state):
    #         return False

    #     if operator == "below" and float(value) >= float(state):
    #         return False

    #     return True
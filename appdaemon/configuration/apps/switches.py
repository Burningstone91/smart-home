"""Define automations for switches and dimmer switches"""

from typing import Union


import voluptuous as vol

import voloptuous_helper as vol_help
from appbase import APP_SCHEMA, AppBase
from constants import (
    CONF_DELAY, CONF_ENTITIES, CONF_EVENT, CONF_PROPERTIES,
    CONF_PRESENCE_STATE, CONF_SCHEDULE_TIME, CONF_SPECIFIC_PERSON, CONF_STATE)
from house_config import HOUSE, PERSONS


CONF_SWITCH = 'switch'

CONF_ACTION = 'action'
CONF_ACTION_TYPE = 'action_type'
ACTION_TYPES = ('toggle', 'scene', 'service_call')
CONF_ENTITY = 'entity'
CONF_PARAMETERS = 'parameters'

CONF_BUTTON_CONFIG = 'button_config'
DECONZ_EVENT = 'deconz_event'

SHORT_PRESS_ON = 'short_press_on'
LONG_PRESS_ON = 'long_press_on'
SHORT_PRESS_UP = 'short_press_up'
LONG_PRESS_UP = 'long_press_up'
SHORT_PRESS_DOWN = 'short_press_down'
LONG_PRESS_DOWN = 'long_press_down'
SHORT_PRESS_OFF = 'short_press_off'
LONG_PRESS_OFF = 'long_press_off'

CONF_TARGET = 'target'
CONF_TARGET_STATE = 'target_state'


##############################################################################
# example YAML
# turn_off_sleep_mode_forgot:
#   module: switches
#   class: ToggleAtTime
#   dependencies:
#     - presence_app
#   disabled_states:
#     presence: vacation
#   entities:
#     switch: input_boolean.sleep_mode
#   properties:
#     type:                        # toggle, scene or service_call
#     schedule_time: "13:30:00"    # only for class ToggleAtTime
#     specific_person: Dimitri     # optional for class ToggleOnArrival, if
#                                    if specified it will only trigger when
#                                    the specified person arrives alone
#     state: "off"                 # target state of the switch or the action
#                                    if a service should be called
#     target: light.office         # only for class ToggleOnStateChange,
#                                    specifies the entity that should be
#                                    monitored for state changes
#     target_state: "off"          # state of monitored entity on which the
#                                    the switch triggers
#     parameters:                  # optional, if specified it defines the
#                                    parameters for the service call
#       brightness: 250
#       transition: 2
#     button_config:               # only for class HueDimmerSwitch
#       short_press_on:
#         action_type: 'service_call'
#         action: 'turn_on'
#         entity: 'light.wohnzimmer'
#         parameters:
#           brightness: 250
#
##############################################################################


class SwitchBase(AppBase):
    """Define a base feature to take action for switches."""

    def initialize(self) -> None:
        """Initialize."""

        super().initialize()
        
        self.switch = self.entities[CONF_SWITCH]
        self.action_type = self.properties.get(CONF_ACTION_TYPE)
        self.delay = self.properties.get(CONF_DELAY)
        self.state = self.properties.get(CONF_STATE)
        self.parameters = self.properties.get(CONF_PARAMETERS, {})

    def action(self, action_type: str, state: str,
               entity: str, **kwargs: dict) -> None:
        if action_type == 'toggle':
            if self.get_state(entity) == 'off' and state == 'on':
                self.turn_on(entity)
            elif self.get_state(entity) == 'on' and state == 'off':
                self.turn_off(entity)
        elif action_type == 'scene':
            self.turn_on(entity)
        else:
            self.call_service(
                f"{entity.split('.')[0]}/{state}",
                entity_id=entity,
                **kwargs
            )

    def action_on_schedule(self, kwargs: dict) -> None:
        self.action(
            kwargs['action_type'],
            kwargs['state'],
            kwargs['action_entity'],
            **kwargs.get('parameters')
        )

        
class ToggleOnStateChange(SwitchBase):
    """Define a feature to take action when an entity enters a state."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(CONF_SWITCH): vol_help.entity_id,
            vol.Required(CONF_TARGET): vol_help.entity_id,
        }, extra=vol.ALLOW_EXTRA),
        CONF_PROPERTIES: vol.Schema({
            vol.Required(CONF_ACTION_TYPE): vol.In(ACTION_TYPES),
            vol.Required(CONF_TARGET_STATE): str,
            vol.Required(CONF_STATE):  str,
            vol.Optional(CONF_DELAY): int,
            vol.Optional(CONF_PARAMETERS): dict,
        }, extra=vol.ALLOW_EXTRA)
    })

    def initialize(self) -> None:
        """Initialize."""

        super().initialize()

        self.listen_state(
            self.state_change,
            self.entities[CONF_TARGET],
            new=self.properties[CONF_TARGET_STATE],
            constrain_app_enabled=1
        )

    def state_change(self, entity: Union[str, dict], attribute: str,
                     old: str, new: str, kwargs: dict) -> None:
        """Take action when entity enters target state."""

        if self.delay:
            self.run_in(
                self.action_on_schedule,
                self.delay * 60,
                action_type=self.action_type,
                state=self.state,
                action_entity=self.switch,
                parameters=self.parameters
            )
        else:
            self.action(
                self.action_type,
                self.state,
                self.switch,
                **self.parameters
            )


class ToggleAtTime(SwitchBase):
    """Define a feature to take action on certain time."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(CONF_SWITCH): vol_help.entity_id,
        }, extra=vol.ALLOW_EXTRA),
        CONF_PROPERTIES: vol.Schema({
            vol.Required(CONF_ACTION_TYPE): vol.In(ACTION_TYPES),
            vol.Required(CONF_STATE): str,
            vol.Required(CONF_SCHEDULE_TIME): str,
            vol.Optional(CONF_PARAMETERS): dict,
        }, extra=vol.ALLOW_EXTRA)
    })

    def initialize(self) -> None:
        """ Initialize."""

        super().initialize()

        # Take action on specified time
        self.run_daily(
            self.action_on_schedule,
            self.parse_time(self.properties[CONF_SCHEDULE_TIME]),
            action_type=self.action_type,
            state=self.state,
            action_entity=self.switch,
            parameters=self.parameters,
            constrain_app_enabled=1
        )


class ToggleOnArrival(SwitchBase):
    """Define a feature to take action on arrival of person/everyone."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(CONF_SWITCH): vol_help.entity_id,
        }, extra=vol.ALLOW_EXTRA),
        CONF_PROPERTIES: vol.Schema({
            vol.Required(CONF_ACTION_TYPE): vol.In(ACTION_TYPES),
            vol.Required(CONF_STATE): str,
            vol.Optional(CONF_SPECIFIC_PERSON): vol.In(PERSONS.keys()),
            vol.Optional(CONF_PARAMETERS): dict,
        }, extra=vol.ALLOW_EXTRA)
    })

    def initialize(self) -> None:
        """Initialize."""

        super().initialize()

        self.person = self.properties.get(CONF_SPECIFIC_PERSON)

        self.listen_state(
            self.someone_arrived,
            HOUSE[CONF_PRESENCE_STATE],
            constrain_app_enabled=1
        )

    def someone_arrived(self, entity: Union[str, dict], attribute: str,
                        old: str, new: str, kwargs: dict) -> None:
        """Take action when a person arrives."""

        someone_home_states = [
            self.presence_app.HouseState.someone.value,
            self.presence_app.HouseState.everyone.value
        ]

        # Only take action if noone was home before
        if (new in someone_home_states) and (old not in someone_home_states):
            persons_home = self.presence_app.persons_home

            if ((self.person in persons_home and len(persons_home) == 1) or
                    not self.person):
                if self.delay:
                    self.run_in(
                        self.action_on_schedule,
                        self.delay * 60,
                        action_type=self.action_type,
                        state=self.state,
                        action_entity=self.switch,
                        parameters=self.parameters
                    )
                else:
                    self.action(
                        self.action_type,
                        self.state,
                        self.switch,
                        **self.parameters
                    )


class ToggleOnDeparture(SwitchBase):
    """Define a feature to take action when everyone leaves."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(CONF_SWITCH): vol_help.entity_id,
        }, extra=vol.ALLOW_EXTRA),
        CONF_PROPERTIES: vol.Schema({
            vol.Required(CONF_ACTION_TYPE): vol.In(ACTION_TYPES),
            vol.Required(CONF_STATE): str,
            vol.Optional(CONF_PARAMETERS): dict,
        }, extra=vol.ALLOW_EXTRA)
    })

    def initialize(self) -> None:
        """Initialize."""

        super().initialize()

        self.listen_state(
            self.everyone_left,
            HOUSE[CONF_PRESENCE_STATE],
            new=self.presence_app.HouseState.noone.value,
            constrain_app_enabled=1
        )

    def everyone_left(self, entity: Union[str, dict], attribute: str,
                      old: str, new: str, kwargs: dict):
        """Take action when everyone left the house."""

        if self.delay:
            self.run_in(
                self.action_on_schedule,
                self.delay * 60,
                action_type=self.action_type,
                state=self.state,
                action_entity=self.switch,
                parameters=self.parameters
            )
        else:
            self.action(
                self.action_type,
                self.state,
                self.switch,
                **self.parameters
            )


class HueDimmerSwitch(SwitchBase):
    """Define a Hue Dimmer Switch automation object."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(CONF_SWITCH): str,
        }, extra=vol.ALLOW_EXTRA),
        CONF_PROPERTIES: vol.Schema({
            vol.Required(CONF_BUTTON_CONFIG): dict,
        }, extra=vol.ALLOW_EXTRA)
    })

    def initialize(self) -> None:
        """Initialize."""

        super().initialize()

        self.button_config = self.properties[CONF_BUTTON_CONFIG]
        self.button_map = {
            1002: SHORT_PRESS_ON, 1003: LONG_PRESS_ON,
            2002: SHORT_PRESS_UP, 2003: LONG_PRESS_UP,
            3002: SHORT_PRESS_DOWN, 3003: LONG_PRESS_DOWN,
            4002: SHORT_PRESS_OFF, 4003: LONG_PRESS_OFF
        }

        self.listen_event(
            self.button_pressed,
            DECONZ_EVENT,
            id=self.switch,
            constrain_app_enabled=1
        )

    def button_pressed(self, event_name: str, data: dict,
                       kwargs: dict) -> None:
        """Take action when button is pressed on dimmer switch."""

        button_code = data[CONF_EVENT]
        button_name = self.button_name(button_code)

        if button_name in self.button_config:
            button_conf = self.button_config[button_name]
            action_type = button_conf[CONF_ACTION_TYPE]
            entity = button_conf[CONF_ENTITY]
            action = button_conf.get(CONF_ACTION)
            delay = button_conf.get(CONF_DELAY)
            parameters = button_conf.get(CONF_PARAMETERS, {})

            if action_type == 'dim':
                brightness = self.get_state(entity, attribute='brightness') or 0
                new_brightness = brightness - 25
                if new_brightness <= 0:
                    self.turn_off(entity)
                else:
                    self.turn_on(entity, brightness=new_brightness)
            elif action_type == 'brighten':
                brightness = self.get_state(entity, attribute='brightness') or 0
                new_brightness = brightness + 25
                if new_brightness > 255:
                    new_brightness = 255
                self.turn_on(entity, brightness=new_brightness)
            else:
                if delay:
                    self.run_in(
                        self.action_on_schedule,
                        delay * 60,
                        action_type=action_type,
                        state=action,
                        action_entity=entity,
                        parameters=parameters
                    )
                else:
                    self.action(
                        action_type,
                        action,
                        entity,
                        **parameters
                    )

    def button_name(self, button_code: int) -> Union[str, None]:
        """Return the button name for the provided code."""

        try:
            return self.button_map[button_code]
        except KeyError:
            return None

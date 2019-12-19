"""Define automations for switches and dimmer switches"""

from typing import Union

import voluptuous as vol

import voluptuous_helper as vol_help
from appbase import APP_SCHEMA, AppBase
from constants import (
    CONF_DELAY,
    CONF_ENTITIES,
    CONF_EVENT,
    CONF_PROPERTIES,
    CONF_PRESENCE_STATE,
    CONF_SCHEDULE_TIME,
    CONF_SPECIFIC_PERSON,
    CONF_STATE,
)
from house_config import HOUSE, PERSONS


CONF_SWITCH = "switch"

CONF_ACTION = "action"
CONF_ACTION_TYPE = "action_type"
ACTION_TYPES = ("toggle", "scene", "service_call", "dim", "brighten")
CONF_ACTION_ENTITY = "action_entity"
CONF_PARAMETERS = "parameters"

CONF_BUTTON_CONFIG = "button_config"
DECONZ_EVENT = "deconz_event"

SHORT_PRESS_ON = "short_press_on"
LONG_PRESS_ON = "long_press_on"
SHORT_PRESS_UP = "short_press_up"
LONG_PRESS_UP = "long_press_up"
SHORT_PRESS_DOWN = "short_press_down"
LONG_PRESS_DOWN = "long_press_down"
SHORT_PRESS_OFF = "short_press_off"
LONG_PRESS_OFF = "long_press_off"
BUTTON_PRESSES = (
    SHORT_PRESS_ON,
    LONG_PRESS_ON,
    SHORT_PRESS_UP,
    LONG_PRESS_UP,
    SHORT_PRESS_DOWN,
    LONG_PRESS_DOWN,
    SHORT_PRESS_OFF,
    LONG_PRESS_OFF,
)

CONF_TARGET = "target"
CONF_TARGET_STATE = "target_state"


class SwitchBase(AppBase):
    """Define a base feature to take action for switches."""

    def action(
        self, action_type: str, state: str, action_entity: str, **kwargs: dict
    ) -> None:
        """Take action."""
        if action_type == "toggle":
            if self.get_state(action_entity) == "off" and state == "on":
                self.turn_on(action_entity)
                self.log(f"{action_entity} wurde eingeschaltet.")
            elif self.get_state(action_entity) == "on" and state == "off":
                self.turn_off(action_entity)
                self.log(f"{action_entity} wurde ausgeschaltet.")
        else:
            self.call_service(
                f"{action_entity.split('.')[0]}/{state}",
                entity_id=action_entity,
                **kwargs,
            )
            self.log(f"{state} {action_entity} wurde ausgeführt.")

    def action_on_schedule(self, kwargs: dict) -> None:
        """Take action on specified time."""
        self.action(
            kwargs[CONF_ACTION_TYPE],
            kwargs[CONF_STATE],
            kwargs[CONF_ACTION_ENTITY],
            **kwargs.get(CONF_PARAMETERS),
        )


class ToggleOnStateChange(SwitchBase):
    """Define a feature to take action when an entity enters a state."""

    APP_SCHEMA = APP_SCHEMA.extend(
        {
            CONF_ENTITIES: vol.Schema(
                {
                    vol.Required(CONF_SWITCH): vol_help.entity_id,
                    vol.Required(CONF_TARGET): vol_help.entity_id,
                },
                extra=vol.ALLOW_EXTRA,
            ),
            CONF_PROPERTIES: vol.Schema(
                {
                    vol.Required(CONF_ACTION_TYPE): vol.In(ACTION_TYPES),
                    vol.Required(CONF_TARGET_STATE): str,
                    vol.Required(CONF_STATE): str,
                    vol.Optional(CONF_DELAY): int,
                    vol.Optional(CONF_PARAMETERS): dict,
                },
                extra=vol.ALLOW_EXTRA,
            ),
        }
    )

    def configure(self) -> None:
        """Configure."""
        self.switch = self.entities[CONF_SWITCH]
        self.action_type = self.properties[CONF_ACTION_TYPE]
        self.state = self.properties[CONF_STATE]
        self.delay = self.properties.get(CONF_DELAY)
        self.parameters = self.properties.get(CONF_PARAMETERS, {})

        self.listen_state(
            self.state_change,
            self.entities[CONF_TARGET],
            new=self.properties[CONF_TARGET_STATE],
            constrain_app_enabled=1,
        )

    def state_change(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Take action when entity enters target state."""
        if self.delay:
            self.run_in(
                self.action_on_schedule,
                self.delay * 60,
                action_type=self.action_type,
                state=self.state,
                action_entity=self.switch,
                parameters=self.parameters,
            )
        else:
            self.action(self.action_type, self.state, self.switch, **self.parameters)


class ToggleAtTime(SwitchBase):
    """Define a feature to take action on certain time."""

    APP_SCHEMA = APP_SCHEMA.extend(
        {
            CONF_ENTITIES: vol.Schema(
                {vol.Required(CONF_SWITCH): vol_help.entity_id}, extra=vol.ALLOW_EXTRA
            ),
            CONF_PROPERTIES: vol.Schema(
                {
                    vol.Required(CONF_ACTION_TYPE): vol.In(ACTION_TYPES),
                    vol.Required(CONF_STATE): str,
                    vol.Required(CONF_SCHEDULE_TIME): str,
                    vol.Optional(CONF_PARAMETERS): dict,
                },
                extra=vol.ALLOW_EXTRA,
            ),
        }
    )

    def configure(self) -> None:
        """Configure."""
        self.switch = self.entities[CONF_SWITCH]
        self.action_type = self.properties[CONF_ACTION_TYPE]
        self.state = self.properties[CONF_STATE]
        self.parameters = self.properties.get(CONF_PARAMETERS, {})

        self.run_daily(
            self.action_on_schedule,
            self.parse_time(self.properties[CONF_SCHEDULE_TIME]),
            action_type=self.action_type,
            state=self.state,
            action_entity=self.switch,
            parameters=self.parameters,
            constrain_app_enabled=1,
        )


class ToggleOnArrival(SwitchBase):
    """Define a feature to take action on arrival of person/everyone."""

    APP_SCHEMA = APP_SCHEMA.extend(
        {
            CONF_ENTITIES: vol.Schema(
                {vol.Required(CONF_SWITCH): vol_help.entity_id}, extra=vol.ALLOW_EXTRA
            ),
            CONF_PROPERTIES: vol.Schema(
                {
                    vol.Required(CONF_ACTION_TYPE): vol.In(ACTION_TYPES),
                    vol.Required(CONF_STATE): str,
                    vol.Optional(CONF_SPECIFIC_PERSON): vol.In(PERSONS.keys()),
                    vol.Optional(CONF_PARAMETERS): dict,
                },
                extra=vol.ALLOW_EXTRA,
            ),
        }
    )

    def configure(self) -> None:
        """Configure."""
        self.switch = self.entities[CONF_SWITCH]
        self.action_type = self.properties[CONF_ACTION_TYPE]
        self.state = self.properties[CONF_STATE]
        self.delay = self.properties.get(CONF_DELAY)
        self.parameters = self.properties.get(CONF_PARAMETERS, {})
        self.person = self.properties.get(CONF_SPECIFIC_PERSON)

        self.listen_state(
            self.someone_arrived, HOUSE[CONF_PRESENCE_STATE], constrain_app_enabled=1
        )

    def someone_arrived(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Take action when a person arrives."""
        someone_home_states = [
            self.presence_app.HouseState.someone.value,
            self.presence_app.HouseState.everyone.value,
        ]

        # Only take action if noone was home before
        if (new in someone_home_states) and (old not in someone_home_states):
            persons_home = self.presence_app.persons_home
            # Only take action if specified person arrives alone or no
            # person was specified
            if (
                self.person in persons_home and len(persons_home) == 1
            ) or not self.person:
                if self.delay:
                    self.run_in(
                        self.action_on_schedule,
                        self.delay * 60,
                        action_type=self.action_type,
                        state=self.state,
                        action_entity=self.switch,
                        parameters=self.parameters,
                    )
                else:
                    self.action(
                        self.action_type, self.state, self.switch, **self.parameters
                    )


class ToggleOnDeparture(SwitchBase):
    """Define a feature to take action when everyone leaves."""

    APP_SCHEMA = APP_SCHEMA.extend(
        {
            CONF_ENTITIES: vol.Schema(
                {vol.Required(CONF_SWITCH): vol_help.entity_id}, extra=vol.ALLOW_EXTRA
            ),
            CONF_PROPERTIES: vol.Schema(
                {
                    vol.Required(CONF_ACTION_TYPE): vol.In(ACTION_TYPES),
                    vol.Required(CONF_STATE): str,
                    vol.Optional(CONF_PARAMETERS): dict,
                },
                extra=vol.ALLOW_EXTRA,
            ),
        }
    )

    def configure(self) -> None:
        """Configure."""
        self.switch = self.entities[CONF_SWITCH]
        self.action_type = self.properties[CONF_ACTION_TYPE]
        self.state = self.properties[CONF_STATE]
        self.delay = self.properties.get(CONF_DELAY)
        self.parameters = self.properties.get(CONF_PARAMETERS, {})

        self.listen_state(
            self.everyone_left,
            HOUSE[CONF_PRESENCE_STATE],
            new=self.presence_app.HouseState.noone.value,
            constrain_app_enabled=1,
        )

    def everyone_left(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Take action when everyone left the house."""
        if self.delay:
            self.run_in(
                self.action_on_schedule,
                self.delay * 60,
                action_type=self.action_type,
                state=self.state,
                action_entity=self.switch,
                parameters=self.parameters,
            )
        else:
            self.action(self.action_type, self.state, self.switch, **self.parameters)


class DeconzLightSwitch(SwitchBase):
    """Define a Hue Dimmer Switch base feature"""

    def configure(self) -> None:
        """Configure"""
        self.button_map = {
            1000: "short_press_on",
            1002: "short_press_on_release",
            1001: "long_press_on",
            1003: "long_press_on_release",
            2000: "short_press_up",
            2002: "short_press_up_release",
            2001: "long_press_up",
            2003: "long_press_up_release",
            3000: "short_press_down",
            3002: "short_press_down_release",
            3001: "long_press_down",
            3003: "long_press_down_release",
            4000: "short_press_off",
            4002: "short_press_off_release",
            4001: "long_press_off",
            4003: "long_press_off_release",
        }
        # configure entities
        self.light = self.entities["light"]
        self.switch = self.entities["switch"]

        # get the advanced button config
        self.button_config = self.properties

        # set defaults for release of ON/OFF button after short press
        if "short_press_on_release" not in self.button_config:
            self.button_config["short_press_on_release"] = {
                "action_type": "turn_on",
                "entity": self.light,
                "parameters": {"brightness": 255}
            }
        if "short_press_off_release" not in self.button_config:
            self.button_config["short_press_off_release"] = {
                "action_type": "turn_off",
                "entity": self.light,
                "parameters": {},
            }

        # check if the light is a deconz group or single bulb
        if self.get_state(self.light, attribute="is_deconz_group"):
            self.deconz_field = "/action"
        else:
            self.deconz_field = "/state"

        # take action when button is pressed
        self.listen_event(
            self.button_pressed_cb,
            "deconz_event",
            id=self.switch
        )

    def button_pressed_cb(self, event_name: str, data: dict, kwargs: dict) -> None:
        """Take action when button is pressed on dimmer switch."""
        button_code = data["event"]
        button_name = self.button_map[button_code]

        if button_name == "long_press_up":
            self.dim_light("up")
        elif button_name == "long_press_down":
            self.dim_light("down")
        elif button_name in ["long_press_up_release", "long_press_down_release"]:
            self.stop_dim_light()
        elif button_name in self.button_config:
            delay = self.button_config.get(CONF_DELAY)
            action_type = "service_call"
            action = self.button_config["service"]
            action_entity = self.button_config["entity"]
            parameters = self.button_config.get("parameters", {})
            if delay:
                self.run_in(
                    self.action_on_schedule,
                    delay * 60,
                    action_type=action_type,
                    state=action,
                    action_entity=action_entity,
                    parameters=parameters,
                )
            else:
                self.action(action_type, action, action_entity, **parameters)


    def dim_light(self, direction: str) -> None:
        """In-/decrease brightness of light through service call to deCONZ."""
        if direction == "up":
            bri_inc = 254
        else:
            bri_inc = -254

        self.call_service(
            "deconz/configure",
            field=self.deconz_field,
            entity=self.light,
            data={"bri_inc": bri_inc, "transitiontime": 50}
        )

    def stop_dim_light(self) -> None:
        """Stop dimming of light through service call to deCONZ."""
        self.call_service(
            "deconz/configure",
            field=self.deconz_field,
            entity=self.light,
            data={"bri_inc": 0}
        )

    def action(self, button_config: dict) -> None:
        """Call the respective service based on the passed button config."""
        action_type = button_config["action_type"]
        entity = button_config["entity"]
        parameters = button_config.get("parameters", {})

        self.call_service(
            f"{entity.split('.')[0]}/{action_type}", 
            entity_id=entity, 
            **parameters
        )

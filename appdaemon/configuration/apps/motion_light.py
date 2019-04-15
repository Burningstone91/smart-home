"""Define automations for motion based lights."""

from typing import Union

import voluptuous as vol

import voloptuous_helper as vol_help
from appbase import AppBase, APP_SCHEMA
from constants import (
    CONF_BRIGHTNESS_LEVEL, CONF_DELAY, CONF_ENTITIES,
    CONF_LIGHT_COLOR, CONF_LIGHTS, CONF_PROPERTIES, ON, HOME
)


##############################################################################
# App to turn on light when motion is detected, then turn off after a delay
# If one of the no_action_devices is on (PC, AV Receiver, etc) a trigger of
# the motion sensor has no effect, light turns only on if lux is above
# threshold
#
# args:
#
# entities:
#   motion_sensor: entity id of motion sensor
#   lux_sensor: entity id of lux sensor
#   no_action_entities: devices which will lead to no action on motion if they are on
#   lights: light entities for each state of day
#     morning:
#     day:
#     night:
# properties:
#   lux_threshold: value above which light will not turn on, default 100 lux
#   delay: minutes until light turns off when no motion, default 300 sec
#   day_state_time:
#     morning: 05:30:00
#     day: 11:30:00
#     night: 22:00:00
#   brightness_level: brightness level in % for each state of day, default 75%
#     morning: 20
#     day: 80
#     night: 30
#   light_color: light color for each state of day, e.g. orange, default white
#     morning: orange
#     day: white
#     night: orange

##############################################################################


LIGHT_TIMER = 'light_timer'

CONF_MOTION_SENSOR = 'motion_sensor'
CONF_LUX_SENSOR = 'lux_sensor'
CONF_DAY_STATE_TIME = 'day_state_time'
CONF_NO_ACTION_ENTITIES = 'no_action_entities'
CONF_LUX_THRESHOLD = 'lux_threshold'

ON_STATES = [ON, HOME]

MORNING = 'morning'
DAY = 'day'
NIGHT = 'night'
DAY_STATES = [MORNING, DAY, NIGHT]


class MotionLightAutomation(AppBase):
    """Define a base feature for motion based lights."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(CONF_MOTION_SENSOR): vol_help.entity_id,
            vol.Optional(CONF_LUX_SENSOR): vol_help.entity_id,
            vol.Required(CONF_LIGHTS): vol.Schema({
                vol.Required(MORNING): vol_help.entity_id_list,
                vol.Required(DAY): vol_help.entity_id_list,
                vol.Required(NIGHT): vol_help.entity_id_list,
            }),
        }, extra=vol.ALLOW_EXTRA),
        CONF_PROPERTIES: vol.Schema({
            vol.Optional(CONF_LUX_THRESHOLD): int,
            vol.Optional(CONF_DELAY): int,
            vol.Required(CONF_DAY_STATE_TIME): vol.Schema({
                vol.Required(MORNING): str,
                vol.Required(DAY): str,
                vol.Required(NIGHT): str,
            }),
            vol.Optional(CONF_BRIGHTNESS_LEVEL): vol.Schema({
                vol.Optional(vol.In(DAY_STATES)): int,
            }),
            vol.Optional(CONF_LIGHT_COLOR): vol.Schema({
                vol.Optional(vol.In(DAY_STATES)): str,
            }),
        }, extra=vol.ALLOW_EXTRA),
    })

    def configure(self) -> None:
        """Configure."""
        self.motion_sensor = self.entities[CONF_MOTION_SENSOR]
        self.delay = self.properties.get(CONF_DELAY, 5) * 60
        self.no_action_entities = self.entities.get(CONF_NO_ACTION_ENTITIES, '')

        self.day_state_map = self.properties[CONF_DAY_STATE_TIME]
        self.brightness_map = self.properties.get(CONF_BRIGHTNESS_LEVEL, {})
        self.color_map = self.properties.get(CONF_LIGHT_COLOR, {})
        self.lights_map = self.entities[CONF_LIGHTS]

        # creates a list of a split of each element in self.lights_map
        self.all_lights = set()
        for lights in self.lights_map.values():
            for light in lights.split(','):
                self.all_lights.add(light)
        
        self.room_name = self.motion_sensor.split('.')[1].split('_', 1)[-1].capitalize()

        self.listen_state(
            self.motion,
            self.motion_sensor,
            new=ON,
            constrain_app_enabled=1)

    def motion(self, entity: Union[str, dict], attribute: str,
               old: str, new: str, kwargs: dict) -> None:
        """Take action on motion."""
        self.log(f"Bewegung im {self.room_name} erkannt.")
        if not self.no_action_entities_on:
            if self.lights_on:
                self.log("Licht ist bereits an, Timer neustarten.")
                self.turn_off_delayed()
            elif self.lux_high:
                self.log("Lichtstärke ist genug hoch, keine Aktion.")
            else:
                self.turn_light_on()
                self.turn_off_delayed()

    def turn_light_on(self) -> None:
        """Turn lights on based on state of day."""
        for entity in self.lights:
            self.turn_on(
                entity,
                brightness=self.brightness,
                color_name=self.light_color)

        self.log(f"Das Licht im {self.room_name} "
                 f"wurde durch Bewegung eingeschaltet.")

    def turn_light_off(self, *args: list) -> None:
        """Turn lights off if none of the no action entities is on."""
        if not self.no_action_entities_on:
            for entity in self.lights_on:
                self.turn_off(entity)
            self.log(f"Das Licht im {self.room_name} "
                     f"wurde durch den Timer ausgeschaltet.")

    def turn_off_delayed(self) -> None:
        """Set timer to turn light off after specified delay."""
        if LIGHT_TIMER in self.handles:
            self.cancel_timer(self.handles[LIGHT_TIMER])
            self.handles.pop(LIGHT_TIMER)
        self.handles[LIGHT_TIMER] = self.run_in(self.turn_light_off,
                                                self.delay)
        self.log(f"Ein Timer von {round(self.delay / 60)} Minuten "
                 f"wurde im {self.room_name} eingeschaltet.")

    @property
    def no_action_entities_on(self) -> list:
        """Return list of no action entities that are on"""
        return [
            entity for entity in self.no_action_entities.split(',')
            if self.get_state(entity) in ON_STATES
        ]

    @property
    def lights_on(self) -> list:
        """Return list of lights that are on."""
        return [
            entity for entity in self.all_lights
            if self.get_state(entity) == ON
        ]

    @property
    def lux_high(self) -> bool:
        """Return true if lux in room is above threshold."""
        if CONF_LUX_SENSOR in self.entities:
            lux_sensor = self.entities[CONF_LUX_SENSOR]
            lux_threshold = self.properties.get(CONF_LUX_THRESHOLD, 100)
            return float(self.get_state(lux_sensor)) > float(lux_threshold)
        return False

    @property
    def day_state(self) -> str:
        """Return the state of the day based on the current time."""
        if self.now_is_between(
                self.day_state_map[MORNING],
                self.day_state_map[DAY]):
            return MORNING
        elif self.now_is_between(
                self.day_state_map[DAY],
                self.day_state_map[NIGHT]):
            return DAY
        else:
            return NIGHT

    @property
    def lights(self) -> list:
        """Return list of lights to turn on based on state of day."""
        return [
            entity for entity in self.lights_map[self.day_state].split(',')
        ]

    @property
    def brightness(self) -> float:
        """Return brightness to set light to based on state of day."""
        brightness_level = self.brightness_map.get(self.day_state, 75)
        return 255 / 100 * int(brightness_level)

    @property
    def light_color(self) -> str:
        """Return light color to set light to based on state of day."""
        return self.color_map.get(self.day_state, 'white')

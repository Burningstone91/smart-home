"""Define automations for Hue Dimmer switches"""

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


##############################################################################
# Hue Dimmer Switch Configuration
#
# With the basic configuration the behaviour is as follows:
# Short press of ON button turns light on at 50%, long press at 100%.
# As long as the "increase brightness" button is pressed, the brightness is
# increased until the button gets released. The same principle applies to the
# "decrease brightness" button. A short press of the OFF button turns of the
# light.
#
# Basic configuration:
#   entities:
#     switch: dimmer_switch_bedroom (required)
#     light: light.bedroom (required)
#
# The action for short/long press of the ON and OFF button can be overwritten.
# The available actions to overwrite the basic configuration are "turn_on",
# "turn_off" and "service_call".
#
# Advanced configuration showing each action type:
#   entities:
#     switch: dimmer_switch_bedroom (required)
#     light: light.bedroom (required)
#   properties:
#     short_press_on:
#       action_type: turn_on
#       entity: scene.good_night
#     long_press_on:
#       action_type: service_call
#       entity: light.bedroom
#       service: turn_on
#       parameters:
#         brightness: 255
#         color_name: blue
#     short_press_off:
#       action_type: turn_off
#       entity: light.bedroom
#     long_press_off:
#       action_type: turn_off
#       entity: group.bedroom
#
# Button Codes:
# 1000: short press ON              1001: long press ON
# 1002: short press release ON      1003: long press release ON
# 2000: short press UP              2001: long press UP
# 2002: short press release UP      2003: long press release UP
# 3000: short press DOWN            3001: long press DOWN
# 3002: short press release DOWN    3003: long press release DOWN
# 4000: short press OFF             4001: long press OFF
# 4002: short press release OFF     4003: long press release OFF
##############################################################################


class HueDimmerSwitch(AppBase):
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
        self.button_config = {}

        # get the advanced button config or create default config
        if "short_press_on" in self.properties:
            self.button_config["short_press_on"] = self.properties["short_press_on"]
        else:
            self.button_config["short_press_on"] = {
                "action_type": "turn_on",
                "entity": self.light,
                "parameters": {"brightness": 255}
            }
        if "long_press_on" in self.properties:
            self.button_config["long_press_on"] = self.properties["long_press_on"]
        if "short_press_off" in self.properties:
            self.button_config["short_press_off"] = self.properties["short_press_off"]
        else:
            self.button_config["short_press_off"] = {
                "action_type": "turn_off",
                "entity": self.light,
                "parameters": {},
            }
        if "long_press_off" in self.properties:
            self.button_config["long_press_off"] = self.properties["long_press_off"]

        self.log(self.button_config)
        # check if the light is a deconz group or not
        if self.get_state(self.light, attribute="is_deconz_group"):
            self.deconz_field = "/action"
        else:
            self.deconz_field = "/state"

        # take action when button is pressed
        self.listen_event(
            self.button_pressed_cb,
            "deconz_event",
            id=self.switch,
            constrain_app_enabled=1,
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
            self.action(self.button_config[button_name])

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

    def stop_dim_light(self):
        """Stop dimming of light through service call to deCONZ."""
        self.call_service(
            "deconz/configure",
            field=self.deconz_field,
            entity=self.light,
            data={"bri_inc": 0}
        )

    def action(self, button_config: dict):
        """Call the respective service based on the button config."""
        action_type = button_config["action_type"]
        entity = button_config["entity"]
        parameters = button_config.get("parameters", {})

        self.call_service(
            f"{entity.split('.')[0]}/{action_type}", entity_id=entity, **parameters
        )

    def test_callback(self, event_name: str, data: dict, kwargs: dict) -> None:
        timestamp = json.loads(data["payload"])["timestamp"]
        self.log(timestamp)
        # self.mark_task_completed()

        # self.mqtt.listen_event(
        #    self.test_callback,
        #    "MQTT_MESSAGE",
        #    topic='homeassistant/sensor/matratze_gewendet/state',
        #    namespace="mqtt"
        # )

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
        self.light = self.entities['light']
        self.switch = self.entities['switch']
        self.advanced_config = self.properties

    def increase_brightness(self):
        if self.get_state(self.light, attribute="is_deconz_group") == "true":
            field = '/action'
        else:
            field = '/state'

        self.call_service(
            "deconz/configure",
            field=field,
            entity=self.light,
            data={"bri_inc": 254, "transitiontime": 50}
        )

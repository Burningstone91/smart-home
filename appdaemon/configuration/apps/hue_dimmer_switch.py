"""Define automations for Hue Dimmer switches"""
##############################################################################
# Hue Dimmer Switch Configuration
#
# With the basic configuration the behaviour is as follows:
# Short press of ON button turns light on at 50%, long press at 100%. A short
# press of the OFF button turns off the light.
# As long as the "increase brightness" button is pressed, the brightness is
# increased. Once the button is released the dimming stops. The same 
# principle applies to the "decrease brightness" button. 
#
# Basic configuration:
#   entities:
#     switch: dimmer_switch_bedroom (required)
#     light: light.bedroom (required)
#
# The button presses can be overwritten and other button presses can be added.
# The available actions to assign to a button press are "turn_on", "turn_off"
# and "service_call".
# The configuration for a service call looks like this.
#
# button_press_name:
#   action_type: turn_on | turn_off | service_call
#   
# example:
#   entities:
#     switch: dimmer_switch_bedroom (required)
#     light: light.bedroom (required)
#   advanced:
#     short_press_on_release: (optional)
#       action_type: turn_on
#       entity: scene.good_night
#     long_press_on_release: (optional)
#       action_type: service_call
#       entity: light.bedroom
#       service: turn_on
#       parameters:
#         brightness: 255
#         color_name: blue
#     short_press_off_release (optional):
#       action_type: turn_off
#       entity: light.bedroom
#     long_press_off_release (optional):
#       action_type: turn_off
#       entity: group.bedroom
#
# Button Codes:
# 1000: short_press_on              1001: long_press_on
# 1002: short_press_on_release      1003: long_press_on_release
# 2000: short_press_up              2001: long_press_up
# 2002: short_press_up_release      2003: long_press_up_release
# 3000: short_press_down            3001: long_press_down
# 3002: short_press_down_release    3003: long_press_down_release
# 4000: short_press_off             4001: long_press_off
# 4002: short_press_off_release     4003: long_press_off_release
##############################################################################


from appdaemon.plugins.hass.hassapi import Hass


class HueDimmerSwitch(Hass):
    """Define a Hue Dimmer Switch base feature"""

    def initialize(self) -> None:
        """Configure"""
        self.set_namespace("hass")

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
        entities = self.args["entities"]
        self.light = entities["light"]
        self.switch = entities["switch"]

        # get the advanced button config
        self.button_config = self.args.get("advanced", {})

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

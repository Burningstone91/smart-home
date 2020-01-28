"""Define automations for DeCONZ lights and remote controls."""


from appdaemon.plugins.hass.hassapi import Hass


class SwitchBase(Hass):
    """Define a base class from which other classes inherit from."""

    def initialize(self) -> None:
        """Initialize."""
        self.set_namespace("hass")

        # configure entities
        self.entities = self.args["entities"]
        self.lights = self.entities["lights"]

        # get the advanced button config
        self.button_config = self.args.get("button_config", {})

    def get_light_type(self, light: str) -> str:
        """Get the DeCONZ light type of the given light."""
        if self.get_state(light, attribute="is_deconz_group"):
            return "/action"
        else:
            return "/state"

    def dim_light(self, direction: str) -> None:
        """In-/decrease brightness of light through service call to deCONZ."""
        if direction == "up":
            bri_inc = 254
        else:
            bri_inc = -254
        for light in self.lights:
            self.call_service(
                "deconz/configure",
                field=self.get_light_type(light),
                entity=light,
                data={"bri_inc": bri_inc, "transitiontime": 50},
            )

    def stop_dim_light(self) -> None:
        """Stop dimming of light through service call to deCONZ."""
        for light in self.lights:
            self.call_service(
                "deconz/configure",
                field=self.get_light_type(light),
                entity=light,
                data={"bri_inc": 0},
            )

    def action(self, button_config: dict) -> None:
        """Call the respective service based on the passed button config."""
        action_type = button_config["action_type"]
        entity = button_config["entity"]
        parameters = button_config.get("parameters", {})

        self.call_service(
            f"{action_type.replace('.','/')}", entity_id=entity, **parameters
        )


class XiaomiWXKG11LM2016(SwitchBase):
    """Define a Aqara Wirless Switch 2016 version base feature"""

    def initialize(self) -> None:
        """Configure"""
        super().initialize()
        self.switch_id = self.entities["remote_event_id"]
        self.button_map = {
            1002: "short_press",
            1004: "double_press",
            1005: "triple_press",
            1006: "quadruple_press",
        }

        # take action when button is pressed
        self.listen_event(self.button_pressed_cb, "deconz_event", id=self.switch_id)

    def button_pressed_cb(self, event_name: str, data: dict, kwargs: dict) -> None:
        """Take action when button is pressed."""
        button_code = data["event"]
        button_name = self.button_map[button_code]

        if button_name in self.button_config:
            self.action(self.button_config[button_name])
        else:
            self.log(f"Button '{button_name}' not configured. No action.")


class TradfriE1743(SwitchBase):
    """Define a Tradfri E1743 base feature"""

    def initialize(self) -> None:
        """Configure"""
        super().initialize()
        self.switch_id = self.entities["remote_event_id"]
        self.button_map = {
            1002: "short_press_on",
            1001: "long_press_on",
            1003: "long_press_on_release",
            2002: "short_press_off",
            2001: "long_press_off",
            2003: "long_press_off_release",
        }

        if "short_press_on" not in self.button_config:
            self.button_config["short_press_on"] = {
                "action_type": "light.turn_on",
                "entity": self.lights,
                "parameters": {"brightness": 255},
            }

        if "short_press_off" not in self.button_config:
            self.button_config["short_press_off"] = {
                "action_type": "light.turn_off",
                "entity": self.lights,
                "parameters": {},
            }

        # take action when button is pressed
        self.listen_event(self.button_pressed_cb, "deconz_event", id=self.switch_id)

    def button_pressed_cb(self, event_name: str, data: dict, kwargs: dict) -> None:
        """Take action when button is pressed."""
        button_code = data["event"]
        button_name = self.button_map[button_code]

        if button_name == "long_press_on":
            self.dim_light("up")
        elif button_name == "long_press_off":
            self.dim_light("down")
        elif button_name in ["long_press_on_release", "long_press_off_release"]:
            self.stop_dim_light()
        elif button_name in self.button_config:
            self.action(self.button_config[button_name])
        else:
            self.log(f"Button '{button_name}' not configured. No action.")


class TradfriE1810(SwitchBase):
    """Define a Tradfri E1810 base feature"""

    def initialize(self) -> None:
        """Configure"""
        super().initialize()
        self.switch_id = self.entities["remote_event_id"]
        self.button_map = {
            1002: "short_press_center",
            2002: "short_press_up",
            2001: "long_press_up",
            2003: "long_press_up_release",
            3002: "short_press_down",
            3001: "long_press_down",
            3003: "long_press_down_release",
            4002: "short_press_left",
            4001: "long_press_left",
            4003: "long_press_left_release",
            5002: "short_press_right",
            5001: "long_press_right",
            5003: "long_press_right_release",
        }

        if "short_press_center" not in self.button_config:
            self.button_config["short_press_center"] = {
                "action_type": "light.toggle",
                "entity": self.lights,
                "parameters": {},
            }

        # take action when button is pressed
        self.listen_event(self.button_pressed_cb, "deconz_event", id=self.switch_id)

    def button_pressed_cb(self, event_name: str, data: dict, kwargs: dict) -> None:
        """Take action when button is pressed."""
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
        else:
            self.log(f"Button '{button_name}' not configured. No action.")


class HueDimmerSwitch(SwitchBase):
    """Define a Hue Dimmer Switch base feature"""

    def initialize(self) -> None:
        """Configure"""
        super().initialize()
        self.switch_id = self.entities["remote_event_id"]
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

        if "short_press_on_release" not in self.button_config:
            self.button_config["short_press_on_release"] = {
                "action_type": "light.turn_on",
                "entity": self.lights,
                "parameters": {"brightness": 255},
            }

        if "short_press_off_release" not in self.button_config:
            self.button_config["short_press_off_release"] = {
                "action_type": "light.turn_off",
                "entity": self.lights,
                "parameters": {},
            }

        # take action when button is pressed
        self.listen_event(self.button_pressed_cb, "deconz_event", id=self.switch_id)

    def button_pressed_cb(self, event_name: str, data: dict, kwargs: dict) -> None:
        """Take action when button is pressed."""
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
        else:
            self.log(f"Button '{button_name}' not configured. No action.")


class KNXSwitch(SwitchBase):
    """Define a KNX Switch base feature"""

    def initialize(self) -> None:
        """Configure"""
        super().initialize()
        self.on_off_address = self.args["knx_address"]["on_off"]
        self.dimming_address = self.args["knx_address"]["dimming"]

        if "short_press_on" not in self.button_config:
            self.button_config["short_press_on"] = {
                "action_type": "light.turn_on",
                "entity": self.lights,
                "parameters": {"brightness": 255},
            }

        if "short_press_off" not in self.button_config:
            self.button_config["short_press_off"] = {
                "action_type": "light.turn_off",
                "entity": self.lights,
                "parameters": {},
            }

        # take action when button is pressed
        self.listen_event(self.button_pressed_cb, "knx_event")

    def button_pressed_cb(self, event_name: str, data: dict, kwargs: dict) -> None:
        """Take action when button is pressed."""
        button_name = self.get_button_name(data)
        self.log(button_name)

        if button_name == "long_press_on":
            self.dim_light("up")
        elif button_name == "long_press_off":
            self.dim_light("down")
        elif button_name == "long_press_release":
            self.stop_dim_light()
        elif button_name in self.button_config:
            self.action(self.button_config[button_name])
        else:
            self.log(f"Button '{button_name}' not configured. No action.")

    def get_button_name(self, event_data: dict) -> str:
        """Get the name of the button pressed from the event data."""
        address = event_data["address"]
        data = event_data["data"]

        if address in [self.on_off_address, self.dimming_address]:
            if address == self.on_off_address and data == [1]:
                return "short_press_on"
            elif address == self.on_off_address and data == [0]:
                return "short_press_off"
            elif address == self.dimming_address and data == [9]:
                return "long_press_on"
            elif address == self.dimming_address and data == [0]:
                return "long_press_release"
            elif address == self.dimming_address and data == [1]:
                return "long_press_off"
        else:
            return f"Address {address}, Data {data}"

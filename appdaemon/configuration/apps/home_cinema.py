"""Define automations for the home cinema"""

from typing import Union

import voluptuous as vol

import voluptuous_helper as vol_help
from appbase import AppBase, APP_SCHEMA
from constants import CONF_ENTITIES, CONF_PROPERTIES, ON, PERSON
from house_config import PERSONS


##############################################################################
# Apps to control the home cinema
# RemoteAutomation:
#   - methods/variables for the use with the harmony remote
#   - remote_is_off: bool True if remote is off
#   - current_device_id: id of the device associated with current activitiy
#   - current_activity_name: name of the current activity
#   - send_command: first arg is command to send, second arg is optional
#                   for the device id, if it is not given the device id of the
#                   device for the current activity will be taken
#   - args:
#     entities:
#       harmony_remote: entity id of the harmony remote
#       activities: dict with device id (number) for each activity
#
# SceneLights:
#   - changes the light in the livingroom when the scene changes
#   - args:
#     entities:
#       lights: lights to control
#     properties:
#       transition_on: transition time from off to on, default 2 seconds
#       transition_off: transition time from on to off, default 60 seconds
#       scene_color: colors for different scenes
#         fernsehen: blue
#       scene_brightness: brightness for different scenes, in %
#         fernsehen: 50
#
# BrightenLightOnPause
#   - requires dependency to scene_lights_app
#   - when home cinema is paused (detected through button press on emulated
#     roku) the lights turn on white and bright
#   - when home cinema is resumed the lights turn back according to current
#     activity and the config in the scene_lights_app
#
# ****************************Under Construction******************************
# PhoneCall
#   - requires dependency to remote_app
#   - when a phone call is ongoing a pause command will be sent to home cinema
#   - when phone call ends a play command will be sent to the home cinema
#   - args:
#     properties:
#       roku_id: entity if of emulated roku id which is needed to workaround
#                the fact that harmony commands sent cant be detected
##############################################################################


CONF_HARMONY_REMOTE = 'harmony_remote'
CONF_ACTIVITIES = 'activities'
CONF_DEVICE = 'device'
CURRENT_ACTIVITY = 'current_activity'

CONF_LIGHTS = 'lights'
CONF_TRANSITION_ON = 'transition_on'
CONF_TRANSITION_OFF = 'transition_off'
CONF_SCENE_COLOR = 'scene_color'
CONF_SCENE_BRIGHTNESS = 'scene_brightness'
POWER_OFF = 'poweroff'

HOME = 'Home'
PLAY = 'Play'
PAUSE = 'Pause'
KEY = 'key'
ROKU_COMMAND = 'roku_command'

CONF_DEVICE_ID = 'device_id'
PHONE_CALL_BOOL = 'phone_call_bool'


class RemoteAutomation(AppBase):
    """Define a base feature for remote automations."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(CONF_HARMONY_REMOTE): vol_help.entity_id,
        }, extra=vol.ALLOW_EXTRA),
        CONF_PROPERTIES: vol.Schema({
            vol.Required(CONF_ACTIVITIES): dict,
        }, extra=vol.ALLOW_EXTRA)
    })

    def configure(self) -> None:
        """Configure."""
        self.remote = self.entities[CONF_HARMONY_REMOTE]
        self.activities = self.properties[CONF_ACTIVITIES]

    @property
    def current_device_id(self) -> Union[int, None]:
        """Get device id of current activity."""
        try:
            return self.activities[
                self.current_activity_name.replace(' ', '_').lower()
            ]
        except KeyError:
            return None

    @property
    def current_activity_name(self) -> Union[str, None]:
        """Get the name of the current activity."""
        return self.get_state(self.remote, attribute=CURRENT_ACTIVITY)

    @property
    def remote_is_off(self) -> bool:
        """Return the power state of the remote control."""
        return self.current_device_id == -1

    def send_command(self, command: str, **kwargs: dict) -> None:
        """Send a command to the remote."""
        device_id = kwargs.get(CONF_DEVICE, self.current_device_id)
        self.log(device_id)

        self.call_service(
            'remote/send_command',
            entity_id=self.remote,
            device=device_id,
            command=command)


class SceneLights(AppBase):
    """Define a feature to change light based on the current activity."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(CONF_LIGHTS): vol_help.entity_id_list,
        }, extra=vol.ALLOW_EXTRA),
        CONF_PROPERTIES: vol.Schema({
            vol.Required(CONF_SCENE_COLOR): str,
            vol.Required(CONF_SCENE_BRIGHTNESS): str,
            vol.Optional(CONF_SCENE_COLOR): dict,
            vol.Optional(CONF_SCENE_BRIGHTNESS): dict,
        }, extra=vol.ALLOW_EXTRA)
    })

    def configure(self) -> None:
        """Configure."""
        self.lights = self.entities[CONF_LIGHTS].split(',')
        self.scene_color_map = self.properties[CONF_SCENE_COLOR]
        self.scene_brightness_map = self.properties[CONF_SCENE_BRIGHTNESS]
        self.transition_on = self.properties.get(CONF_TRANSITION_ON, 2)
        self.transition_off = self.properties.get(CONF_TRANSITION_OFF, 60)

        self.listen_state(
            self.scene_changed,
            self.remote_app.remote,
            attribute=CURRENT_ACTIVITY,
            constrain_app_enabled=1)

    def scene_changed(self, entity: Union[str, dict], attribute: str,
                      old: str, new: str, kwargs: dict) -> None:
        """Change the light when the acitivity changed."""
        if self.scene_name(new) == POWER_OFF:
            for light in self.lights:
                self.turn_off(light, transition=self.transition_off)
        else:
            for light in self.lights:
                self.turn_on(
                    light,
                    brightness=self.brightness(new),
                    color_name=self.light_color(new),
                    transition=self.transition_on)

    def brightness(self, scene: str) -> float:
        """Get the specified brightness for the given scene."""
        brightness_pct = self.scene_brightness_map.get(self.scene_name(scene), 75)
        return 255 / 100 * int(brightness_pct)

    def light_color(self, scene: str) -> str:
        """Get the specified light color for the given scene."""
        return self.scene_color_map.get(self.scene_name(scene), 'white')

    @staticmethod
    def scene_name(scene: str) -> str:
        """Convert the scene name to the correct format."""
        return scene.replace(' ', '_').lower()

    def brighten_lights(self):
        """Brighten lights."""
        for light in self.lights:
            self.turn_on(
                light,
                brightness=200,
                color_name='white',
                transition=2)

    def dim_lights(self):
        """Dim lights."""
        current_activity = self.remote_app.current_activity_name

        for light in self.lights:
            self.turn_on(
                light,
                brightness=self.brightness(current_activity),
                color_name=self.light_color(current_activity),
                transition=2)


class PhoneCall(AppBase):
    """Define a feature to pause current activity on phone call."""

    def configure(self) -> None:
        """Configure."""
        for person, attribute in PERSONS.items():
            self.listen_state(
                self.phone_call_changed,
                attribute[PHONE_CALL_BOOL],
                person=person)

    def phone_call_changed(self, entity: Union[str, dict], attribute: str,
                           old: str, new: str, kwargs: dict) -> None:
        """Pause/play and brighten/dim when phone call is ongoing/ended."""
        if (not self.remote_app.remote_is_off and
                kwargs[PERSON] in self.presence_app.persons_home):
            if new == ON:
                self.remote_app.send_command(PAUSE)
                self.scene_lights_app.brighten_lights()
            else:
                self.remote_app.send_command(PLAY)
                self.scene_lights_app.dim_lights()


class BrightenLightOnPause(AppBase):
    """Define a feature to dim/brighten light on play/pause."""

    def configure(self) -> None:
        """Configure."""
        self.listen_event(self.button_pressed, ROKU_COMMAND)

    def button_pressed(self, event_name: str,
                       data: dict, kwargs: dict) -> None:
        """Dim/brighten on button press."""
        key = data[KEY]
        self.log(key)
        if key == HOME:  # Home = Pause
            self.scene_lights_app.brighten_lights()
        elif key == PLAY:
            self.scene_lights_app.dim_lights()

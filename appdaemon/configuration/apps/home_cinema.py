from typing import Union

from appbase import AppBase
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


class RemoteAutomation(AppBase):
    def initialize(self) -> None:
        super().initialize()
        self.remote = self.entities['harmony_remote']
        self.activities = self.properties['activities']

    @property
    def current_device_id(self) -> Union[int, None]:
        activity_name = self.get_state(self.remote,
                                       attribute='current_activity')
        try:
            return self.activities[activity_name.replace(' ', '_').lower()]
        except KeyError:
            return None

    @property
    def current_activity_name(self) -> Union[str, None]:
        return self.get_state(self.remote, attribute='current_activity')

    @property
    def remote_is_off(self) -> bool:
        return self.current_device_id == -1

    def send_command(self, command: str, **kwargs: dict) -> None:
        if 'device' in kwargs:
            device_id = kwargs['device']
        else:
            device_id = self.current_device_id
        self.log(device_id)

        self.call_service('remote/send_command',
                          entity_id=self.remote,
                          device=device_id,
                          command=command)


class SceneLights(AppBase):
    def initialize(self) -> None:
        super().initialize()

        self.lights = self.entities['lights'].split(',')
        self.transition_on = self.properties.get('transition_on', 2)
        self.transition_off = self.properties.get('transition_off', 60)
        self.scene_color_map = self.properties['scene_color']
        self.scene_brightness_map = self.properties['scene_brightness']

        # change color on scene change
        self.listen_state(self.scene_changed,
                          self.remote_app.remote,
                          attribute='current_activity',
                          constrain_app_enabled=1)

    def scene_changed(self, entity: Union[str, dict], attribute: str,
                      old: str, new: str, kwargs: dict) -> None:
        if self.scene_name(new) == 'poweroff':
            for light in self.lights:
                self.turn_off(light, transition=self.transition_off)
        else:
            for light in self.lights:
                self.turn_on(light,
                             brightness=self.brightness(new),
                             color_name=self.light_color(new),
                             transition=self.transition_on)

    def brightness(self, scene: str) -> float:
        brightness_pct = self.scene_brightness_map.get(self.scene_name(scene), 75)
        return 255 / 100 * int(brightness_pct)

    def light_color(self, scene: str) -> str:
        return self.scene_color_map.get(self.scene_name(scene), 'white')

    def scene_name(self, scene: str) -> str:
        return scene.replace(' ', '_').lower()

    def brighten_on_pause(self):
        for light in self.lights:
            self.turn_on(light,
                         brightness=200,
                         color_name='white',
                         transition=2)

    def dim_on_play(self):
        current_activity = self.remote_app.current_activity_name

        for light in self.lights:
            self.turn_on(light,
                         brightness=self.brightness(current_activity),
                         color_name=self.light_color(current_activity),
                         transition=2)


class PhoneCall(AppBase):
    def initialize(self) -> None:
        super().initialize()
        self.device_id = self.properties['device_id']
        for person, attribute in PERSONS.items():
            self.listen_state(self.phone_call_changed,
                              attribute['phone_call_bool'],
                              person=person)

    def phone_call_changed(self, entity: Union[str, dict], attribute: str,
                           old: str, new: str, kwargs: dict) -> None:
        if (not self.remote_app.remote_is_off and
                kwargs['person'] in self.presence_app.persons_home):
            if new == 'on':
                self.remote_app.send_command('Pause')
                self.scene_lights_app.brighten_on_pause()
            else:
                self.remote_app.send_command('Play')
                self.scene_lights_app.dim_on_play()


class BrightenLightOnPause(AppBase):
    def initialize(self) -> None:
        super().initialize()

        # brighten/dim when pause/play is pressed
        self.listen_event(self.button_pressed, 'roku_command')

    def button_pressed(self, event_name: str, data: dict, kwargs: dict) -> None:
        key = data['key']
        self.log(key)
        if key == 'Home':
            self.scene_lights_app.brighten_on_pause()
        elif key == 'Play':
            self.scene_lights_app.dim_on_play()


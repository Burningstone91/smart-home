from typing import Union

from appbase import AppBase

LIGHT_TIMER = 'light_timer'


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
#   no_action: devices which will lead to no action on motion if they are on
#   lights: light entities for each state of day
#     morning:
#     day:
#     night:
# properties:
#   lux_threshold: value above which light will not turn on, default 100 lux
#   timer_sec: seconds until light turns off when no motion, default 300 sec
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


class MotionLightAutomation(AppBase):

    def initialize(self) -> None:
        super().initialize()
        self.delay = self.properties.get('timer_sec', 300)
        self.no_action_entities = self.entities.get('no_action', '').split(',')

        self.day_state_map = self.properties.get('day_state_time', {})
        self.brightness_map = self.properties.get('brightness_level', {})
        self.color_map = self.properties.get('light_color', {})
        self.lights_map = self.entities['lights']

        # creates a list of a split of each element in self.lights_map
        self.all_lights = []
        for lights in self.lights_map.values():
            for light in lights.split(','):
                if light not in self.all_lights:
                    self.all_lights.append(light)

        self.room_name = self.all_lights[0].split('.')[1].split('_')[-1].capitalize()

        if 'motion_sensor' in self.entities:
            # take action when motion is detected
            self.listen_state(self.motion,
                              self.entities['motion_sensor'],
                              constrain_app_enabled=1)
        else:
            self.log("Kein Bewegungssensor konfiguriert, keine Aktion!")

    def motion(self, entity: Union[str, dict], attribute: str,
               old: str, new: str, kwargs: dict) -> None:
        if new == 'on':
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
        for entity in self.lights:
            self.turn_on(entity,
                         brightness=self.brightness,
                         color_name=self.light_color)

        self.log(f"Das Licht im {self.room_name} "
                 f"wurde durch Bewegung eingeschaltet. "
                 f"Die Helligkeit ist {round(self.brightness * 100 / 255)}% "
                 f"und die Farbe ist {self.light_color}.")

    def turn_light_off(self, *args: list) -> None:
        if not self.no_action_entities_on:
            for entity in self.lights_on:
                self.turn_off(entity)
            self.log(f"Das Licht im {self.room_name} "
                     f"wurde durch den Timer ausgeschaltet.")

    def turn_off_delayed(self) -> None:
        if LIGHT_TIMER in self.handles:
            self.cancel_timer(self.handles[LIGHT_TIMER])
            self.handles.pop(LIGHT_TIMER)
        self.handles[LIGHT_TIMER] = self.run_in(self.turn_light_off,
                                                self.delay)
        self.log(f"Ein Timer von {round(self.delay / 60)} Minuten "
                 f"wurde im {self.room_name} eingeschaltet.")

    @property
    def no_action_entities_on(self) -> list:
        on_states = ['on', 'home']
        return [entity for entity in self.no_action_entities
                if self.get_state(entity) in on_states]

    @property
    def lights_on(self) -> list:
        return [entity for entity in self.all_lights
                if self.get_state(entity) == 'on']

    @property
    def lux_high(self) -> bool:
        if 'lux_sensor' in self.entities:
            lux_sensor = self.entities['lux_sensor']
            lux_threshold = self.properties.get('lux_threshold', 100)
            return float(self.get_state(lux_sensor)) > float(lux_threshold)
        return False

    @property
    def day_state(self) -> str:
        if self.now_is_between(self.day_state_map['morning'],
                               self.day_state_map['day']):
            return 'morning'
        elif self.now_is_between(self.day_state_map['day'],
                                 self.day_state_map['night']):
            return 'day'
        else:
            return 'night'

    @property
    def lights(self) -> list:
        return [entity for entity in self.lights_map[self.day_state].split(',')]

    @property
    def brightness(self) -> float:
        brightness_level = self.brightness_map.get(self.day_state, 75)
        return 255 / 100 * int(brightness_level)

    @property
    def light_color(self) -> str:
        return self.color_map.get(self.day_state, 'white')

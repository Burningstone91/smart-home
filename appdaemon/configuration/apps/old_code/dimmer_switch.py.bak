from appbase import AppBase


##############################################################################
# DimmerSwitch
#   - App to control hue dimmer switches, config:
#   - config:
#       On Button: Turn lights on full brightness
#       Brightness+ Button: Increase brightness by 10%, turn on if light is off
#       Brightness- Button: Decrease brightness by 10%, turn light off if <=0
#       Off Button: Turn lights off
#   - args:
#     entities:
#       lights: entity id of lights to control, comma separated
#       dimmer_switch: entity id of dimmer switch
##############################################################################


class DimmerSwitch(AppBase):
    def initialize(self) -> None:
        super().initialize()
        self.lights = self.entities.get('lights', '').split(',')
        self.room_name = self.lights[0].split('.')[1].split('_')[-1].capitalize()

        if 'dimmer_switch' in self.entities:
            # take action when button is pressed on dimmer switch
            self.listen_event(self.button_pressed,
                              "deconz_event",
                              id=self.entities['dimmer_switch'])

    def button_pressed(self, event_name: str, data: dict,
                       kwargs: dict) -> None:
        button_event = data['event']
        # 10xx: on, 20xx: brighten, 30xx: dim, 40xx: off
        # xx03: long press release, xx02: short press release

        if (button_event == 1002) or (button_event == 1003):
            for entity in self.lights:
                self.turn_on(entity, brightness=255, color_name='white')
            self.log(f"Das Licht im {self.room_name} "
                     f"wurde durch den Lichtschalter eingeschaltet.")

        if (button_event == 2002) or (button_event == 2003):
            for entity in self.lights:
                brightness = self.get_state(entity, attribute='brightness') or 0
                new_brightness = brightness + 25
                if new_brightness > 255:
                    new_brightness = 255
                self.turn_on(entity, brightness=new_brightness)
            self.log(f"Das Licht im {self.room_name} "
                     f"wurde durch den Lichtschalter aufgehellt.")

        if (button_event == 3002) or (button_event == 3003):
            for entity in self.lights:
                brightness = self.get_state(entity, attribute='brightness') or 0
                new_brightness = brightness - 25
                if new_brightness <= 0:
                    self.turn_off(entity)
                else:
                    self.turn_on(entity, brightness=new_brightness)
            self.log(f"Das Licht im {self.room_name} "
                     f"wurde durch den Lichtschalter gedimmt.")

        if (button_event == 4002) or (button_event == 4003):
            for entity in self.lights:
                self.turn_off(entity)
            self.log(f"Das Licht im {self.room_name} "
                     f"wurde durch den Lichtschalter ausgeschaltet.")

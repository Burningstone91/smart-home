import datetime
from typing import Union

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
#       window_sensors: comma separated list
#       humidity_sensors: comma separated list
#       temperature_sensors: comma separated list
#       average_temperature_sensor:
#       thresholds:
#       humidity_room:
#       temperature_average:
##############################################################################


class ClimateAutomation(AppBase):
    def initialize(self):
        super().initialize()
        self.window_sensors = self.entities.get('window_sensors', '').split(',')

        self.humidity_sensors = self.entities.get('humidity_sensors', '').split(',')
        self.humidity_room_threshold = float(self.args['thresholds']['humidity_room'])

    @property
    def window_is_open(self) -> bool:
        return not(not self.which_window_open)

    @property
    def which_window_open(self) -> list:
        return [
            window for window in self.window_sensors
            if self.get_state(window) == 'offen'
        ]

    @property
    def humidity_in_room_high(self) -> bool:
        return not(not self.which_room_high_humidity)

    @property
    def which_room_high_humidity(self) -> list:
        return [
            self.room_name(room) for room in self.humidity_sensors
            if float(self.get_state(room)) > self.humidity_room_threshold
        ]

    def room_name(self, room: str) -> str:
        return room.split('.')[1].split('_', 1)[-1].capitalize()


class NotifyOnHighHumidity(AppBase):
    def initialize(self):
        super().initialize()

        # check every 30 min if humidity threshold is reached, if yes -> send notification
        self.run_every(self.send_notification,
                       datetime.datetime.now(),
                       30 * 60,
                       constrain_app_enabled=1)

    def send_notification(self, kwargs: dict) -> None:
        if self.climate_app.humidity_in_room_high:
            self.notification_app.notify(
                kind='single',
                level='home',
                title="Hohe Luftfeuchtigkeit!",
                message=f"Im {', '.join(self.climate_app.which_room_high_humidity)} "
                        f"herrscht eine hohe Luftfeuchtigkeit",
                targets=self.notifications['targets'])


class NotifyOnWindowOpen(AppBase):
    def initialize(self):
        super().initialize()
        self.notification_lights = self.entities['notification_lights']
        self.notification_sent = False

        for entity in self.climate_app.window_sensors:
            # send notification if a window is open for more than 10 minutes
            self.listen_state(self.send_notification,
                              entity,
                              new='offen',
                              duration=10 * 60,
                              constrain_app_enabled=1)

            # turn off notification bulb if all windows are closed
            self.listen_state(self.turn_off_notification_bulb,
                              entity,
                              new='geschlossen',
                              constrain_app_enabled=1)

    def send_notification(self, entity: Union[str, dict], attribute: str,
                          old: str, new: str, kwargs: dict) -> None:
        if not self.notification_sent:
            self.notification_app.notify(
                kind='single',
                level='emergency',
                title="Fenster offen!",
                message=f"Das Fenster im "
                        f"{entity.split('.')[1].split('_')[-1].capitalize()} "
                        f"ist länger als 10 Minuten offen.",
                targets=self.notifications['targets'])

            self.notification_sent = True

        #self.notification_app.notify_with_light(self.notification_lights)

    def turn_off_notification_bulb(self, entity: Union[str, dict],
                                   attribute: str, old: str, new: str,
                                   kwargs: dict) -> None:
        if not self.climate_app.window_is_open and self.notification_sent:
            self.log('Alle Fenster wurden geschlossen')
            self.notification_sent = False
            ########### problem somewhere in below code ##############333
            #self.notification_app.notify_with_light(self.notification_lights,
                                                     #cancel=True)

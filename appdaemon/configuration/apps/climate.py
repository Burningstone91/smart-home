"""Define automations for climate."""

import datetime
from typing import Union

import voluptuous as vol

import voloptuous_helper as vol_help
from appbase import AppBase, APP_SCHEMA
from constants import (
    CONF_ENTITIES, CONF_NOTIFICATIONS, CONF_PROPERTIES,
    CONF_TARGETS, EMERGENCY, HOME, OPEN, SINGLE
)


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


CONF_WINDOW_SENSORS = 'window_sensors'
CONF_HUMIDITY_SENSORS = 'humidity_sensors'
CONF_THRESHOLDS = 'thresholds'
CONF_HUMIDITY_ROOM = 'humidity_room'

CONF_CHECK_INTERVAL = 'check_interval'

CONF_WINDOW_OPEN_THRESHOLD = 'window_open_threshold'


class ClimateAutomation(AppBase):
    """Define a base for climate automations."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(CONF_HUMIDITY_SENSORS): vol_help.entity_id_list,
            vol.Required(CONF_WINDOW_SENSORS): vol_help.entity_id_list,
        }, extra=vol.ALLOW_EXTRA),
        CONF_PROPERTIES: vol.Schema({
            vol.Required(CONF_HUMIDITY_ROOM): int,
        }, extra=vol.ALLOW_EXTRA)
    })

    @property
    def window_is_open(self) -> bool:
        return not(not self.which_window_open)

    @property
    def which_window_open(self) -> list:
        return [
            window for window in self.entities[CONF_WINDOW_SENSORS].split(',')
            if self.get_state(window) == OPEN
        ]

    @property
    def humidity_in_room_high(self) -> bool:
        return not(not self.which_room_high_humidity)

    @property
    def which_room_high_humidity(self) -> list:
        return [
            self.room_name(room) for room in self.entities[CONF_HUMIDITY_SENSORS].split(',')
            if float(self.get_state(room)) > float(self.properties[CONF_HUMIDITY_ROOM])
        ]

    def room_name(self, room: str) -> str:
        return room.split('.')[1].split('_', 1)[-1].capitalize()


class NotifyOnHighHumidity(AppBase):
    """Define a feature to notify on high humidity."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_PROPERTIES: vol.Schema({
            vol.Required(CONF_CHECK_INTERVAL): int,
        }, extra=vol.ALLOW_EXTRA),
        CONF_NOTIFICATIONS: vol.Schema({
            vol.Required(CONF_TARGETS): str,
        })
    })

    def configure(self):
        """Configure."""
        self.run_every(
            self.send_notification,
            datetime.datetime.now(),
            self.properties[CONF_CHECK_INTERVAL] * 60,
            constrain_app_enabled=1)

    def send_notification(self, kwargs: dict) -> None:
        """Send notification on high humidity."""
        if self.climate_app.humidity_in_room_high:
            self.notification_app.notify(
                kind=SINGLE,
                level=HOME,
                title="Hohe Luftfeuchtigkeit!",
                message=f"Im {', '.join(self.climate_app.which_room_high_humidity)} "
                        f"herrscht eine hohe Luftfeuchtigkeit",
                targets=self.notifications[CONF_TARGETS])


class NotifyOnWindowOpen(AppBase):
    """Define a feature to notify on a window open longer than threshold."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(CONF_WINDOW_SENSORS): vol_help.entity_id_list,
        }, extra=vol.ALLOW_EXTRA),
        CONF_PROPERTIES: vol.Schema({
            vol.Required(CONF_WINDOW_OPEN_THRESHOLD): int,
        }, extra=vol.ALLOW_EXTRA),
        CONF_NOTIFICATIONS: vol.Schema({
            vol.Required(CONF_TARGETS): str,
        })
    })

    def configure(self):
        """Configure."""
        self.window_open_threshold = self.properties[CONF_WINDOW_OPEN_THRESHOLD]

        for entity in self.entities[CONF_WINDOW_SENSORS].split(','):
            self.listen_state(
                self.send_notification,
                entity,
                new=OPEN,
                duration=self .window_open_threshold * 60,
                constrain_app_enabled=1)

    def send_notification(self, entity: Union[str, dict], attribute: str,
                          old: str, new: str, kwargs: dict) -> None:
        """Send notification if a window is open longer than threshold."""
        self.notification_app.notify(
            kind=SINGLE,
            level=EMERGENCY,
            title="Fenster offen!",
            message=f"Das Fenster im "
                    f"{entity.split('.')[1].split('_')[-1].capitalize()} "
                    f"ist länger als {self.window_open_threshold} "
                    f"Minuten offen.",
            targets=self.notifications['targets'])

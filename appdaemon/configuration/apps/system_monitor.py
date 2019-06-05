"""Define automations for system monitoring."""

import os
from typing import Union

import voluptuous as vol

import voluptuous_helper as vol_help
from appbase import AppBase, APP_SCHEMA
from constants import (
    CONF_ENTITIES, CONF_NOTIFICATIONS, CONF_PROPERTIES,
    CONF_TARGETS, OFF, NOT_HOME
)
from house_config import PERSONS


CONF_TRACKING_DEVICES = 'tracking_devices'

SWITCH = 'switch'
DEVICE_TRACKER = 'device_tracker'
SENSOR = 'sensor'
BINARY_SENSOR = 'binary_sensor'
ZWAVE = 'zwave'
DEVICE_TYPES = [SWITCH, DEVICE_TRACKER, SENSOR, BINARY_SENSOR]

UNAVAILABLE = 'unavailable'
UNKNOWN = 'unknown'
UNAVAILABLE_STATES = [UNAVAILABLE, UNKNOWN]
OFF_STATES = [OFF, NOT_HOME]

CRITICAL_LOG_STATES = ['WARNING', 'ERROR', 'CRITICAL']

CONF_BATTERY_LOW_THRESHOLD = 'battery_low_threshold'

CONF_AVAILABLE = 'available'


class NotifyOnDeviceOffline(AppBase):
    """Define an automation to notify on device going offline."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(CONF_TRACKING_DEVICES): vol.Schema([
                vol.Optional(vol_help.entity_id),
            ]),
        }, extra=vol.ALLOW_EXTRA),
        CONF_NOTIFICATIONS: vol.Schema({
            vol.Required(CONF_TARGETS): vol.In(PERSONS.keys()),
        }, extra=vol.ALLOW_EXTRA),
    })

    def configure(self) -> None:
        """Configure."""
        for entity in self.entities[CONF_TRACKING_DEVICES]:
            device_type = entity.split('.')[0]
            if device_type == SWITCH:
                self.listen_state(
                    self.device_offline,
                    entity,
                    new=OFF,
                    duration=60 * 5,
                    constrain_app_enabled=1)
            elif device_type == DEVICE_TRACKER:
                self.listen_state(
                    self.device_offline,
                    entity,
                    new=NOT_HOME,
                    duration=60 * 5,
                    constrain_app_enabled=1)
            elif device_type == ZWAVE:
                self.listen_state(
                    self.device_offline,
                    entity,
                    new=UNKNOWN,
                    duration=60 * 5,
                    constrain_app_enabled=1)
                self.listen_state(
                    self.device_offline,
                    entity,
                    new=UNAVAILABLE,
                    duration=60 * 5,
                    constrain_app_enabled=1)
            elif device_type in (SENSOR, BINARY_SENSOR):
                self.listen_state(
                    self.device_offline,
                    entity,
                    new=UNAVAILABLE,
                    duration=60 * 5,
                    constrain_app_enabled=1)

    def device_offline(self, entity: Union[str, dict], attribute: str,
                       old: str, new: str, kwargs: dict) -> None:
        """Send notification when device is offline longer than 5 minutes."""
        self.notification_app.notify(
            kind='single',
            level='emergency',
            title="Gerät offline!",
            message=f"Das folgende Gerät ist offline {entity}",
            targets=self.notifications['targets'])


class NotifyOnAppdaemonLogError(AppBase):
    """Define an automation to notify on error in Appdaemon log."""

    def configure(self) -> None:
        """Configure."""
        self.listen_log(self.new_log)

    def new_log(self, name: str, timestamp: str, level: str, message: str) -> None:
        """Send notification when Appdaemon log shows an error."""
        if level in CRITICAL_LOG_STATES:
            self.notification_app.notify(
                kind='single',
                level='emergency',
                title="Appdaemon Fehler in Log!",
                message=(f"Die App {name} hat den folgenden Fehler "
                         f"um {timestamp} ausgelöst: {message}."),
                targets=self.notifications['targets'])


class NotifyOnLowBattery(AppBase):
    """Define an automation to notify on low battery."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(CONF_TRACKING_DEVICES): vol.Schema([
                vol.Optional(vol_help.entity_id),
            ]),
        }, extra=vol.ALLOW_EXTRA),
        CONF_NOTIFICATIONS: vol.Schema({
            vol.Required(CONF_TARGETS): vol.In(PERSONS.keys()),
        }, extra=vol.ALLOW_EXTRA),
        CONF_PROPERTIES: vol.Schema({
            vol.Optional(CONF_BATTERY_LOW_THRESHOLD): int,
        }, extra=vol.ALLOW_EXTRA)
    })

    def configure(self) -> None:
        """Configure."""
        for entity in self.entities[CONF_TRACKING_DEVICES]:
            self.listen_state(
                self.battery_low,
                entity,
                constrain_app_enabled=1)

    def battery_low(self, entity: Union[str, dict], attribute: str,
                    old: str, new: str, kwargs: dict) -> None:
        """Send notification when battery is below threshold."""
        if float(new) < float(self.properties[CONF_BATTERY_LOW_THRESHOLD]):
            self.notification_app.notify(
                kind='home',
                level='repeat',
                title="Batterie niedrig!",
                message=f"Die Batterie für {entity} ist niedrig.",
                targets=self.notifications['targets'])


class CheckAppDaemonVersionInstalled(AppBase):
    """Define a feature to daily update installed version sensor for appdaemon."""

    def configure(self) -> None:
        """Configure"""
        self.run_daily(self.set_sensor, self.parse_time("01:00:00"))

    def set_sensor(self, kwargs: dict) -> None:
        """Set the sensor to the current installed version."""
        subdirs = os.listdir("/usr/local/lib/python3.6/site-packages")
        for subdirname in subdirs:
            if "appdaemon" in subdirname.lower():
                if "info" in subdirname.lower():
                    version = subdirname.split("-")[1][:-5]
                    self.set_state("sensor.appdaemon_installed",
                                   state=version)


class NotifyOnNewVersion(AppBase):
    """Define an automation to notify when a new version is available."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(CONF_AVAILABLE): vol.Schema([
                vol.Optional(vol_help.entity_id),
            ]),
        }, extra=vol.ALLOW_EXTRA),
        CONF_NOTIFICATIONS: vol.Schema({
            vol.Required(CONF_TARGETS): vol.In(PERSONS.keys()),
        }, extra=vol.ALLOW_EXTRA),
    })

    def configure(self) -> None:
        """Configure."""
        for entity in self.entities[CONF_AVAILABLE]:
            self.listen_state(
                self.version_changed,
                entity,
                constrain_app_enabled=1)

    def version_changed(self, entity: Union[str, dict], attribute: str,
                        old: str, new: str, kwargs: dict) -> None:
        """Send notification when new version is available."""
        self.log(old)
        self.log(new)
        if new != old:
            app = entity.split('.')[1].split('_')[0]
            self.notification_app.notify(
                kind='home',
                level='single',
                title=f"Neue Version für {app}!",
                message=f"Die Version {self.get_state(entity)} "
                        f"für {app} ist verfügbar.",
                targets=self.notifications['targets'])

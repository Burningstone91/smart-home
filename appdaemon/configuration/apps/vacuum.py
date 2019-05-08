"""Define automations for the vacuum cleaner."""

from enum import Enum
from typing import Union

import voluptuous as vol

import voloptuous_helper as vol_help
from appbase import AppBase, APP_SCHEMA
from constants import (
    CONF_ENTITIES, CONF_INTERVAL, CONF_NOTIFICATIONS,
    CONF_PROPERTIES, CONF_TARGETS
)
from house_config import HOUSE, MODES, PERSONS


##############################################################################
# App to control vacuum cleaner, cleans at chosen time
# stops cleaning when someone comes home, notifies when bin is full
# dependencies: presence_app, notification_app
# args:
#
# entities:
#   - vacuum: entity id of vacuum cleaner
# notifications:
#   targets:
#   interval:
# properties:
#   cleaning_time: time to start cleaning, default 11:00:00
##############################################################################


BIN_FULL = 'bin_full'
CONF_CLEANING_TIME = 'cleaning_time'
CLEANING_MODE = 'cleaning_mode'
VACUUM = 'vacuum'
STATUS = 'status'
PRESENCE_STATE = 'presence_state'
CONF_REMINDER_TIME = 'reminder_time'


class VacuumAutomation(AppBase):
    """Define a feature for scheduled cleaning cycle including
       cancellation when someone arrives home."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(VACUUM): vol_help.entity_id,
        }, extra=vol.ALLOW_EXTRA),
        CONF_PROPERTIES: vol.Schema({
            vol.Optional(CONF_CLEANING_TIME): str,
        }, extra=vol.ALLOW_EXTRA),
        CONF_NOTIFICATIONS: vol.Schema({
            vol.Required(CONF_TARGETS): vol.In(PERSONS.keys()),
        }, extra=vol.ALLOW_EXTRA),
    })

    class VacuumState(Enum):
        """Define an enum for vacuum states."""

        charging = 'Charging'
        running = 'Running'
        returning = 'User Docking'
        stuck = 'Stuck'

    def configure(self) -> None:
        """Configure."""
        self.started_by_app = False
        self.vacuum = self.entities[VACUUM]
        cleaning_time = self.parse_time(
            self.properties.get(CONF_CLEANING_TIME, '11:00:00'))

        # scheduled clean cycle
        self.run_daily(self.start_cleaning,
                       cleaning_time,
                       constrain_app_enabled=1)

        # cycle finished
        self.listen_state(self.cleaning_finished,
                          self.vacuum,
                          attribute=STATUS,
                          old=self.VacuumState.returning.value,
                          new=self.VacuumState.charging.value)

        # cancel cycle if someone arrives home
        self.listen_state(self.cancel_cleaning, HOUSE[PRESENCE_STATE])

        # turn on/off cleaning mode when cleaning/finished cleaning
        self.listen_state(self.set_cleaning_mode_input_boolean,
                          self.vacuum,
                          attribute=STATUS)

    @property
    def vacuum_state(self) -> VacuumState:
        """Return the current state of the vacuum cleaner."""
        return self.get_state(self.vacuum, attribute='status')

    def start_cleaning(self, kwargs: dict) -> None:
        """Start the scheduled cleaning cycle."""
        self.call_service('vacuum/start_pause', entity_id=self.vacuum)
        self.started_by_app = True
        self.log("Pedro startet die Reinigung!")

    def cleaning_finished(self, entity: Union[str, dict], attribute: str, 
                          old: str, new: str, kwargs: dict) -> None:
        """Deactive input boolean when cleaning cycle finished."""
        self.started_by_app = False
        self.log("Pedro hat die Reinigung beendet")

    def cancel_cleaning(self, entity: Union[str, dict], attribute: str,
                        old: str, new: str, kwargs: dict) -> None:
        """Cancel the cleaning cycle when someone arrives home."""
        if ((not self.presence_app.noone_home and self.started_by_app) and 
                self.vacuum_state == self.VacuumState.running.value):
            self.call_service('vacuum/return_to_base', entity_id=self.vacuum)
            self.started_by_app = False
            self.log("Jemand ist gerade angekommen, beende Reiningung!")

    def set_cleaning_mode_input_boolean(self, entity: Union[str, dict],
                                        attribute: str, old: str,
                                        new: str, kwargs: dict) -> None:
        """Set the input boolean for the cleaning mode."""
        if 'cleaning_mode' in MODES and old != new:
            if new == self.VacuumState.running.value:
                self.turn_on(MODES[CLEANING_MODE])
            elif new == self.VacuumState.charging.value:
                self.turn_off(MODES[CLEANING_MODE])
    

class NotifyWhenBinFull(AppBase):
    """Define a feature to send a notification when the bin is full."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_ENTITIES: vol.Schema({
            vol.Required(VACUUM): vol_help.entity_id,
        }, extra=vol.ALLOW_EXTRA),
        CONF_NOTIFICATIONS: vol.Schema({
            vol.Required(CONF_TARGETS): vol.In(PERSONS.keys()),
            vol.Optional(CONF_INTERVAL): int,
        }, extra=vol.ALLOW_EXTRA),
    })
    
    def configure(self) -> None:
        """Configure."""
        self.listen_state(self.notify_bin_full,
                          self.vacuum_app.vacuum,
                          attribute=BIN_FULL,
                          old=False,
                          new=True,
                          constrain_app_enabled=1)

        self.listen_state(self.bin_emptied,
                          self.vacuum_app.vacuum,
                          attribute=BIN_FULL,
                          old=True,
                          new=False,
                          constrain_app_enabled=1)

    def notify_bin_full(self, entity: Union[str, dict], attribute: str, 
                        old: str, new: str, kwargs: dict) -> None:
        """Send repeating notification that bin should be emptied."""
        self.handles[BIN_FULL] = self.notification_app.notify(
            kind='repeat',
            level='home',
            title="Pedro voll!",
            message="Pedro muss geleert werden",
            targets=self.notifications['targets'],
            interval=self.notifications['interval'] * 60)
        self.log("Abfalleimer voll! Benachrichtige zum Leeren.")

    def bin_emptied(self, entity: Union[str, dict], attribute: str, 
                    old: str, new: str, kwargs: dict) -> None:
        """Cancel the notification when bin has been emptied."""
        if BIN_FULL in self.handles:
            self.handles.pop(BIN_FULL)()
            self.log("Abfalleimer geleert! Schalte Benachrichtigung aus")


class NotifyOnCleaningDay(AppBase):
    """Define a feature to send a notification in morning of the cleaning day."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_PROPERTIES: vol.Schema({
            vol.Optional(CONF_REMINDER_TIME): vol_help.valid_time,
        }, extra=vol.ALLOW_EXTRA),
        CONF_NOTIFICATIONS: vol.Schema({
            vol.Required(CONF_TARGETS): vol.In(PERSONS.keys()),
        }, extra=vol.ALLOW_EXTRA),
    })

    def configure(self) -> None:
        """Configure."""
        self.run_daily(self.notify_on_cleaning_day,
                       self.parse_time(self.properties[CONF_REMINDER_TIME]),
                       constrain_app_enabled=1)

    def notify_on_cleaning_day(self, kwargs: dict) -> None:
        """Send notification in the morning to remind of cleaning day."""
        self.notification_app.notify(
            kind='single',
            level='emergency',
            title="Putztag",
            message=f"Heute ist Putztag. Bitte Möbel richten!",
            targets=self.notifications['targets'])
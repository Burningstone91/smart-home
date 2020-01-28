"""Define automations for home security system."""

from enum import Enum
from typing import Union

import voluptuous as vol

import voluptuous_helper as vol_help
from appbase import AppBase, APP_SCHEMA
from constants import CONF_ENTITIES, CONF_NOTIFICATIONS, CONF_TARGETS, ON
from house_config import HOUSE, MODES, PERSONS


##############################################################################
# App to control security system
#
# ARGS:
# yaml args:
#
# entities:
#   motion: motion sensor that will trigger alarm if armed_motion, comma list
#   other_sensors: other sensors that trigger if armed_no_motion or
#                  armed_motion, comma list
#   alarm_lights: lights that will flash red when alert, comma list
#
##############################################################################

ALARM_STATE = "alarm_state"

CONF_ALARM_LIGHTS = "alarm_lights"
CONF_MOTION_SENSORS = "motion_sensors"
CONF_DOOR_SENSORS = "door_sensors"

PRESENCE_STATE = "presence_state"

CLEANING_MODE = "cleaning_mode"

WRONG_ALARM = "wrong_alarm"


class SecurityAutomation(AppBase):
    """Define a base for security automations."""

    APP_SCHEMA = APP_SCHEMA.extend(
        {
            CONF_ENTITIES: vol.Schema(
                {
                    vol.Required(CONF_ALARM_LIGHTS): vol.Schema(
                        [vol.Optional(vol_help.entity_id)]
                    ),
                    vol.Required(CONF_MOTION_SENSORS): vol.Schema(
                        [vol.Optional(vol_help.entity_id)]
                    ),
                    vol.Required(CONF_DOOR_SENSORS): vol.Schema(
                        [vol.Optional(vol_help.entity_id)]
                    ),
                },
                extra=vol.ALLOW_EXTRA,
            )
        }
    )

    class AlarmType(Enum):
        """Define an enum for Alarm types."""

        armed_no_motion = "Scharf ohne Bewegung"
        armed_motion = "Scharf mit Bewegung"
        disarmed = "Ungesichert"
        alert = "Einbrecher"

    def configure(self) -> None:
        """Configure."""
        self.alarm_lights = self.entities[CONF_ALARM_LIGHTS]
        self.motion_sensors = self.entities[CONF_MOTION_SENSORS]
        self.door_sensors = self.entities[CONF_DOOR_SENSORS]
        self.code = self.args["code"]

        for entity in self.motion_sensors:
            self.listen_state(
                self.motion_triggered, entity, new=ON, constrain_app_enabled=1
            )

        for entity in self.door_sensors:
            self.listen_state(
                self.door_opened, entity, new=ON, constrain_app_enabled=1
            )

    @property
    def alarm_state(self) -> "AlarmType":
        """Return the current state of the security system."""
        return self.AlarmType(self.get_state(HOUSE[ALARM_STATE]))

    @alarm_state.setter
    def alarm_state(self, alarm_state: AlarmType) -> None:
        """Set the the security system to given state."""
        self.select_option(HOUSE[ALARM_STATE], alarm_state.value)
        if alarm_state == self.AlarmType.armed_motion:
            self.call_service(
                "alarm_control_panel/alarm_arm_away",
                entity_id=HOUSE["alarm_panel"],
                code=self.code
            )
        elif alarm_state == self.AlarmType.armed_no_motion:
            self.call_service(
                "alarm_control_panel/alarm_arm_home",
                entity_id=HOUSE["alarm_panel"],
                code=self.code
            )
        elif alarm_state == self.AlarmType.disarmed:
            self.call_service(
                "alarm_control_panel/alarm_disarm",
                entity_id=HOUSE["alarm_panel"],
                code=self.code
            )
        elif alarm_state == self.AlarmType.alert:
            self.call_service(
                "alarm_control_panel/alarm_trigger",
                entity_id=HOUSE["alarm_panel"],
                code=self.code
            )

    def motion_triggered(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Take action when motion sensor is triggered based on alarm state."""
        if self.alarm_state == self.AlarmType.armed_motion:
            self.alarm_state = self.AlarmType.alert
            self.log(
                f"Bewegung im " f"{entity.split('.')[1].split('_')[1].capitalize()}!!!"
            )

    def door_opened(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Take action when a door is opened based on alarm state."""
        if self.alarm_state in (
            self.AlarmType.armed_motion,
            self.AlarmType.armed_no_motion,
        ):
            self.alarm_state = self.AlarmType.alert
            self.log(
                f"{entity.split('.')[1].split('_')[0].capitalize()}"
                f" im/in der "
                f"{entity.split('.')[1].split('_')[1].capitalize()}"
                f" wurde geöffnet!!!"
            )

    # test presence first
    # need a way to cancel flash lights
    # if new == 'on' or new == 'offen':
    #     self.log("Lichter werden jetzt blinken!")
    #     for light in self.alarm_lights:
    #         self.turn_on(light, brightness=255, color_name='white')
    #         self.flash_lights(light)

    def flash_lights(self, light: str) -> None:
        """Flash lights as long as alarm state is alert."""
        self.toggle(light)
        if self.self.alarm_state == self.AlarmType.alert:
            self.run_in(self.flash_lights(light), 1)


class ArmOnDeparture(AppBase):
    """Define a feature to arm the security system when everyone left."""

    def configure(self):
        """Configure."""
        self.listen_state(
            self.noone_home, HOUSE[PRESENCE_STATE], constrain_app_enabled=1
        )

    def noone_home(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Arm the security system when everyone left."""
        someone_home_states = [
            self.presence_app.HouseState.someone.value,
            self.presence_app.HouseState.everyone.value,
        ]
        if (new not in someone_home_states) and (old in someone_home_states):
            self.security_app.alarm_state = self.security_app.AlarmType.armed_motion
            self.log("Alle sind gegangen. Stelle Alarm scharf!")


class DisarmOnArrival(AppBase):
    """Define a feature to disarm the security system when someone arrives."""

    def configure(self):
        """Configure."""
        self.listen_state(
            self.someone_home, HOUSE[PRESENCE_STATE], constrain_app_enabled=1
        )

    def someone_home(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Disarm the security system when someone arrives."""
        someone_home_states = [
            self.presence_app.HouseState.someone.value,
            self.presence_app.HouseState.everyone.value,
        ]
        if (new in someone_home_states) and (old not in someone_home_states):
            self.security_app.alarm_state = self.security_app.AlarmType.disarmed
            self.log("Jemand ist jetzt zu Hause. Schalte Alarm aus!")


class ArmDisarmCleaning(AppBase):
    """Define a feature to disable the motion sensors when the vacuum runs."""

    def configure(self):
        """Configure."""
        self.listen_state(
            self.cleaning_mode_changed, MODES[CLEANING_MODE], constrain_app_enabled=1
        )

    def cleaning_mode_changed(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Set the security system based on the state of the vacuum cleaner."""
        if new == "on" and self.presence_app.noone_home:
            self.security_app.alarm_state = self.security_app.AlarmType.armed_no_motion
            self.log("Pedro putzt jetzt. Schalte Bewegungssensoren aus!")
        elif new == "off" and self.presence_app.noone_home:
            self.security_app.alarm_state = self.security_app.AlarmType.armed_motion
            self.log("Pedro ist fertig. Schalte Bewegungssensoren wieder ein!")


class NotificationOnChange(AppBase):
    """Define a feature to send a notification when the alarm state changed."""

    APP_SCHEMA = APP_SCHEMA.extend(
        {
            CONF_NOTIFICATIONS: vol.Schema(
                {vol.Required(CONF_TARGETS): vol.In(PERSONS.keys())},
                extra=vol.ALLOW_EXTRA,
            )
        }
    )

    def configure(self):
        """Configure."""
        self.listen_state(
            self.alarm_state_changed, HOUSE[ALARM_STATE], constrain_app_enabled=1
        )

        self.listen_event(
            self.disarm_on_push_notification,
            "html5_notification.clicked",
            action=WRONG_ALARM,
            constrain_app_enabled=1,
        )

    def alarm_state_changed(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Send notification when alarm state changed."""
        self.notification_app.notify(
            kind="single",
            level="emergency",
            title="Alarm Status gewechselt",
            message=f"Der neue Alarm Status ist {new}",
            targets=self.notifications["targets"],
            data={"actions": [{"action": WRONG_ALARM, "title": "Fehlalarm"}]},
        )

    def disarm_on_push_notification(
        self, event_name: str, data: dict, kwargs: dict
    ) -> None:
        """Disarm when push notification got clicked."""
        self.security_app.alarm_state = self.security_app.AlarmType.disarmed
        self.log("Fehlalarm, Alarmanlage wird ausgeschaltet!")


class NotifyOnBadLoginAttempt(AppBase):
    """Define a feature to send a notification when bad login happened."""

    APP_SCHEMA = APP_SCHEMA.extend(
        {
            CONF_NOTIFICATIONS: vol.Schema(
                {vol.Required(CONF_TARGETS): vol.In(PERSONS.keys())},
                extra=vol.ALLOW_EXTRA,
            )
        }
    )

    def configure(self):
        """Configure."""
        self.listen_state(
            self.bad_login_attempt,
            "persistent_notification.http_login",
            new="notifying",
        )

    def bad_login_attempt(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Send notification when bad login happened."""
        msg = self.get_state("persistent_notification.http_login", attribute="message")
        self.notification_app.notify(
            kind="single",
            level="emergency",
            title="Falscher Loginversuch",
            message=msg,
            targets=self.notifications["targets"],
        )


class LastMotion(AppBase):
    """Define a feature to update a sensor with the
       name of the room where last motion was detected"""

    APP_SCHEMA = APP_SCHEMA.extend(
        {
            CONF_ENTITIES: vol.Schema(
                {
                    vol.Required(CONF_MOTION_SENSORS): vol.Schema(
                        [vol.Optional(vol_help.entity_id)]
                    )
                },
                extra=vol.ALLOW_EXTRA,
            )
        }
    )

    def configure(self):
        """Configure."""
        for sensor in self.entities[CONF_MOTION_SENSORS]:
            self.listen_state(self.motion_detected, sensor, new="on")

    def motion_detected(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Select the room input select based on the triggered entity."""
        room_name = entity.split(".")[1].split("_", 1)[-1].capitalize()
        self.select_option(HOUSE["last_motion"], room_name)

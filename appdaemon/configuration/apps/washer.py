"""Define automations for washer-type appliances."""

from enum import Enum
from typing import Union

import voluptuous as vol

import voluptuous_helper as vol_help
from appbase import AppBase, APP_SCHEMA
from constants import (
    CONF_ENTITIES,
    CONF_INTERVAL,
    CONF_NOTIFICATIONS,
    CONF_PROPERTIES,
    CONF_TARGETS,
)
from house_config import PERSONS


WASHER_STATE = "washer_state"

CONF_POWER = "power"
CONF_STATUS = "status"

CONF_THRESHOLDS = "thresholds"
CONF_RUNNING_THRESHOLD = "running"
CONF_DRYING_THRESHOLD = "drying"
CONF_CLEAN_THRESHOLD = "clean"
THRESHOLDS_TYPES = (CONF_RUNNING_THRESHOLD, CONF_DRYING_THRESHOLD, CONF_CLEAN_THRESHOLD)

DONE = "done"
WASHER_CLEAN = "washer_clean"
CONF_MSG = "message"


class WasherAutomation(AppBase):  # pylint: disable=too-few-public-methods
    """Define a base for washer-type appliances automations."""

    APP_SCHEMA = APP_SCHEMA.extend(
        {
            CONF_ENTITIES: vol.Schema(
                {
                    vol.Required(CONF_POWER): vol_help.entity_id,
                    vol.Required(CONF_STATUS): vol_help.entity_id,
                },
                extra=vol.ALLOW_EXTRA,
            )
        }
    )

    class WasherStates(Enum):
        """Define an enum for Washer states."""

        clean = "Sauber"
        dirty = "Dreckig"
        running = "Läuft"
        drying = "Trocknung"

    @property
    def washer_state(self) -> "WasherStates":
        """Return the current state of the washer appliance."""
        return self.WasherStates(self.get_state(self.entities[CONF_STATUS]))

    @washer_state.setter
    def washer_state(self, washer_state: WasherStates) -> None:
        """Set the the washer appliance to given state."""
        self.select_option(self.entities[CONF_STATUS], washer_state.value)


class NotifyWhenWasherDone(AppBase):
    """Define a feature to send a notification when the washer has finished."""

    APP_SCHEMA = APP_SCHEMA.extend(
        {
            CONF_PROPERTIES: vol.Schema(
                {vol.Required(vol.In(THRESHOLDS_TYPES)): int}, extra=vol.ALLOW_EXTRA
            ),
            CONF_NOTIFICATIONS: vol.Schema(
                {
                    vol.Required(CONF_TARGETS): vol.In(PERSONS.keys()),
                    vol.Required(CONF_MSG): str,
                    vol.Optional(CONF_INTERVAL): int,
                },
                extra=vol.ALLOW_EXTRA,
            ),
        }
    )

    def configure(self) -> None:
        """Configure."""
        self.listen_state(
            self.power_changed,
            self.manager.entities[CONF_POWER],
            constrain_app_enabled=1,
        )

        self.listen_state(
            self.status_changed,
            self.manager.entities[CONF_STATUS],
            constrain_app_enabled=1,
        )

        self.listen_event(
            self.cancel_on_push_notification,
            "html5_notification.clicked",
            action=DONE,
            constrain_app_enabled=1,
        )

    def power_changed(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Set washer state based on power change."""
        power = float(new)
        thresholds = self.properties[CONF_THRESHOLDS]
        if (
            self.manager.washer_state != self.manager.WasherStates.running
            and power >= thresholds[CONF_RUNNING_THRESHOLD]
        ):
            self.manager.washer_state = self.manager.WasherStatus.running
            self.log("Washer set to Running")
        elif (
            self.manager.washer_state == self.manager.WasherStates.running
            and power <= thresholds[CONF_DRYING_THRESHOLD]
        ):
            self.manager.washer_state = self.manager.WasherStatus.drying
            self.log("Washer set to Drying")
        elif (
            self.manager.washer_state == self.manager.WasherStates.drying
            and power == thresholds[CONF_CLEAN_THRESHOLD]
        ):
            self.manager.washer_state = self.manager.WasherStatus.clean
            self.log("Washer set to Clean")

    def status_changed(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Take action based on status change."""
        if new == self.manager.WasherStates.clean.value:
            self.handles[WASHER_CLEAN] = self.notification_app.notify(
                kind="repeat",
                level="home",
                title="Waschgerät fertig!",
                message=self.notifications[CONF_MSG],
                targets=self.notifications[CONF_TARGETS],
                interval=self.notifications[CONF_INTERVAL] * 60,
                data={"actions": [{"action": DONE, "title": "Erledigt"}]},
            )
            self.log("Waschgerät fertig! Benachrichtige zum Leeren!")

        elif old == self.manager.WasherStates.clean.value:
            if WASHER_CLEAN in self.handles:
                self.handles.pop(WASHER_CLEAN)()
                self.log("Waschgerät geleert. Schalte Benachrichtigung aus.")

    def cancel_on_push_notification(
        self, event_name: str, data: dict, kwargs: dict
    ) -> None:
        """Cancel the notification when push notification got clicked."""
        self.manager.washer_state = self.manager.WasherStates.dirty
        self.log("Waschgerät wurde geleert!")

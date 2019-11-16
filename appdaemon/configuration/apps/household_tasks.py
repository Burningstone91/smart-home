"""Define automations for household tasks"""

import json
import voluptuous as vol
from datetime import datetime, timedelta

import voluptuous_helper as vol_help
from appbase import APP_SCHEMA, AppBase
from constants import CONF_INTERVAL, CONF_NOTIFICATIONS, CONF_PROPERTIES, CONF_TARGETS
from house_config import PERSONS


COMPLETED = "completed"
REMINDER = "reminder"
CONF_REMINDER_TIME = "reminder_time"
CONF_TITLE = "title"
CONF_MESSAGE = "message"


class HouseHoldTasks(AppBase):
    """Define a feature for managing household tasks."""

    def configure(self) -> None:
        """Configure."""
        self.task_entity_id = self.entities["task_sensor"]
        self.task_name = self.task_entity_id.split(".")[1]
        self.expiry_days = self.properties["expiry_in_days"]

        self.run_daily(
            self.check_task_due,
            self.parse_time(self.properties[CONF_REMINDER_TIME]),
            constrain_app_enabled=1,
        )

        self.listen_event(
            self.mark_task_completed,
            "html5_notification.clicked",
            action=self.task_name,
        )
        self.log("Init complete")

    def check_task_due(self, kwargs: dict) -> None:
        """Check if task has been done in threshold."""
        task_last_done = self.get_task_date()

        if task_last_done + timedelta(days=self.expiry_days) < datetime.today():
            self.send_reminder()

    def send_reminder(self) -> None:
        """Send a repeating actionable push notification as a reminder."""
        self.handles[REMINDER] = self.notification_app.notify(
            kind="single",
            level="home",
            title=self.properties[CONF_TITLE],
            message=self.properties[CONF_MESSAGE],
            targets=self.notifications[CONF_TARGETS],
            interval=self.notifications[CONF_INTERVAL] * 60,
            data={"actions": [{"action": self.task_name, "title": "Erledigt"}]},
        )

    def mark_task_completed(self, event_name: str, data: dict, kwargs: dict) -> None:
        """Mark the task as completed by updating the timestamp of the sensor over MQTT."""
        timestamp = datetime.timestamp(datetime.now())
        payload = {
            "timestamp": int(timestamp),
            "visibility_timeout": "none",
            "visible": "true",
            "unit_of_measurement": "timestamp",
        }

        self.mqtt.mqtt_publish(
            f"homeassistant/sensor/{self.task_name}/state",
            json.dumps(payload),
            namespace="mqtt",
        )

        self.log(f"Der Task '{self.task_name}' wurde als erledigt markiert.")

    def get_task_date(self):
        """Get the timestamp of the task and convert into date."""
        timestamp = self.get_state(self.task_entity_id)
        return datetime.fromtimestamp(int(timestamp))


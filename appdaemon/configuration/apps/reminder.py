"""Define automations for reminders."""
from datetime import datetime

import voluptuous as vol

import voloptuous_helper as vol_help
from appbase import AppBase, APP_SCHEMA
from constants import (
    CONF_INTERVAL, CONF_NOTIFICATIONS, CONF_PROPERTIES, CONF_TARGETS
)
from house_config import PERSONS


DONE = 'done'
REMINDER = 'reminder'
CONF_TITLE = 'title'
CONF_MESSAGE = 'message'
CONF_REMINDER_DATE = 'reminder_date'
CONF_REMINDER_TIME = 'reminder_time'
CONF_REPEAT = 'repeat'
CONF_REPEAT_TYPE = 'type'
CONF_REPEAT_FREQ = 'frequency'

DAYS = 'days'
WEEKS = 'weeks'
MONTHS = 'months'
REPEAT_TYPES = (DAYS, WEEKS, MONTHS)


class ReminderAutomation(AppBase):
    """Define a feature for recurring or one time reminders."""

    APP_SCHEMA = APP_SCHEMA.extend({
        CONF_PROPERTIES: vol.Schema({
            vol.Required(CONF_TITLE): str,
            vol.Required(CONF_MESSAGE): str,
            vol.Required(CONF_REMINDER_DATE): vol_help.valid_date,
            vol.Required(CONF_REMINDER_TIME): vol_help.valid_time,
            vol.Optional(CONF_REPEAT): vol.Schema({
                vol.Required(CONF_REPEAT_TYPE): vol.In(REPEAT_TYPES),
                vol.Required(CONF_REPEAT_FREQ): int,
            }),
        }, extra=vol.ALLOW_EXTRA),
        CONF_NOTIFICATIONS: vol.Schema({
            vol.Required(CONF_TARGETS): vol.In(PERSONS.keys()),
            vol.Optional(CONF_INTERVAL): int,
        }, extra=vol.ALLOW_EXTRA),
    })

    def configure(self) -> None:
        """Configure."""
        self.reminder_time = self.properties[CONF_REMINDER_TIME]
        self.reminder_date = datetime.strptime(
            self.properties[CONF_REMINDER_DATE], '%d.%m.%Y')
        self.repeat_type = self.properties[CONF_REPEAT][CONF_REPEAT_TYPE]
        self.repeat_freq = self.properties[CONF_REPEAT][CONF_REPEAT_FREQ]

        self.run_daily(self.check_reminder_date,
                       self.parse_time(self.properties[CONF_REMINDER_TIME]),
                       constrain_app_enabled=1)

        self.listen_event(self.disable_on_push_notification,
                          'html5_notification.clicked',
                          action=DONE,
                          constrain_app_enabled=1)

    def check_reminder_date(self, kwargs: dict) -> None:
        """Check if today is a reminder day, if yes send reminder."""
        days_to_reminder_date = (datetime.today() - self.reminder_date).days
        divisor = None
        if self.repeat_type == DAYS:
            divisor = self.repeat_freq
        elif self.repeat_type == WEEKS:
            divisor = self.repeat_freq * 7
        elif self.repeat_type == MONTHS:
            divisor = self.repeat_freq * 30

        if not days_to_reminder_date // divisor == 0:
            self.send_reminder()
            self.log("Erinnerungstag! Erinnerung gesendet.")
        
    def send_reminder(self) -> None:
        """Send a repeating actionable push notification as a reminder."""
        self.handles[REMINDER] = self.notification_app.notify(
            kind='repeat',
            level='home',
            title=self.properties[CONF_TITLE],
            message=self.properties[CONF_MESSAGE],
            targets=self.notifications[CONF_TARGETS],
            interval=self.notifications[CONF_INTERVAL] * 60,
            data={'actions': [{
                'action': DONE,
                'title': 'Erledigt'
            }]})

    def disable_on_push_notification(self, event_name: str,
                                    data: dict, kwargs: dict) -> None:
        """Disable reminder when 'done' got clicked on push notification."""
        if REMINDER in self.handles:
            self.handles.pop(REMINDER)()
            self.log("Aufgabe erledigt! Schalte Erinnerung aus.")




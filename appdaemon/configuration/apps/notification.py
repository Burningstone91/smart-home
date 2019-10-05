"""Define automations for notifications."""

from datetime import datetime
from enum import Enum
from typing import Callable, Union

from appbase import AppBase
from constants import OFF, PERSON
from house_config import HOUSE, PERSONS, MODES


##############################################################################
# App to control notifications,
#
# ARGS:
# yaml args:
#
# send method args:
# notification_type: single, repeat (repeat every interval until cancelled
# notification_level: emergency, home (emergency --> send immediately
#                                      home --> send when person arrives home
# notification example:
# if self.bin_full:
#     self.handles[BIN_FULL] = self.notification_app.notify(
#         'repeat',
#         'home',
#         "Pedro voll!",
#         "Pedro muss geleert werden",
#         self.properties['notification_targets'],
#         interval=self.properties['notification_interval'])
# else:
#     if BIN_FULL in self.handles:
#         self.handles.pop(BIN_FULL)()
##############################################################################


TITLE = "title"
MESSAGE = "message"
DATA = "data"
INTERVAL = "interval"
NOTIFIER = "notifier"
PRESENCE_STATE = "presence_state"
SLEEP_MODE = "sleep_mode"


class NotificationAutomation(AppBase):
    """Define a base feature for notifications."""

    class NotificationType(Enum):
        """Define an enum for notification types."""

        single = "single"
        repeat = "repeat"

    class NotificationLevel(Enum):
        """Define an enum for notification levels."""

        emergency = "emergency"
        home = "home"

    # pylint: disable=too-few-public-methods,too-many-instance-attributes
    class Notification:
        """Define a notification object."""

        def __init__(self, kind, level, title, message, targets, **kwargs):
            self.kind = kind
            self.level = level
            self.title = title
            self.message = message
            self.targets = targets
            self.cancel = None

            self.interval = kwargs.get(INTERVAL)
            self.data = kwargs.get(DATA)

    def configure(self):
        """Configure."""
        self.briefing_list = {}

        for person, attribute in PERSONS.items():
            self.listen_state(
                self.someone_arrived,
                attribute[PRESENCE_STATE],
                new=self.presence_app.PresenceState.just_arrived.value,
                person=person,
            )

        self.listen_state(self.sleep_mode_deactivated, MODES[SLEEP_MODE], new=OFF)

    def someone_arrived(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Send a briefing to the person that arrived home."""
        self.send_briefing(kwargs[PERSON])

    def sleep_mode_deactivated(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Send a briefing to persons home when sleep mode is deactivated."""
        for person in list(self.briefing_list.keys()):
            if person in self.presence_app.persons_home:
                self.send_briefing(person)

    def add_item_to_briefing(self, notification: Notification) -> None:
        """Add given notification to the briefing list."""
        for target in notification.targets.split(","):
            if target in PERSONS.keys():
                self.briefing_list[target] = {
                    notification.title: {
                        TITLE: notification.title,
                        MESSAGE: notification.message,
                        DATA: notification.data,
                    }
                }

    def remove_item_from_briefing(self, title: str) -> None:
        """Remove items of the given person from the briefing list."""
        for target, item in self.briefing_list.items():
            if item == title:
                del self.briefing_list[target][title]

    def remove_person_from_briefing(self, person: str) -> None:
        """Remove all items of the given person from the briefing list."""
        if person in self.briefing_list.keys():
            del self.briefing_list[person]

    def send_briefing(self, person: str) -> None:
        """Send each notification on the briefing list for given person."""
        if person in self.briefing_list.keys():
            for attribute in self.briefing_list[person].values():
                self.call_service(
                    f"notify/" f"{PERSONS[person][NOTIFIER].split('.')[1]}",
                    title=attribute[TITLE],
                    message=attribute[MESSAGE],
                    data=attribute[DATA],
                )
            self.remove_person_from_briefing(person)
            self.log(f"Briefing an {person} gesendet.")

    def notify(
        self,
        kind: str,
        level: str,
        title: str,
        message: str,
        targets: str,
        **kwargs: dict,
    ) -> Callable:
        """Return an object to send a notification."""
        return self.send_notification(
            self.Notification(
                kind,
                level,
                title,
                message,
                targets,
                data=kwargs.get(DATA, {}),
                interval=kwargs.get(INTERVAL, 3600),
            )
        )

    def send_notification(self, notification: Notification) -> Callable:
        """Send single or repeating notification and
           return a method to cancel notification"""
        one_target_available = False

        if notification.level == self.NotificationLevel.home.value:
            for target in notification.targets.split(","):
                if self.target_available(target):
                    one_target_available = True
                    break
            if not one_target_available:
                self.add_item_to_briefing(notification)

        if notification.kind == self.NotificationType.single.value:
            handle = self.run_in(self.send, 1, notification=notification)
        else:
            handle = self.run_every(
                self.send,
                datetime.now(),
                notification.interval,
                notification=notification,
            )

        def cancel(delete: bool = True) -> None:
            """Define a method to cancel the notification."""
            self.cancel_timer(handle)
            self.remove_item_from_briefing(notification.title)

        notification.cancel = cancel

        return cancel

    def send(self, kwargs: dict) -> None:
        """Send a notification."""
        notification = kwargs["notification"]
        for target in self.get_targets(notification.targets, notification.level):
            self.call_service(
                f"notify/{target.split('.')[1]}",
                title=notification.title,
                message=notification.message,
                data=notification.data,
            )
            target_name = target.split(".")[1].split("_")[0].capitalize()
            self.log(f"Nachricht '{notification.title}' an {target_name}")
            self.remove_person_from_briefing(target_name)

    def get_targets(self, targets: str, level: str) -> list:
        """Return list of targets based on given level and targets string."""
        targets_split = targets.split(",")
        targets_list = []

        if level == self.NotificationLevel.emergency.value:
            if "everyone" in targets_split:
                targets_list.append(HOUSE[NOTIFIER])
                for person, attribute in PERSONS.items():
                    targets_list.append(attribute[NOTIFIER])
            else:
                if "home" in targets_split:
                    targets_list.append(HOUSE[NOTIFIER])
                for person, attribute in PERSONS.items():
                    if person in targets_split:
                        targets_list.append(attribute[NOTIFIER])
        else:
            if "everyone" in targets_split:
                targets_list.append(HOUSE[NOTIFIER])
                for person, attribute in PERSONS.items():
                    if self.target_available(person):
                        targets_list.append(attribute[NOTIFIER])
            else:
                if "home" in targets_split:
                    targets_list.append(HOUSE[NOTIFIER])
                for person, attribute in PERSONS.items():
                    if person in targets_split and self.target_available(person):
                        targets_list.append(attribute[NOTIFIER])

        return targets_list

    def target_available(self, target: str) -> bool:
        """Return true if target is at home and sleep mode is off."""
        return (
            target in self.presence_app.persons_home
            and self.get_state(MODES[SLEEP_MODE]) == OFF
        )

from datetime import datetime
from enum import Enum
from typing import Callable, Union

from appbase import AppBase
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


class NotificationAutomation(AppBase):
    class NotificationType(Enum):
        single = 'single'
        repeat = 'repeat'

    class NotificationLevel(Enum):
        emergency = 'emergency'
        home = 'home'

    class Notification:
        def __init__(self, kind, level, title, message, targets, **kwargs):
            self.kind = kind
            self.level = level
            self.title = title
            self.message = message
            self.targets = targets
            self.cancel = None

            self.interval = kwargs.get('interval')
            self.data = kwargs.get('data')

    def initialize(self):
        super().initialize()
        self.briefing_list = {}

        # send briefing when someone arrives home
        for person, attribute in PERSONS.items():

            self.listen_state(self.someone_arrived,
                              attribute['presence_state'],
                              new=self.presence_app.PresenceState.just_arrived.value,
                              person=person)

        # send briefing when sleep mode is deactivated
        self.listen_state(self.sleep_mode_deactivated,
                          MODES['sleep_mode'],
                          new='off')

    def someone_arrived(self, entity: Union[str, dict], attribute: str,
                        old: str, new: str, kwargs: dict) -> None:
        self.send_briefing(kwargs['person'])

    def sleep_mode_deactivated(self, entity: Union[str, dict], attribute: str,
                               old: str, new: str, kwargs: dict) -> None:
        for person in list(self.briefing_list.keys()):
            self.send_briefing(person)

    def add_item_to_briefing(self, notification: Notification) -> None:
        item = notification.title
        for target in notification.targets.split(','):
            if target in PERSONS.keys():
                self.briefing_list[target] = {notification.title: {
                                                'title': notification.title,
                                                'message': notification.message,
                                                'data': notification.data
                                                }
                                             }

    def remove_person_from_briefing(self, person: str) -> None:
        if person in self.briefing_list.keys():
            del self.briefing_list[person]

    def send_briefing(self, person: str) -> None:
        if person in self.briefing_list.keys():
            for item, attribute in self.briefing_list[person].items():
                self.call_service(f"notify/"
                                  f"{PERSONS[person]['notifier'].split('.')[1]}",
                                  title=attribute['title'],
                                  message=attribute['message'],
                                  data=attribute['data'])
            self.remove_person_from_briefing(person)
            self.log(f'Briefing an {person} gesendet.')

    def notify(self, kind: str, level: str, title: str, message: str,
               targets: str, **kwargs: dict) -> Callable:
        return self.send_notification(
            self.Notification(kind, level, title, message, targets,
                              data=kwargs.get('data', {}),
                              interval=kwargs.get('interval', 3600)))

    def send_notification(self, notification: Notification) -> Callable:
        one_target_available = False

        if notification.level == self.NotificationLevel.home.value:
            for target in notification.targets.split(','):
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
                notification=notification)

        def cancel(delete: bool = True) -> None:
            self.cancel_timer(handle)
            self.remove_item_from_briefing(notification.title)

        notification.cancel = cancel

        return cancel

    def send(self, kwargs: dict) -> None:
        notification = kwargs['notification']
        for target in self.get_targets(notification.targets, notification.level):
            self.call_service(f"notify/{target.split('.')[1]}",
                              title=notification.title,
                              message=notification.message,
                              data=notification.data)
            self.log(f"Nachricht '{notification.title}' an "
                     f"{target.split('.')[1].split('_')[0].capitalize()}")
            self.remove_person_from_briefing(target)

    def get_targets(self, targets: str, level: str) -> list:
        targets_split = targets.split(',')
        targets_list = []

        if level == self.NotificationLevel.emergency.value:
            if 'everyone' in targets_split:
                targets_list.append(HOUSE['notifier'])
                for person, attribute in PERSONS.items():
                    targets_list.append(attribute['notifier'])
            else:
                if 'home' in targets_split:
                    targets_list.append(HOUSE['notifier'])
                for person, attribute in PERSONS.items():
                    if person in targets_split:
                        targets_list.append(attribute['notifier'])
        else:
            if 'everyone' in targets_split:
                targets_list.append(HOUSE['notifier'])
                for person, attribute in PERSONS.items():
                    if self.target_available(person):
                        targets_list.append(attribute['notifier'])
            else:
                if 'home' in targets_split:
                    targets_list.append(HOUSE['notifier'])
                for person, attribute in PERSONS.items():
                    if person in targets_split and self.target_available(person):
                        targets_list.append(attribute['notifier'])

        return targets_list

    def target_available(self, target: str) -> bool:
        return (target in self.presence_app.persons_home and
                self.get_state(MODES['sleep_mode']) == 'off')

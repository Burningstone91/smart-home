import datetime
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

        for person in PERSONS.keys():
            # send briefing when someone arrives home
            self.listen_state(self.someone_arrived,
                              PERSONS[person]['presence_state'],
                              constrain_app_enabled=1,
                              person=person)

    def someone_arrived(self, entity: Union[str, dict], attribute: str,
                        old: str, new: str, kwargs: dict) -> None:
        person = kwargs['person']
        if (person in self.presence_app.persons_home and
                self.first_briefing[person]):
            self.send_briefing(person)
            self.first_briefing[person] = False

    def add_item_to_briefing(self, notification: Notification) -> None:
        for target in notification.targets.split(','):
            item = notification.title
            self.briefing_list[target][item] = {'title': notification.title,
                                                'message': notification.message,
                                                'data': notification.data}

    def remove_item_from_briefing(self, name: str) -> None:
        for target, item in self.briefing_list.items():
            if item == name:
                del self.briefing_list[target][name]

    def notify(self, kind: str, level: str, title: str, message: str,
               targets: str, **kwargs: dict) -> Callable:
        return self.send_notification(
            self.Notification(kind, level, title, message, targets,
                              data=kwargs.get('data', {}),
                              interval=kwargs.get('interval', 3600)))

    def send_notification(self, notification: Notification) -> Callable:
        time = datetime.datetime.now() + datetime.timedelta(seconds=10)
        if notification.level == self.NotificationLevel.home.value:
            self.add_item_to_briefing(notification)
        if notification.kind == self.NotificationType.single.value:
            handle = self.run_at(self.send, time, notification=notification)
        else:
            handle = self.run_every(
                self.send,
                time,
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

    def get_targets(self, targets: str, level: str) -> list:
        targets_split = targets.split(',')
        targets_list = []
        persons_home = self.presence_app.who_in_state(
            self.presence_app.PresenceState.home,
            self.presence_app.PresenceState.just_arrived)

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
                        
        elif not self.get_state(MODES['sleep_mode']):
            if 'everyone' in targets_split:
                targets_list.append(HOUSE['notifier'])
                for person, attribute in PERSONS.items():
                    if person in persons_home:
                        targets_list.append(attribute['notifier'])
            else:
                if 'home' in targets_split:
                    targets_list.append(HOUSE['notifier'])
                for person, attribute in PERSONS.items():
                    if person in targets_split:
                        if person in persons_home:
                            targets_list.append(attribute['notifier'])

        return targets_list

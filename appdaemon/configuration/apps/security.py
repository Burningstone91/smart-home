from enum import Enum
from typing import Union

from appbase import AppBase
from house_config import HOUSE, MODES


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


class SecurityAutomation(AppBase):
    class AlarmType(Enum):
        armed_no_motion = 'Scharf ohne Bewegung'
        armed_motion = 'Scharf mit Bewegung'
        disarmed = 'Ungesichert'
        alert = 'Einbrecher'

    def initialize(self) -> None:
        super().initialize()

        self.alarm_lights = self.entities['alarm_lights'].split(',')
        self.motion_entities = self.entities.get('motion', '').split(',')
        self.other_security_entities = self.entities.get('other_security', '').split(',')

        # take action when a motion sensor is triggered
        for entity in self.motion_entities:
            self.listen_state(self.motion_triggered,
                              entity,
                              new='on',
                              constrain_app_enabled=1)

        # take action when a non-motion sensor is triggered
        for entity in self.other_security_entities:
            self.listen_state(self.other_sensor_triggered,
                              entity,
                              new='offen',
                              constrain_app_enabled=1)

    @property
    def alarm_state(self) -> AlarmType:
        return self.AlarmType(self.get_state(HOUSE['alarm_state']))

    @alarm_state.setter
    def alarm_state(self, alarm_state: AlarmType) -> None:
        self.select_option(HOUSE['alarm_state'], alarm_state.value)

    def motion_triggered(self, entity: Union[str, dict], attribute: str,
                         old: str, new: str, kwargs: dict) -> None:
        if self.alarm_state == self.AlarmType.armed_motion:
            self.alarm_state = self.AlarmType.alert
            self.log(f"Bewegung im "
                     f"{entity.split('.')[1].split('_')[1].capitalize()}!!!")

    def other_sensor_triggered(self, entity: Union[str, dict], attribute: str,
                               old: str, new: str, kwargs: dict) -> None:
        if self.alarm_state in (self.AlarmType.armed_motion,
                                self.AlarmType.armed_no_motion):
            self.alarm_state = self.AlarmType.alert
            self.log(f"{entity.split('.')[1].split('_')[0].capitalize()}"
                     f" im/in der "
                     f"{entity.split('.')[1].split('_')[1].capitalize()}"
                     f" wurde geöffnet!!!")

#################test presence first############# if presence works, also change enabled presence for lights
################# need a way to cancel flash lights ####################################
        #if new == 'on' or new == 'offen':
        #    self.log("Lichter werden jetzt blinken!")
        #    for light in self.alarm_lights:
        #        self.turn_on(light, brightness=255, color_name='white')
        #        self.flash_lights(light)

    def flash_lights(self, light: str) -> None:
        self.toggle(light)
        if self.self.alarm_state == self.AlarmType.alert:
            self.run_in(self.flash_lights(light), 1)


class ArmOnDeparture(AppBase):
    def initialize(self):
        super().initialize()

        # arm when everyone is gone
        self.listen_state(self.noone_home,
                          HOUSE['presence_state'],
                          constrain_app_enabled=1)

    def noone_home(self, entity: Union[str, dict], attribute: str, old: str,
                   new: str, kwargs: dict) -> None:
        someone_home_states = [self.presence_app.HouseState.someone.value,
                               self.presence_app.HouseState.everyone.value]
        if (new not in someone_home_states) and (old in someone_home_states):
            self.security_app.alarm_state = self.security_app.AlarmType.armed_motion
            self.log("Alle sind gegangen. Stelle Alarm scharf!")


class DisarmOnArrival(AppBase):
    def initialize(self):
        super().initialize()

        # disarm when someone arrives
        self.listen_state(self.someone_home,
                          HOUSE['presence_state'],
                          constrain_app_enabled=1)

    def someone_home(self, entity: Union[str, dict], attribute: str, 
                     old: str, new: str, kwargs: dict) -> None:
        someone_home_states = [self.presence_app.HouseState.someone.value,
                               self.presence_app.HouseState.everyone.value]
        if (new in someone_home_states) and (old not in someone_home_states):
            self.security_app.alarm_state = self.security_app.AlarmType.disarmed
            self.log("Jemand ist jetzt zu Hause. Schalte Alarm aus!")


class ArmDisarmCleaning(AppBase):
    def initialize(self):
        super().initialize()

        # disarm when someone arrives
        self.listen_state(self.cleaning_mode_changed,
                          MODES['cleaning_mode'],
                          constrain_app_enabled=1)

    def cleaning_mode_changed(self, entity: Union[str, dict], attribute: str,
                              old: str, new: str, kwargs: dict) -> None:
        if new == 'on' and self.presence_app.noone_home:
            self.security_app.alarm_state = self.security_app.AlarmType.armed_no_motion
            self.log("Pedro putzt jetzt. Schalte Bewegungssensoren aus!")
        
        if new == 'off' and self.presence_app.noone_home:
            self.security_app.alarm_state = self.security_app.AlarmType.armed_motion
            self.log("Pedro ist fertig. Schalte Bewegungssensoren wieder ein!")

    
class NotificationOnChange(AppBase):
    def initialize(self):
        super().initialize()

        # notify immediately when state of alarm system changes
        self.listen_state(self.alarm_state_changed,
                          HOUSE['alarm_state'],
                          constrain_app_enabled=1)

        # deactivate alarm if respond 'wrong_alarm' is given by target
        self.listen_event(self.disarm_on_push_notification,
                         'html5_notification.clicked',
                         action='wrong_alarm',
                         constrain_app_enabled=1)

    def alarm_state_changed(self, entity: Union[str, dict], attribute: str,
                            old: str, new: str, kwargs: dict) -> None:           
        self.notification_app.notify(
            kind='single',
            level='emergency',
            title="Alarm Status gewechselt",
            message=f"Der neue Alarm Status ist {new}",
            targets=self.notifications['targets'],
            data={'actions': [{
                'action': 'wrong_alarm',
                'title': 'Fehlalarm'
                }]})

    def disarm_on_push_notification(self, event_name: str, data: dict, 
                                    kwargs: dict) -> None:
        self.security_app.alarm_state = self.security_app.AlarmType.disarmed
        self.log("Fehlalarm, Alarmanlage wird ausgeschaltet!")


class LastMotion(AppBase):
    def initialize(self):
        super().initialize()
        self.motion_sensors = self.entities['motion_sensors']

        # change last motion input boolean when motion is detected
        for sensor in self.motion_sensors.split(','):
            self.listen_state(self.motion, sensor, new='on')

    def motion(self, entity: Union[str, dict], attribute: str,
               old: str, new: str, kwargs: dict) -> None:
        room_name = entity.split('.')[1].split('_', 1)[-1].capitalize()
        self.select_option(HOUSE['last_motion'], room_name)

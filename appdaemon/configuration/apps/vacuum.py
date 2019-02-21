from enum import Enum
from typing import Union

from appbase import AppBase
from house_config import HOUSE, MODES

BIN_FULL = 'bin_full'


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


class VacuumAutomation(AppBase):
    class VacuumState(Enum):
        charging = 'Charging'
        running = 'Running'
        returning = 'User Docking'
        stuck = 'Stuck'

    def initialize(self) -> None:
        super().initialize()
        self.started_by_app = False
        cleaning_time = self.parse_time(
            self.properties.get('cleaning_time', '11:00:00'))
        
        if 'vacuum' in self.entities:
            self.vacuum = self.entities['vacuum']
            # scheduled clean cycle
            self.run_daily(self.start_cleaning,
                           cleaning_time,
                           constrain_app_enabled=1)

            # cycle finished
            self.listen_state(self.cleaning_finished,
                              self.vacuum,
                              attribute='status',
                              old=self.VacuumState.returning.value,
                              new=self.VacuumState.charging.value)

            # cancel cycle if someone arrives home
            self.listen_state(self.cancel_cleaning, HOUSE['presence_state'])

            # turn on/off cleaning mode when cleaning/finished cleaning
            self.listen_state(self.set_cleaning_mode_input_boolean,
                              self.vacuum,
                              attribute='status')
        else:
            self.log("Kein Staubsauger konfiguriert, keine Aktion!")

    @property
    def vacuum_state(self) -> VacuumState:
        return self.get_state(self.vacuum, attribute='status')

    def start_cleaning(self, kwargs: dict) -> None:
        self.call_service('vacuum/start_pause', entity_id=self.vacuum)
        self.started_by_app = True
        self.log("Pedro startet die Reinigung!")

    def cleaning_finished(self, entity: Union[str, dict], attribute: str, 
                          old: str, new: str, kwargs: dict) -> None:
        self.started_by_app = False
        self.log("Pedro hat die Reinigung beendet")

    def cancel_cleaning(self, entity: Union[str, dict], attribute: str,
                        old: str, new: str, kwargs: dict) -> None:
        if ((not self.presence_app.noone_home and self.started_by_app) and 
                self.vacuum_state == self.VacuumState.running.value):
            self.call_service('vacuum/return_to_base', entity_id=self.vacuum)
            self.started_by_app = False
            self.log("Jemand ist gerade angekommen, beende Reiningung!")

    def set_cleaning_mode_input_boolean(self, entity: Union[str, dict],
                                        attribute: str, old: str, new: str,
                                        kwargs: dict) -> None:
        if 'cleaning_mode' in MODES and old != new:
            if new == self.VacuumState.running.value:
                self.turn_on(MODES['cleaning_mode'])
            elif new == self.VacuumState.charging.value:
                self.turn_off(MODES['cleaning_mode'])
    

class NotifyWhenBinFull(AppBase):
    def initialize(self) -> None:
        super().initialize()

        # notify when the bin is full
        self.listen_state(self.notify_bin_full,
                          self.vacuum_app.vacuum,
                          attribute='bin_full',
                          old=False,
                          new=True,
                          constrain_app_enabled=1)

        # stop notification when bin has been emptied
        self.listen_state(self.bin_emptied,
                          self.vacuum_app.vacuum,
                          attribute='bin_full',
                          old=True,
                          new=False,
                          constrain_app_enabled=1)

    def notify_bin_full(self, entity: Union[str, dict], attribute: str, 
                        old: str, new: str, kwargs: dict) -> None:
        self.handles[BIN_FULL] = self.notification_app.notify(
            kind='repeat',
            level='home',
            title="Pedro voll!",
            message="Pedro muss geleert werden",
            targets=self.notifications['targets'],
            interval=self.notifications['interval'])
        self.log("Abfalleimer voll! Benachrichtige zum Leeren.")

    def bin_emptied(self, entity: Union[str, dict], attribute: str, 
                    old: str, new: str, kwargs: dict) -> None:
        if BIN_FULL in self.handles:
            self.handles.pop(BIN_FULL)()
            self.log("Abfalleimer geleert! Schalte Benachrichtigung aus")

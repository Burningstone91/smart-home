from enum import Enum
from typing import Union

from appbase import AppBase
from house_config import HOUSE, PERSONS

##############################################################################
# App to set input_selects for all persons in the house and the house itself
# based on presence status
##############################################################################


class PresenceAutomation(AppBase):
    class PresenceState(Enum):
        home = 'zu Hause'
        just_arrived = 'gerade angekommen'
        just_left = 'gerade gegangen'
        away = 'weg'
        extended_away = 'lange weg'

    class HouseState(Enum):
        someone = 'Jemand ist zu Hause'
        everyone = 'Alle sind zu Hause'
        noone = 'Niemand ist zu Hause'
        vacation = 'Ferien'

    def initialize(self) -> None:
        super().initialize()
        for person, attribute in PERSONS.items():
            # set initial state
            if self.get_state(attribute['keys']) == 'not_home':
                self.select_option(
                    attribute['presence_state'],
                    self.PresenceState.away.value)
            else:
                self.select_option(
                    attribute['presence_state'],
                    self.PresenceState.home.value)

            # away/extented away to just arrived
            self.listen_state(
                self.set_presence_person,
                attribute['keys'],
                old='not_home',
                input_select=attribute['presence_state'],
                person=person,
                target_state=self.PresenceState.just_arrived.value)

            # home to just left
            self.listen_state(
                self.set_presence_person,
                attribute['keys'],
                new='not_home',
                input_select=attribute['presence_state'],
                person=person,
                target_state=self.PresenceState.just_left.value)

            # just arrived to home
            self.listen_state(
                self.set_presence_person,
                attribute['presence_state'],
                new=self.PresenceState.just_arrived.value,
                duration=60 * 5,
                input_select=attribute['presence_state'],
                person=person,
                target_state=self.PresenceState.home.value)

            # just left to just arrived = home
            self.listen_state(
                self.set_presence_person,
                attribute['presence_state'],
                old=self.PresenceState.just_left.value,
                new=self.PresenceState.just_arrived.value,
                input_select=attribute['presence_state'],
                person=person,
                target_state=self.PresenceState.home.value)

            # just left to away
            self.listen_state(
                self.set_presence_person,
                attribute['presence_state'],
                new=self.PresenceState.just_left.value,
                duration=60 * 5,
                input_select=attribute['presence_state'],
                person=person,
                target_state=self.PresenceState.away.value)

            # away to extended away
            self.listen_state(
                self.set_presence_person,
                attribute['presence_state'],
                new=self.PresenceState.away.value,
                duration=60 * 60 * 24,
                input_select=attribute['presence_state'],
                person=person,
                target_state=self.PresenceState.extended_away.value)

            # listen state to trigger house state change
            self.listen_state(
                self.set_presence_house, attribute['presence_state'])

    def set_presence_person(self, entity: Union[str, dict], attribute: str,
                            old: str, new: str, kwargs: dict) -> None:
        old_state = self.get_state(kwargs['input_select'])
        self.select_option(kwargs['input_select'], kwargs['target_state'])
        self.log(
            "{} war {}, ist jetzt {} ".format(
                kwargs['person'], old_state, kwargs['target_state']))

    def set_presence_house(self, entity: Union[str, dict], attribute: str,
                           old: str, new: str, kwargs: dict) -> None:
        if self.who_in_state(
                self.PresenceState.home,
                self.PresenceState.just_arrived) == list(PERSONS.keys()):
            self.set_house_input_select(self.HouseState.everyone.value)
        elif self.who_in_state(
                self.PresenceState.extended_away) == list(PERSONS.keys()):
            self.set_house_input_select(self.HouseState.vacation.value)
        elif self.who_in_state(
                self.PresenceState.away,
                self.PresenceState.just_left,
                self.PresenceState.extended_away) == list(PERSONS.keys()):
            self.set_house_input_select(self.HouseState.noone.value)
        else:
            self.set_house_input_select(self.HouseState.someone.value)

    def set_house_input_select(self, new_state: str) -> None:
        old_state = self.get_state(HOUSE['presence_state'])
        if not old_state == new_state:
            self.select_option(HOUSE['presence_state'], new_state)
            self.log("Vorher: {}, Jetzt: {}".format(old_state, new_state))

    def who_in_state(self, *presence_states: Enum) -> list:
        presence_state_list = [presence_state.value
                               for presence_state in presence_states]
        return [
            person for person, attribute in PERSONS.items() if self.get_state(
                attribute['presence_state']) in presence_state_list
        ]

    @property
    def noone_home(self) -> bool:
        return not self.who_in_state(self.PresenceState.home,
                                     self.PresenceState.just_arrived)

    @property
    def persons_home(self) -> list:
        return self.who_in_state(self.PresenceState.home,
                                 self.PresenceState.just_arrived)

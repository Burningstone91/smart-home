"""Define automations for presence."""

from enum import Enum
from typing import Union

from appbase import AppBase
from constants import NOT_HOME, PERSON
from house_config import HOUSE, PERSONS


##############################################################################
# App to set input_selects for all persons in the house and the house itself
# based on presence status
##############################################################################


KEYS = 'keys'
PRESENCE_STATE = 'presence_state'

INPUT_SELECT = 'input_select'
TARGET_STATE = 'target_state'


class PresenceAutomation(AppBase):
    """Define a base feature for presence automations."""

    class PresenceState(Enum):
        """Define an enum for person related presence states."""

        home = 'zu Hause'
        just_arrived = 'gerade angekommen'
        just_left = 'gerade gegangen'
        away = 'weg'
        extended_away = 'lange weg'

    class HouseState(Enum):
        """Define an enum for house related presence states."""

        someone = 'Jemand ist zu Hause'
        everyone = 'Alle sind zu Hause'
        noone = 'Niemand ist zu Hause'
        vacation = 'Ferien'

    def configure(self) -> None:
        """Configure."""
        for person, attribute in PERSONS.items():
            # set initial state
            if self.get_state(attribute[KEYS]) == NOT_HOME:
                self.select_option(
                    attribute[PRESENCE_STATE],
                    self.PresenceState.away.value)
            else:
                self.select_option(
                    attribute[PRESENCE_STATE],
                    self.PresenceState.home.value)

            # away/extented away to just arrived
            self.listen_state(
                self.set_presence_person,
                attribute[KEYS],
                old=NOT_HOME,
                input_select=attribute[PRESENCE_STATE],
                person=person,
                target_state=self.PresenceState.just_arrived.value)

            # home to just left
            self.listen_state(
                self.set_presence_person,
                attribute[KEYS],
                new=NOT_HOME,
                input_select=attribute[PRESENCE_STATE],
                person=person,
                target_state=self.PresenceState.just_left.value)

            # just arrived to home
            self.listen_state(
                self.set_presence_person,
                attribute[PRESENCE_STATE],
                new=self.PresenceState.just_arrived.value,
                duration=60 * 5,
                input_select=attribute[PRESENCE_STATE],
                person=person,
                target_state=self.PresenceState.home.value)

            # just left to just arrived = home
            self.listen_state(
                self.set_presence_person,
                attribute[PRESENCE_STATE],
                old=self.PresenceState.just_left.value,
                new=self.PresenceState.just_arrived.value,
                input_select=attribute[PRESENCE_STATE],
                person=person,
                target_state=self.PresenceState.home.value)

            # just left to away
            self.listen_state(
                self.set_presence_person,
                attribute[PRESENCE_STATE],
                new=self.PresenceState.just_left.value,
                duration=60 * 5,
                input_select=attribute[PRESENCE_STATE],
                person=person,
                target_state=self.PresenceState.away.value)

            # away to extended away
            self.listen_state(
                self.set_presence_person,
                attribute[PRESENCE_STATE],
                new=self.PresenceState.away.value,
                duration=60 * 60 * 24,
                input_select=attribute[PRESENCE_STATE],
                person=person,
                target_state=self.PresenceState.extended_away.value)

            # listen state to trigger house state change
            self.listen_state(
                self.set_presence_house,
                attribute[PRESENCE_STATE])

    def set_presence_person(self, entity: Union[str, dict], attribute: str,
                            old: str, new: str, kwargs: dict) -> None:
        """Set the presence input select for the
           specified person based on the given state"""
        old_state = self.get_state(kwargs[INPUT_SELECT])
        self.select_option(kwargs[INPUT_SELECT], kwargs[TARGET_STATE])
        self.log(f"{kwargs[PERSON]} war {old_state}, "
                 f"ist jetzt {kwargs[TARGET_STATE]}")

    def set_presence_house(self, entity: Union[str, dict], attribute: str,
                           old: str, new: str, kwargs: dict) -> None:
        """Set the presence for the house."""
        if self.everyone_home:
            self.set_house_input_select(self.HouseState.everyone.value)
        elif self.everyone_vacation:
            self.set_house_input_select(self.HouseState.vacation.value)
        elif self.noone_home:
            self.set_house_input_select(self.HouseState.noone.value)
        else:
            self.set_house_input_select(self.HouseState.someone.value)

    def set_house_input_select(self, new_state: str) -> None:
        """Set the presence input select for the house."""
        old_state = self.house_presence_state
        if not old_state == new_state:
            self.select_option(HOUSE[PRESENCE_STATE], new_state)
            self.log("Vorher: {}, Jetzt: {}".format(old_state, new_state))

    def who_in_state(self, *presence_states: Enum) -> list:
        """Return list of person in given state."""
        presence_state_list = [presence_state.value
                               for presence_state in presence_states]
        return [
            person for person, attribute in PERSONS.items() if self.get_state(
                attribute[PRESENCE_STATE]) in presence_state_list
        ]

    @property
    def house_presence_state(self):
        return self.get_state(HOUSE[PRESENCE_STATE])

    @property
    def everyone_home(self) -> bool:
        """Return true if everyone is home."""
        return self.persons_home == list(PERSONS.keys())

    @property
    def someone_home(self) -> bool:
        """Return true if someone is home."""
        return not (not self.persons_home)

    @property
    def noone_home(self) -> bool:
        """Return true if noone is home."""
        return not self.persons_home

    @property
    def everyone_vacation(self):
        """Return true if everyone is on vacation."""
        return self.who_in_state(
            self.PresenceState.extended_away) == list(PERSONS.keys())

    @property
    def persons_home(self) -> list:
        """Return list of persons home."""
        return self.who_in_state(
            self.PresenceState.home,
            self.PresenceState.just_arrived)

"""Define automations for presence."""
from enum import Enum
from typing import Union
import voluptuous as vol

from appbase import AppBase
from house import HOUSE
from persons import PERSONS
from helpers import voluptuous_helper as vol_help


class PresenceAutomation(AppBase):
    """Define a base feature for presence automations."""

    class PresenceStates(Enum):
        """Define an enum for person related presence states."""

        home = "zu Hause"
        just_arrived = "gerade angekommen"
        just_left = "gerade gegangen"
        away = "weg"
        extended_away = "lange weg"

    class HouseStates(Enum):
        """Define an enum for house related presence states."""

        someone = "Jemand ist zu Hause"
        everyone = "Alle sind zu Hause"
        noone = "Niemand ist zu Hause"
        vacation = "Ferien"

    def configure(self) -> None:
        """Configure."""
        self.house_state = HOUSE["presence_state"]
        for person, attribute in PERSONS.items():
            # set initial state
            if self.hass.get_state(attribute["keys"]) == "not_home":
                self.hass.select_option(
                    attribute["presence_state"], self.PresenceStates.away.value
                )
            else:
                self.hass.select_option(
                    attribute["presence_state"], self.PresenceStates.home.value
                )

            # away/extented away to just arrived/home
            self.hass.listen_state(
                self.set_presence_person,
                attribute["keys"],
                old="not_home",
                input_select=attribute["presence_state"],
                person=person,
                target_state=self.PresenceStates.just_arrived.value,
            )

            # home to just left
            self.hass.listen_state(
                self.set_presence_person,
                attribute["keys"],
                new="not_home",
                input_select=attribute["presence_state"],
                person=person,
                target_state=self.PresenceStates.just_left.value,
            )

            # just arrived to home
            self.hass.listen_state(
                self.set_presence_person,
                attribute["presence_state"],
                new=self.PresenceStates.just_arrived.value,
                duration=60 * 5,
                input_select=attribute["presence_state"],
                person=person,
                target_state=self.PresenceStates.home.value,
            )

            # just left to away
            self.hass.listen_state(
                self.set_presence_person,
                attribute["presence_state"],
                new=self.PresenceStates.just_left.value,
                duration=60 * 5,
                input_select=attribute["presence_state"],
                person=person,
                target_state=self.PresenceStates.away.value,
            )

            # away to extended away
            self.hass.listen_state(
                self.set_presence_person,
                attribute["presence_state"],
                new=self.PresenceStates.away.value,
                duration=60 * 60 * 24,
                input_select=attribute["presence_state"],
                person=person,
                target_state=self.PresenceStates.extended_away.value,
            )

            # house state
            self.hass.listen_state(
                self.set_presence_house, attribute["presence_state"],
            )

        self.set_house_input_select()

    def set_presence_person(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        """Set the presence input select for the person and the house."""
        self.adbase.log("test")
        old_state = self.hass.get_state(kwargs["input_select"])
        target_state = kwargs["target_state"]

        # just left to just arrived --> home
        if (
            old_state == self.PresenceStates.just_left.value
            and target_state == self.PresenceStates.just_arrived.value
        ):
            target_state = self.PresenceStates.home.value

        # update person device tracker via mqtt
        if "keys_topic" in PERSONS[kwargs["person"]]:
            if target_state in [
                self.PresenceStates.home.value,
                self.PresenceStates.just_arrived.value,
            ]:
                payload = "home"
            else:
                payload = "not_home"
            self.mqtt.mqtt_publish(
                PERSONS[kwargs["person"]]["keys_topic"], payload,
            )

        # set person input_select
        self.hass.select_option(kwargs["input_select"], target_state)
        self.adbase.log(f"{kwargs['person']} war {old_state}, ist jetzt {target_state}")

    def set_presence_house(
        self, entity: Union[str, dict], attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        self.set_house_input_select()

    def set_house_input_select(self) -> None:
        old_state = self.hass.get_state(self.house_state)
        target_state = self.house_presence_state
        if not old_state == target_state:
            self.hass.select_option(self.house_state, target_state.value)
            self.adbase.log(f"Vorher: {old_state}, Jetzt: {target_state.value}")

    @property
    def house_presence_state(self) -> "HouseState":
        """Return the presence state of the house."""
        if self.everyone_home:
            return self.HouseStates.everyone
        elif self.everyone_extended_away:
            return self.HouseStates.vacation
        elif self.noone_home:
            return self.HouseStates.noone
        else:
            return self.HouseStates.someone

    def house_in_state(self, house_states: Union[list, str]) -> bool:
        """Return True if house is in specified states."""
        return self.hass.get_state(self.house_state) in house_states.split(",")

    def who_in_state(self, *presence_states: Enum) -> list:
        """Return list of person in given state."""
        presence_state_list = [
            presence_state.value for presence_state in presence_states
        ]
        return [
            person
            for person, attribute in PERSONS.items()
            if self.hass.get_state(attribute["presence_state"]) in presence_state_list
        ]

    @property
    def persons_home(self) -> list:
        """Return list of persons home."""
        return self.who_in_state(
            self.PresenceStates.home, self.PresenceStates.just_arrived
        )

    @property
    def everyone_home(self) -> bool:
        """Return true if everyone is home."""
        return self.persons_home == list(PERSONS.keys())

    @property
    def someone_home(self) -> bool:
        """Return true if someone is home."""
        return len(self.persons_home) != 0

    @property
    def noone_home(self) -> bool:
        """Return true if noone is home."""
        return not self.persons_home

    @property
    def everyone_extended_away(self) -> bool:
        """Return true if everyone is extended away."""
        return self.who_in_state(self.PresenceStates.extended_away) == list(
            PERSONS.keys()
        )

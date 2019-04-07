from typing import Union

from appbase import AppBase
from house_config import HOUSE


##############################################################################
# example YAML
# turn_off_sleep_mode_forgot:
#   module: switches
#   class: ToggleAtTime
#   dependencies:
#     - presence_app
#   disabled_states:
#     presence: vacation
#   entities:
#     switch: input_boolean.sleep_mode
#   properties:
#     type:                        # toggle, scene or service_call
#     schedule_time: "13:30:00"    # only for class ToggleAtTime
#     specific_person: Dimitri     # optional for class ToggleOnArrival, if
#                                    if specified it will only trigger when
#                                    the specified person arrives alone
#     state: "off"                 # target state of the switch or the action
#                                    if a service should be called
#     target: light.office         # only for class ToggleOnStateChange,
#                                    specifies the entity that should be
#                                    monitored for state changes
#     target_state: "off"          # state of monitored entity on which the
#                                    the switch triggers
#     parameters:                  # optional, if specified it defines the
#                                    parameters for the service call
#       brightness: 250
#       transition: 2
#     button_config:               # only for class HueDimmerSwitch
#       short_press_on:
#         action_type: 'service_call'
#         action: 'turn_on'
#         entity: 'light.wohnzimmer'
#         parameters:
#           brightness: 250
#
##############################################################################


class SwitchBase(AppBase):
    def initialize(self) -> None:
        super().initialize()
        
        self.switch = self.entities['switch']
        self.action_type = self.properties.get('action_type')
        self.delay = self.properties.get('delay')
        self.state = self.properties.get('state')
        self.parameters = self.properties.get('parameters', {})

    def action(self, action_type: str, state: str,
               entity: str, **kwargs: dict) -> None:
        if action_type == 'toggle':
            if self.get_state(entity) == 'off' and state == 'on':
                self.turn_on(entity)
            elif self.get_state(entity) == 'on' and state == 'off':
                self.turn_off(entity)
        elif action_type == 'scene':
            self.turn_on(entity)
        else:
            self.call_service(
                f"{entity.split('.')[0]}/{state}",
                entity_id=entity,
                **kwargs
            )

    def action_on_schedule(self, kwargs: dict) -> None:
        self.action(
            kwargs['action_type'],
            kwargs['state'],
            kwargs['action_entity'],
            **kwargs.get('parameters')
        )

        
class ToggleOnStateChange(SwitchBase):
    def initialize(self) -> None:
        super().initialize()

        self.listen_state(
            self.state_change,
            self.entities['target'],
            new=self.properties['target_state'],
            constrain_app_enabled=1
        )

    def state_change(self, entity: Union[str, dict], attribute: str,
                     old: str, new: str, kwargs: dict) -> None:
        if self.delay:
            self.run_in(
                self.action_on_schedule,
                self.delay * 60,
                action_type=self.action_type,
                state=self.state,
                action_entity=self.switch,
                parameters=self.parameters
            )
        else:
            self.action(
                self.action_type,
                self.state,
                self.switch,
                **self.parameters
            )


class ToggleAtTime(SwitchBase):
    def initialize(self) -> None:
        super().initialize()

        self.run_daily(
            self.action_on_schedule,
            self.parse_time(self.properties['schedule_time']),
            action_type=self.action_type,
            state=self.state,
            action_entity=self.switch,
            parameters=self.parameters,
            constrain_app_enabled=1
        )


class ToggleOnArrival(SwitchBase):
    def initialize(self) -> None:
        super().initialize()
        self.person = self.properties.get('specific_person')

        self.listen_state(
            self.someone_arrived,
            HOUSE['presence_state'],
            constrain_app_enabled=1
        )

    def someone_arrived(self, entity: Union[str, dict], attribute: str,
                        old: str, new: str, kwargs: dict) -> None:
        someone_home_states = [self.presence_app.HouseState.someone.value,
                               self.presence_app.HouseState.everyone.value]
        if (new in someone_home_states) and (old not in someone_home_states):
            persons_home = self.presence_app.persons_home

            if ((self.person in persons_home and len(persons_home) == 1) or
                    not self.person):
                if self.delay:
                    self.run_in(
                        self.action_on_schedule,
                        self.delay * 60,
                        action_type=self.action_type,
                        state=self.state,
                        action_entity=self.switch,
                        parameters=self.parameters
                    )
                else:
                    self.action(
                        self.action_type,
                        self.state,
                        self.switch,
                        **self.parameters
                    )


class ToggleOnDeparture(SwitchBase):
    def initialize(self) -> None:
        super().initialize()

        self.listen_state(self.everyone_left,
                          HOUSE['presence_state'],
                          new=self.presence_app.HouseState.noone.value,
                          constrain_app_enabled=1)

    def everyone_left(self, entity: Union[str, dict], attribute: str,
                      old: str, new: str, kwargs: dict):
        if self.delay:
            self.run_in(
                self.action_on_schedule,
                self.delay * 60,
                action_type=self.action_type,
                state=self.state,
                action_entity=self.switch,
                parameters=self.parameters
            )
        else:
            self.action(
                self.action_type,
                self.state,
                self.switch,
                **self.parameters
            )


class HueDimmerSwitch(SwitchBase):
    def initialize(self) -> None:
        super().initialize()

        self.button_config = self.properties['button_config']
        self.button_map = {
            1002: 'short_press_on', 1003: 'long_press_on',
            2002: 'short_press_up', 2003: 'long_press_up',
            3002: 'short_press_down', 3003: 'long_press_down',
            4002: 'short_press_off', 4003: 'long_press_off'
        }

        # take action when button is pressed on dimmer switch
        self.listen_event(
            self.button_pressed,
            'deconz_event',
            id=self.switch,
            constrain_app_enabled=1
        )

    def button_name(self, button_code: int) -> Union[str, None]:
        try:
            return self.button_map[button_code]
        except KeyError:
            return None
        
    def button_pressed(self, event_name: str, data: dict,
                       kwargs: dict) -> None:
        button_code = data['event']
        button_name = self.button_name(button_code)

        if button_name in self.button_config:
            button_conf = self.button_config[button_name]
            action_type = button_conf['action_type']
            entity = button_conf['entity']
            action = button_conf.get('action')
            delay = button_conf.get('delay')
            parameters = button_conf.get('parameters', {})

            if action_type == 'dim':
                brightness = self.get_state(entity, attribute='brightness') or 0
                new_brightness = brightness - 25
                if new_brightness <= 0:
                    self.turn_off(entity)
                else:
                    self.turn_on(entity, brightness=new_brightness)
            elif action_type == 'brighten':
                brightness = self.get_state(entity, attribute='brightness') or 0
                new_brightness = brightness + 25
                if new_brightness > 255:
                    new_brightness = 255
                self.turn_on(entity, brightness=new_brightness)
            else:
                if delay:
                    self.run_in(
                        self.action_on_schedule,
                        delay * 60,
                        action_type=action_type,
                        state=action,
                        action_entity=entity,
                        parameters=parameters
                    )
                else:
                    self.action(
                        action_type,
                        action,
                        entity,
                        **parameters
                    )

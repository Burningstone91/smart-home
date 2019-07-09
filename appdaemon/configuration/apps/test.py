from appbase import AppBase


class TestClass(AppBase):

    def configure(self):
        # self.handle = self.run_in(self.pump_on, 5, entity_id="4", action="5")
        self.pump_on({"entity_id": "switch.schalter_entfeuchter", "action": 'off'})

    def pump_on(self, kwargs):

        action = kwargs.get('action')
        entity_id = kwargs.get('entity_id')
        state = self.get_state(kwargs['entity_id'])
        if state != action:
            if action == 'on':
                self.turn_on(entity_id)
            else:
                self.turn_off(entity_id)
            self.log('hier fehler')
            self.run_in(self.pump_on, 5, entity_id=entity_id, action=action)

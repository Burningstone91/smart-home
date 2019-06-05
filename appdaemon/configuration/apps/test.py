from appbase import AppBase


class TestClass(AppBase):

    def configure(self):
        self.handle = self.run_daily(self.pump_on, self.parse_time("21:13:00"))
        self.listen_state(self.pump_on, 'switch.schalter_entfeuchter', new='on')

    def pump_on(self, *args, **kwargs):
        self.log("module: __module__, function: __function__, MSG: Paused registered")
        for item, value in kwargs.items():
            self.log(item)
            self.log(value)
        for arg in args:
            self.log(arg)


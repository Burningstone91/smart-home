from appbase import AppBase
from house_config import MODES

SLEEP_TIMER = 'sleep_timer'


##############################################################################
# App to control sleep mode, controlled by a Hue Dimmer Switch
# Sleep mode: turn off all lights, send harmony command "Power Off",
# start a playlist on spotify in bedroom
# Hue Dimmer Switch:
#   On Button: Start sleep mode
#   Off Button: Stop music in x min
#   Off Button long press: Stop music
#   Dim - Button: Volume Down
#   Dim + Button: Volume Up
#
# args:
# entities:
#   hue_dimmer: Dimmer Switch entity_id, which controls sleep mode
#   media_player:
# properties:
#   delay: seconds for timer to stop music, default 1800
#   shutdown_time: time that music shuts down, default 02:00:00
#   sleep_playlist: spotify playlist to play in sleep mode
#   wakeup_playlist: spotify playlist to wake up
#   source: media player source if media player has multiple sources
#   turn_off_entities: entities to turn off when sleep starts, comma separated
##############################################################################


class SleepAutomation(AppBase):

    def initialize(self) -> None:
        super().initialize()
        self.delay = self.properties.get('delay', 1800)
        self.media_player = self.entities['media_player']
        self.sleep_playlist = self.properties['sleep_playlist']
        self.wakeup_playlist = self.properties['wakeup_playlist']
        self.wakeup_light = self.entities['wakeup_light'].split(',')
        self.source = self.properties['source']
        self.transition = self.properties['transition']

        shutdown_time = self.parse_time(self.properties.get('shutdown_time',
                                                            '02:00:00'))

        # timer to shutdown music at given time when I forgot to set timer
        self.run_daily(self.stop_music, shutdown_time, constrain_app_enabled=1)

        # activate scene based on button press on state of day
        if 'dimmer_switch' in self.entities:
            self.listen_event(self.activate_scene,
                              'deconz_event',
                              id=self.entities['dimmer_switch'],
                              constrain_app_enabled=1)
        else:
            self.log("Keine Fernbedienung konfiguriert")

    def activate_scene(self, event_name: str, data: dict,
                       kwargs: dict) -> None:
        button_event = data['event']
        # 10xx: on, 20xx: brighten, 30xx: dim, 40xx: off
        # xx03: long press release, xx02: short press release

        if button_event == 1002:
            if self.day_state == 'sleep':
                self.sleep_mode()
            else:
                self.wakeup_mode()
        elif button_event == 2003:
            self.media_player_app.volume_up(self.media_player)
        elif button_event == 2002:
            self.media_player_app.next_track(self.media_player)
        elif button_event == 3003:
            self.media_player_app.volume_down(self.media_player)
        elif button_event == 3002:
            self.media_player_app.previous_track(self.media_player)
        elif button_event == 4003:
            if self.day_state == 'sleep':
                self.handles[SLEEP_TIMER] = self.run_in(self.stop_music,
                                                        self.delay)
            else:
                self.stop_music()
        elif button_event == 4002:
            self.stop_music()
            self.turn_entities_off()

    def sleep_mode(self) -> None:
        self.turn_entities_off()
        self.media_player_app.play_media(
            self.media_player,
            self.sleep_playlist,
            self.source,
            volume=7,
            shuffle='true')
        self.log("Schlafmodus gestartet.")
        self.turn_on(MODES['sleep_mode'])

    def wakeup_mode(self) -> None:
        for light in self.wakeup_light:
            self.turn_on(light,
                         brightness=200,
                         color='orange',
                         transition=self.transition)
        self.media_player_app.play_media(
            self.media_player,
            self.wakeup_playlist,
            self.source,
            volume=7,
            shuffle='true')
        self.log("Aufwachmodus gestartet.")
        self.turn_off(MODES['sleep_mode'])

    def turn_entities_off(self) -> None:
        for entity in self.entities['turn_off_entities'].split(','):
            self.turn_off(entity)
        self.log("Alle Lichter und Geräte ausgeschaltet.")

    def stop_music(self, *args: list) -> None:
        if SLEEP_TIMER in self.handles:
            self.cancel_timer(self.handles[SLEEP_TIMER])
            self.handles.pop(SLEEP_TIMER)

        self.media_player_app.stop(self.media_player)
        self.log("Stoppe Musik")

    @property
    def day_state(self) -> str:
        if self.now_is_between(self.properties['sleep_time_start'],
                               self.properties['wakeup_time_start']):
            return 'sleep'
        else:
            return 'wakeup'

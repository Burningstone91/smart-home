from typing import Union

from appbase import AppBase


##############################################################################
# Supporting app that can be used by other apps to play media
#
# ARGS:
# yaml args:
# properties:
#   source: device that plays music
#   media_player: the media_player to use
#   volume: default 10
#   playlist: id of spotify playlist to play
##############################################################################


class MediaPlayerAutomation(AppBase):

    class MediaItem:
        def __init__(self, media_player, playlist, source, **kwargs):
            self.media_player = media_player
            self.playlist = playlist
            self.source = source

            self.volume = float(kwargs.get('volume', 0.1))
            self.source_entity = kwargs.get('source_entity')
            self.shuffle = kwargs.get('shuffle', 'false')

    def initialize(self) -> None:
        super().initialize()

    def play_media(self, media_player: str, playlist: str, source: str,
                   **kwargs: Union[None, dict]) -> None:
        mediaitem = self.MediaItem(
            media_player,
            playlist,
            source,
            volume=kwargs.get('volume'),
            shuffle=kwargs.get('shuffle')
        )

        self.set_source(mediaitem.media_player, mediaitem.source)
        self.set_volume(mediaitem.media_player, mediaitem.volume)
        self.start_playlist(mediaitem.media_player, mediaitem.playlist)
        if mediaitem.shuffle:
            self.shuffle(mediaitem.media_player)
            self.next_track(mediaitem.media_player)

    def set_source(self, media_player: str, source: str) -> None:
        self.call_service(
            'media_player/select_source',
            entity_id=media_player,
            source=source
        )

    def set_volume(self, media_player: str, volume: float) -> None:
        self.call_service(
            'media_player/volume_set',
            entity_id=media_player,
            volume_level=volume / 100
        )

    def start_playlist(self, media_player: str, playlist: str) -> None:
        self.call_service(
            'media_player/play_media',
            entity_id=media_player,
            media_content_type='playlist',
            media_content_id=playlist
        )

    def stop(self, media_player: str, **kwargs: Union[None, dict]) -> None:
        self.call_service(
            'media_player/media_pause', entity_id=media_player
        )
        if 'source_entity' in kwargs:
            self.turn_off(kwargs['source_entity'])

    def shuffle(self, media_player: str) -> None:
        self.call_service(
            'media_player/shuffle_set', 
            entity_id=media_player, 
            shuffle='true'
        )

    def next_track(self, media_player: str) -> None:
        self.call_service(
            'media_player/media_next_track', entity_id=media_player
        )

    def previous_track(self, media_player: str) -> None:
        self.call_service(
            'media_player/media_previous_track', entity_id=media_player
        )

    def volume_up(self, media_player: str) -> None:
        self.call_service('media_player/volume_up', entity_id=media_player)

    def volume_down(self, media_player: str) -> None:
        self.call_service('media_player/volume_down', entity_id=media_player)

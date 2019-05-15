"""Define automations for media players."""

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
#   playlist: id of Spotify playlist to play
##############################################################################


VOLUME = 'volume'
SHUFFLE = 'shuffle'
SOURCE_ENTITY = 'source_entity'


class MediaPlayerAutomation(AppBase):
    """Define a base feature for media player automations."""

    class MediaItem:  # pylint: disable=too-few-public-methods
        """Define a Media item."""

        def __init__(self, media_player, playlist, source, **kwargs) -> None:
            """"Initialize media item."""
            self.media_player = media_player
            self.playlist = playlist
            self.source = source

            self.volume = float(kwargs.get(VOLUME, 0.1))
            self.source_entity = kwargs.get(SOURCE_ENTITY)
            self.shuffle = kwargs.get(SHUFFLE)

    def play_media(self, media_player: str, playlist: str,
                   source: str, **kwargs: Union[None, dict]) -> None:
        """Play media."""
        media_item = self.MediaItem(
            media_player,
            playlist,
            source,
            volume=kwargs.get(VOLUME),
            shuffle=kwargs.get(SHUFFLE))

        self.set_source(media_item.media_player, media_item.source)
        self.set_volume(media_item.media_player, media_item.volume)
        self.start_playlist(media_item.media_player, media_item.playlist)
        if media_item.shuffle:
            self.shuffle(media_item.media_player)
            self.next_track(media_item.media_player)

    def set_source(self, media_player: str, source: str) -> None:
        """Set the media player source."""
        self.call_service(
            'media_player/select_source',
            entity_id=media_player,
            source=source)

    def set_volume(self, media_player: str, volume: float) -> None:
        """Set volume of the media player."""
        self.call_service(
            'media_player/volume_set',
            entity_id=media_player,
            volume_level=volume / 100)

    def start_playlist(self, media_player: str, playlist: str) -> None:
        """Start the playlist."""
        self.call_service(
            'media_player/play_media',
            entity_id=media_player,
            media_content_type='playlist',
            media_content_id=playlist)

    def stop(self, media_player: str, **kwargs: Union[None, dict]) -> None:
        """Stop the media player."""
        self.call_service('media_player/media_pause', entity_id=media_player)
        if SOURCE_ENTITY in kwargs:
            self.turn_off(kwargs['source_entity'])

    def shuffle(self, media_player: str) -> None:
        """Enables shuffle."""
        self.call_service(
            'media_player/shuffle_set',
            entity_id=media_player,
            shuffle='true')

    def next_track(self, media_player: str) -> None:
        """Play next track."""
        self.call_service(
            'media_player/media_next_track', entity_id=media_player
        )

    def previous_track(self, media_player: str) -> None:
        """Play previous track."""
        self.call_service(
            'media_player/media_previous_track', entity_id=media_player
        )

    def volume_up(self, media_player: str) -> None:
        """Increase volume."""
        self.call_service('media_player/volume_up', entity_id=media_player)

    def volume_down(self, media_player: str) -> None:
        """Decrease volume."""
        self.call_service('media_player/volume_down', entity_id=media_player)

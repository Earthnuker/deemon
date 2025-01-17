from pathlib import Path

from deezer import Deezer
from deezer.api import APIError
from deezer.utils import map_user_playlist
from deezer.gw import GWAPIError, LyricsStatus
from deemix import generateDownloadObject
from deemix.types.DownloadObjects import Single, Collection
from deemix.downloader import Downloader
from deemix.settings import load as loadSettings
from deemon.app import Deemon
import deemix.utils.localpaths as localpaths
import logging

logger = logging.getLogger(__name__)


class DeemixInterface:
    def __init__(self, download_path, config_dir):
        super().__init__()
        logger.debug("Initializing deemix library")
        self.dz = Deezer()
        self.download_path = download_path
        self.config_dir = config_dir

        if self.config_dir == "":
            self.config_dir = localpaths.getConfigFolder()
        else:
            self.config_dir = Path(self.config_dir)

        self.dx_settings = loadSettings(self.config_dir)

        if self.download_path != "":
            self.download_path = Path(self.download_path)
            self.dx_settings['downloadLocation'] = str(self.download_path)

        logger.debug(f"deemix Config Path: {self.config_dir}")
        logger.debug(f"deemix Download Path: {self.dx_settings['downloadLocation']}")


    def download_url(self, url, bitrate):
        links = []
        for link in url:
            if ';' in link:
                for l in link.split(";"):
                    links.append(l)
            else:
                links.append(link)
        for link in links:
            download_object = generateDownloadObject(self.dz, link, bitrate)
            if isinstance(download_object, list):
                for obj in download_object:
                    Downloader(self.dz, obj, self.dx_settings).start()
            else:
                Downloader(self.dz, download_object, self.dx_settings).start()

    def login(self):
        logger.info("Verifying ARL is valid, please wait...")
        if self.config_dir.is_dir():
            if Path(self.config_dir / '.arl').is_file():
                with open(self.config_dir / '.arl', 'r') as f:
                    arl = f.readline().rstrip("\n")
                    logger.debug(f"ARL found: {arl}")
                if not self.dz.login_via_arl(arl):
                    logger.error(f"ARL is expired or invalid")
                    return False
            else:
                logger.error(f"ARL not found in {self.config_dir}")
                return False
        else:
            logger.error(f"ARL directory {self.config_dir} was not found")
            return False
        return True

    def generatePlaylistItem(self, link_id, bitrate, playlistAPI=None, playlistTracksAPI=None):
        if not playlistAPI:
            if not str(link_id).isdecimal(): raise InvalidID(f"https://deezer.com/playlist/{link_id}")
            # Get essential playlist info
            try:
                playlistAPI = self.dz.api.get_playlist(link_id)
            except APIError:
                playlistAPI = None
            # Fallback to gw api if the playlist is private
            if not playlistAPI:
                try:
                    userPlaylist = self.dz.gw.get_playlist_page(link_id)
                    playlistAPI = map_user_playlist(userPlaylist['DATA'])
                except GWAPIError as e:
                    raise GenerationError(f"https://deezer.com/playlist/{link_id}", str(e)) from e

            # Check if private playlist and owner
            if not playlistAPI.get('public', False) and playlistAPI['creator']['id'] != str(self.dz.current_user['id']):
                logger.warning("You can't download others private playlists.")
                raise NotYourPrivatePlaylist(f"https://deezer.com/playlist/{link_id}")

        if not playlistTracksAPI:
            playlistTracksAPI = self.dz.gw.get_playlist_tracks(link_id)
        playlistAPI['various_artist'] = self.dz.api.get_artist(5080)  # Useful for save as compilation

        totalSize = len(playlistTracksAPI)
        playlistAPI['nb_tracks'] = totalSize
        collection = []
        dn = Deemon()
        for pos, trackAPI in enumerate(playlistTracksAPI, start=1):
            # Check if release has been seen already and skip it
            vals = {'track_id': trackAPI['SNG_ID'], 'playlist_id': id}
            sql = "SELECT * FROM 'playlist_tracks' WHERE track_id = :track_id AND playlist_id = :playlist_id"
            result = dn.db.query(sql, vals).fetchone()
            if result:
                continue
            if trackAPI.get('EXPLICIT_TRACK_CONTENT', {}).get('EXPLICIT_LYRICS_STATUS', LyricsStatus.UNKNOWN) in [
                LyricsStatus.EXPLICIT, LyricsStatus.PARTIALLY_EXPLICIT]:
                playlistAPI['explicit'] = True
            trackAPI['POSITION'] = pos
            trackAPI['SIZE'] = totalSize
            collection.append(trackAPI)

        if 'explicit' not in playlistAPI: playlistAPI['explicit'] = False

        return Collection({
            'type': 'playlist',
            'id': link_id,
            'bitrate': bitrate,
            'title': playlistAPI['title'],
            'artist': playlistAPI['creator']['name'],
            'cover': playlistAPI['picture_small'][:-24] + '/75x75-000000-80-0-0.jpg',
            'explicit': playlistAPI['explicit'],
            'size': totalSize,
            'collection': {
                'tracks_gw': collection,
                'playlistAPI': playlistAPI
            }
        })


class GenerationError(Exception):
    def __init__(self, link, message, errid=None):
        super().__init__()
        self.link = link
        self.message = message
        self.errid = errid

    def toDict(self):
        return {
            'link': self.link,
            'error': self.message,
            'errid': self.errid
        }


class InvalidID(GenerationError):
    def __init__(self, link):
        super().__init__(link, "Link ID is invalid!", "invalidID")


class NotYourPrivatePlaylist(GenerationError):
    def __init__(self, link):
        super().__init__(link, "You can't download others private playlists.", "notYourPrivatePlaylist")
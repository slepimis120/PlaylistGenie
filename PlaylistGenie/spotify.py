import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials

client_id = "f491929c43934c9487efb95c557b55c9"
client_secret = "d34016d53bda4f89b0b448759c66e1c9"
redirect_uri = "3000"

sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))

popular_playlists = sp.featured_playlists(country="US", limit=50)["playlists"]["items"]


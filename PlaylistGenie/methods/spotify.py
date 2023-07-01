import spotipy
from spotipy.oauth2 import SpotifyOAuth

#User ID: 9w5c1jwp91zo38q1ureemynxe

client_id = "f491929c43934c9487efb95c557b55c9"
client_secret = "d34016d53bda4f89b0b448759c66e1c9"
redirect_uri = "http://localhost:3000"

def authorize_user():
    scope = "playlist-read-private"
    print("A1")
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope,client_id=client_id,client_secret=client_secret,redirect_uri=redirect_uri))
    print("A2")
    results = sp.current_user_playlists(limit=50)
    print("AAAAA")
    for i, item in enumerate(results['items']):
        print("%d %s" % (i, item['name']))





#sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
#popular_playlists = sp.featured_playlists(country="US", limit=50)["playlists"]["items"]






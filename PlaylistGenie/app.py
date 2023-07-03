import base64
import time
import urllib
from os.path import exists
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from keras.models import Model
from keras.layers import Input, Dense

import spotipy
from flask import Flask, render_template, redirect, request, session, url_for
import PlaylistGenie.methods.spotify as spotify

app = Flask(__name__)


app.secret_key = 'd53bda4f89b0b448759c66e1c9'
app.config['SESSION_COOKIE_NAME'] = 'spotify-login-session'

client_id = "f491929c43934c9487efb95c557b55c9"
client_secret = "d34016d53bda4f89b0b448759c66e1c9"
redirect_uri = "http://localhost:3000"
scope = "playlist-read-private"

songs=[]


@app.route("/")
def index():
    if(exists(".cache")):
        return redirect("/getPlaylists")
    else:
        return render_template("main.html")


@app.route('/login')
def login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route('/authorize')
def authorize():
    sp_oauth = create_spotify_oauth()
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect("/getPlaylists")

@app.route('/autoencoder')
def autoencoder():
    return render_template("main.html")

@app.route('/logout')
def logout():
    for key in list(session.keys()):
        session.pop(key)
    return redirect('/')


@app.route('/getPlaylists')
def get_user_playlists():
    session['token_info'], authorized = get_token()
    session.modified = True
    if not authorized:
        return redirect('/')
    my_playlists = get_nonempty_playlists()
    #load_database(my_playlists[0])
    return render_template("home.html", playlists=my_playlists)


def get_nonempty_playlists():
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    my_playlists = sp.current_user_playlists(limit=50)['items']
    new_playlists = []
    for playlist in my_playlists:
        playlistitem = sp.playlist_items(playlist.get("id"))
        count = 0
        for item in playlistitem.get("items"):
            if not item.get("is_local"):
                count += 1
        if count > 0:
            new_playlists.append(playlist)
    return new_playlists


def load_database(playlist):
    global songs
    tracks=get_artists_tracks(playlist)
    songs=get_features(tracks)


def get_artists_tracks(playlist):
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    playlists = sp.current_user_playlists(limit=50)['items']
    all_tracks = []
    tracks = sp.playlist_items(playlist['id'])
    for track in tracks['items']:
        if track.get("is_local") == False:
            artist_tracks = sp.artist_top_tracks(track['track']['artists'][0]['id'], country='US')
            for t in artist_tracks['tracks']:
                all_tracks.append(t['id'])
    return all_tracks


def get_features(tracks):
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    features=[]
    for track in tracks:
        track_features = sp.audio_features(track)
        features.append({"track_id":track,"features":track_features[0]})
    for feature in features:
        print(feature)
    return features


def get_token():
    token_valid = False
    token_info = session.get("token_info", {})

    if not (session.get('token_info', False)):
        token_valid = False
        return token_info, token_valid

    now = int(time.time())
    is_token_expired = session.get('token_info').get('expires_at') - now < 60

    if is_token_expired:
        sp_oauth = create_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(session.get('token_info').get('refresh_token'))

    token_valid = True
    return token_info, token_valid


def create_spotify_oauth():
    return spotipy.SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=url_for('authorize', _external=True),
        scope=scope)

def encoder():


    # Convert song_data to a feature matrix
    song_ids = []
    song_features = []
    for song_dict in songs:
        song_ids.append(list(song_dict.keys())[0])
        song_features.append(list(song_dict.values())[0])

    song_features = np.array(song_features)

    # Normalize the feature matrix
    normalized_song_features = (song_features - np.mean(song_features, axis=0)) / np.std(song_features, axis=0)

    # Define the dimensions of the autoencoder
    input_dim = normalized_song_features.shape[1]
    encoding_dim = 64

    # Define the autoencoder model
    input_layer = Input(shape=(input_dim,))
    encoded = Dense(encoding_dim, activation='relu')(input_layer)
    decoded = Dense(input_dim, activation='linear')(encoded)

    autoencoder = Model(inputs=input_layer, outputs=decoded)
    autoencoder.compile(optimizer='adam', loss='mean_squared_error')

    # Train the autoencoder
    autoencoder.fit(normalized_song_features, normalized_song_features, epochs=50, batch_size=32, shuffle=True)

    # Extract the encoder part of the autoencoder
    encoder = Model(inputs=input_layer, outputs=encoded)

    # Calculate the embedding of the old playlist
    old_playlist_embedding = encoder.predict(songs)

    # Calculate the cosine similarity between the old playlist embedding and all songs
    similarities = cosine_similarity(old_playlist_embedding, normalized_song_features)

    # Sort the similarities in descending order
    sorted_indices = np.argsort(-similarities)

    # Get the top recommended songs
    top_recommendations = [song_ids[i] for i in sorted_indices[:10]]

    # Print the top recommended songs
    print("Top Recommended Songs:")
    for song_id in top_recommendations:
        print(song_id)


if __name__ == "__main__":
    app.run(host="localhost", port=3000)

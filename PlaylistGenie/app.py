import time
from os.path import exists
import numpy as np
import itertools
from sklearn.metrics.pairwise import cosine_similarity
from keras.models import Model
from keras.layers import Input, Dense

import spotipy
from flask import Flask, render_template, redirect, request, session, url_for

app = Flask(__name__)

app.secret_key = 'd53bda4f89b0b448759c66e1c9'
app.config['SESSION_COOKIE_NAME'] = 'spotify-login-session'

client_id = "d9e8ced8616446b29c5e55bc847168c3"
client_secret = "22e8c3ddf1ea49079ab253646db6539b"
redirect_uri = "http://localhost:3000"
scope = "playlist-read-private"

all_songs = []
chosen_playlist_songs = []
chosen_playlist = {}


@app.route("/")
def index():
    if (exists(".cache")):
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
    code = request.args.get('id')
    get_tracks_from_playlist(code)
    print("Loaded songs from the playlist...")
    load_database(chosen_playlist)
    print("Created a database...")
    encoder()
    return render_template("main.html")


@app.route('/logout')
def logout():
    for key in list(session.keys()):
        session.pop(key)
    return redirect('/')


@app.route('/getPlaylists')
def get_user_playlists():
    global chosen_playlist
    session['token_info'], authorized = get_token()
    session.modified = True
    if not authorized:
        return redirect('/')
    my_playlists = get_nonempty_playlists()
    return render_template("home.html", playlists=my_playlists)


# ----------------------------------------------------------------------------------------------------------------------

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


def get_tracks_from_playlist(playlist_id):
    global chosen_playlist
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    chosen_playlist = sp.playlist_items(playlist_id)


def load_database(playlist):
    global all_songs
    tracks = get_artists_tracks(playlist)
    all_songs = get_features(tracks)


# Get top 10 tracks from every artist on the playlist
def get_artists_tracks(playlist):
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    all_tracks = []
    for track in playlist['items']:
        if not track.get("is_local"):
            artist_tracks = sp.artist_top_tracks(track['track']['artists'][0]['id'], country='US')
            for t in artist_tracks['tracks']:
                all_tracks.append(t['id'])
    return all_tracks

# Get info about every song in the database
def get_features(tracks):
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    features = []
    for track in tracks:
        track_features = sp.audio_features(track)
        features.append({"track_id": track, "features": track_features[0]})
    return features


def get_chosen_playlist_features():
    global chosen_playlist
    tracks = []
    for track in chosen_playlist['items']:
        tracks.append(track['track']['id'])
    return get_features(tracks)


def get_token():
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
    global all_songs

    old_playlist_features = get_chosen_playlist_features()
    # Convert song_data to a feature matrix
    song_ids = []
    song_features = []
    for song_dict in old_playlist_features:
        song_features.append(dict(itertools.islice((list(song_dict.values())[1]).items(), 11)))

    # Features of songs from old playlist
    playlist_songs_features = np.array(song_features)

    # Features of all songs from database
    all_songs_features = []
    for song_dict in all_songs:
        all_songs_features.append(dict(itertools.islice((list(song_dict.values())[1]).items(), 11)))

    # Define the dimensions of the autoencoder
    print(song_features)
    print(all_songs_features)
    input_dim = len(song_features[0])
    encoding_dim = 4

    # Define the autoencoder model
    input_layer = Input(shape=(input_dim,))
    encoded = Dense(encoding_dim, activation='relu')(input_layer)
    decoded = Dense(input_dim, activation='linear')(encoded)

    autoencoder = Model(inputs=input_layer, outputs=decoded)
    autoencoder.compile(optimizer='adam', loss='mean_squared_error')

    # Train the autoencoder
    autoencoder.fit(song_features, song_features, epochs=50, batch_size=32, shuffle=True)

    # Extract the encoder part of the autoencoder
    encoder = Model(inputs=input_layer, outputs=encoded)

    # Calculate the embedding of the old playlist
    old_playlist_embedding = encoder.predict(song_features)

    # Calculate the cosine similarity between the old playlist embedding and all songs
    similarities = cosine_similarity(old_playlist_embedding, all_songs_features)

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

import time
from os.path import exists
import numpy as np
import itertools
import os
from sklearn.metrics.pairwise import cosine_similarity
from keras.models import Model
from keras.layers import Input, Dense
from PIL import Image
import requests
from io import BytesIO
import base64

import spotipy
from flask import Flask, render_template, redirect, request, session, url_for

app = Flask(__name__)

app.secret_key = 'd53bda4f89b0b448759c66e1c9'
app.config['SESSION_COOKIE_NAME'] = 'spotify-login-session'

client_id = "e8790382ecf54dcc90a37ccb9956b08a"
client_secret = "547e66f99a0a47cfba27f11db46861ae"
redirect_uri = "http://localhost:3000"
scope = "playlist-read-private playlist-modify-public playlist-modify-private ugc-image-upload"

user_id = ""
old_playlist_id = ""
old_playlist_img_url = ""
new_playlist_id = ""

all_songs = []
chosen_playlist_songs = []
chosen_playlist = {}
top_recommendations = []


@app.route("/")
def index():
    if exists(".cache"):
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
    global new_playlist_id, old_playlist_id
    old_playlist_id = request.args.get('id')
    get_tracks_from_playlist(old_playlist_id)
    print("Loaded songs from the playlist...")
    load_database(chosen_playlist)
    print("Created a database...")
    encoder()
    print("Database created!")
    print("Creating a playlist...")
    create_playlist()
    return render_template("generatedresult.html", playlist_id=new_playlist_id)


@app.route('/about')
def about():
    return render_template("about.html")

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
    global user_id
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    my_playlists = sp.current_user_playlists(limit=50)['items']
    user_id = sp.current_user().get("id")
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
    all_songs_unfiltered = get_features(tracks)
    print(len(all_songs_unfiltered))
    [all_songs.append(x) for x in all_songs_unfiltered if x not in all_songs]
    all_songs = [i for i in all_songs if i not in chosen_playlist_songs]
    print(len(all_songs))
    # get_random_songs()


def get_random_songs():
    global all_songs
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    track_ids = []
    tracks = sp.search(q='rock', type='track', limit=50)
    for t in tracks['tracks']['items']:
        track_ids.append(t['id'])
    song_features = get_features(track_ids)
    all_songs.extend(song_features)


# Get top 10 tracks from every artist on the playlist
def get_artists_tracks(playlist):
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    all_tracks = []
    all_artists = []
    for track in playlist['items']:
        if not track.get("is_local"):
            all_artists.append(track['track']['artists'][0]['id'])
            artist_tracks = sp.artist_top_tracks(track['track']['artists'][0]['id'], country='US')
            for t in artist_tracks['tracks']:
                all_tracks.append(t['id'])

    all_artists_filtered = []
    similar_artists_unfiltered = []
    similar_artists_filtered = []
    [all_artists_filtered.append(x) for x in all_artists if x not in all_artists_filtered]

    for artist in all_artists_filtered[:2]:
        similar_artists = sp.artist_related_artists(artist)
        for similar_artist in similar_artists.get("artists"):
            similar_artists_unfiltered.append(similar_artist.get("id"))

    print("Fetched similar artists...")

    [similar_artists_filtered.append(x) for x in similar_artists_unfiltered if x not in similar_artists_filtered]
    similar_artists_filtered = [i for i in similar_artists_filtered if i not in all_artists_filtered]

    print(len(similar_artists_filtered))

    for artist in similar_artists_filtered:
        artist_tracks = sp.artist_top_tracks(artist, country='US')
        for t in artist_tracks['tracks']:
            all_tracks.append(t['id'])

    # for track in playlist['items']:
    #     if not track.get("is_local"):
    #         albums = sp.artist_albums(track['track']['artists'][0]['id'], album_type=None, country=None, limit=20,
    #                                   offset=0)
    #         for album in albums['items']:
    #             tracks = sp.album_tracks(album.get("id"), limit=50, offset=0, market=None)
    #             for track_new in tracks.get("items"):
    #                 all_tracks.append(track_new['id'])

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
    global all_songs, top_recommendations

    old_playlist_features = get_chosen_playlist_features()

    song_features = []
    for song_dict in old_playlist_features:
        song_features.append(list(song_dict['features'].values())[0:11])
    song_features = np.array(song_features)

    normalized_song_features = (song_features - np.mean(song_features, axis=0)) / np.std(song_features, axis=0)

    all_songs_features = []
    for song_dict in all_songs:
        all_songs_features.append(list(song_dict['features'].values())[0:11])
    all_songs_features = np.array(all_songs_features)

    normalized_all_songs_features = (all_songs_features - np.mean(all_songs_features, axis=0)) / np.std(
        all_songs_features, axis=0)

    input_dim = len(song_features[0])
    encoding_dim = 4

    input_layer = Input(shape=(input_dim,))
    encoded = Dense(encoding_dim, activation='relu')(input_layer)
    decoded = Dense(input_dim, activation='linear')(encoded)

    autoencoder = Model(inputs=input_layer, outputs=decoded)
    autoencoder.compile(optimizer='adam', loss='mean_squared_error')

    autoencoder.fit(normalized_song_features, normalized_song_features, epochs=50,
                    batch_size=len(normalized_song_features), shuffle=True)

    encoder = Model(inputs=input_layer, outputs=encoded)

    old_playlist_embedding = encoder.predict(normalized_song_features)
    all_songs_embedding = encoder.predict(normalized_all_songs_features)

    similarities = cosine_similarity(old_playlist_embedding, all_songs_embedding)
    similarities = [sum(elements) for elements in zip(*similarities)]
    print(similarities)

    top_recommendation_index = [index for index, _ in
                                sorted(enumerate(similarities), key=lambda x: x[1], reverse=True)[:20]]

    for song_id in top_recommendation_index:
        sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))

        track_id = all_songs[song_id]['track_id']
        top_recommendations.append(sp.track(track_id))


def create_playlist():
    global user_id, new_playlist_id, old_playlist_id
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    playlist_name = sp.playlist(old_playlist_id).get("name") + " (DELUXE)"
    playlist = sp.user_playlist_create(user_id, playlist_name, public=True, collaborative=False, description='')
    new_playlist_id = playlist.get("id")

    create_artwork()

    with open("cover.png", "rb") as image_file:  # opening file safely
        image_64_encode = base64.b64encode(image_file.read())
    if len(image_64_encode) > 256000:  # check if image is too big
        print("Image is too big: ", len(image_64_encode))
    else:
        sp.playlist_upload_cover_image(new_playlist_id, image_64_encode)
        print("Image added.")

    new_song_list = []

    print(top_recommendations)

    for song in top_recommendations:
        new_song_list.append("https://open.spotify.com/track/" + song.get("id"))

    sp.playlist_add_items(new_playlist_id, new_song_list)


def create_artwork():
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    url = sp.playlist(old_playlist_id).get("images")[0].get("url")

    response = requests.get(url)
    im = Image.open(BytesIO(response.content))

    angle = 180
    out = im.rotate(angle)
    if exists("cover.png"):
        os.remove("cover.png")
        out.save('cover.png')
    else:
        out.save('cover.png')


if __name__ == "__main__":
    app.run(host="localhost", port=3000)

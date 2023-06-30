from flask import Flask, render_template
import PlaylistGenie.templates
import PlaylistGenie.spotify as spotify

app = Flask(__name__)


@app.route("/")
def index():

    return render_template("main.html", playlists=spotify.popular_playlists)


@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == "__main__":
    app.run(host="localhost", port=3000)

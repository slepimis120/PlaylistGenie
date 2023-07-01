from flask import Flask, render_template
import methods.spotify as spotify
import PlaylistGenie.methods.spotify as spotify

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("main.html")

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login')
def login():
    spotify.authorize_user()
    return render_template('about.html')

if __name__ == "__main__":
    app.run(host="localhost", port=3000)

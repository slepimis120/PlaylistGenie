from flask import Flask, render_template
import PlaylistGenie.templates

app = Flask(__name__)

@app.route('/')
def hello():
    return render_template('main.html')

if __name__ == "__main__":
    app.run(host="localhost", port=3000)
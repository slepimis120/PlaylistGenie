from flask import Flask, render_template
import PlaylistGenie.templates

app = Flask(__name__)

@app.route('/')
def main():
    return render_template('main.html')

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == "__main__":
    app.run(host="localhost", port=3000)
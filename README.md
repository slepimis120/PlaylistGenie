![PlaylistGenie](https://i.imgur.com/fCAk4Q5.jpg)


![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white) ![Spotify](https://img.shields.io/badge/Spotify-1ED760?style=for-the-badge&logo=spotify&logoColor=white)


# PlaylistGenie
PlaylistGenie project for "Computer Intelligence"

## Project goal
"PlaylistGenie", developed as our 3rd year college project, is a program used for class "Computer Intelligence" in 2023. 

The goal of this program is to generate a playlist of new songs, where songs from the old playlist are taken as input. Spotify regularly recommends "Sponsored songs" (about 20% of the time), so we designed a neural network that would handle recommendations instead of Spotify. 

All of the data used for the program was made possible with the Spotify API system.

## Installing / Getting started

To install this program, you're required to do two things.

1. CD into the folder where requirements.txt can be found and do:
   
```shell
pip install -r requirements.txt
```

2. Run the script itself

```shell
python app.py
```

After that, go to http://localhost:3000/ where you can use the program itself.

## Database

For the database, instead of having already set up one, we opted to generate the database "on the go". It takes artists from the playlists and artists similar to them, and gets their top 10 songs. That way, the base has around 10x more songs than the average playlist which should be enough for now.

## Neural Network

For the neural network, we opted for Autoencoder. Considering there isn't a right or wrong solution to this problem, we used Autoencoder to replicate the playlist as close as possible, and used that to find similar songs.

Loss function used for this was "Mean Squared Error". It was trained on 50 epochs. Similarity function we used afterwards was cosine similarity.

## Licence 

PlaylistGenie is available under the GNU GPLv3 license.

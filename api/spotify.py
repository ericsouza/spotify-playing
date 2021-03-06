from datetime import datetime, time, timedelta
import os
import json
import random
import requests
import pathlib

from base64 import b64encode
from dotenv import load_dotenv, find_dotenv
from flask import Flask, Response, jsonify, render_template

load_dotenv(find_dotenv())

# Spotify:
#   user-read-currently-playing
#   user-read-recently-played
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_SECRET_ID = os.getenv("SPOTIFY_SECRET_ID")
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")

SPOTIFY_URL_REFRESH_TOKEN = "https://accounts.spotify.com/api/token"
SPOTIFY_URL_NOW_PLAYING = "https://api.spotify.com/v1/me/player/currently-playing?additional_types=track%2Cepisode"
SPOTIFY_URL_RECENTLY_PLAY = (
    "https://api.spotify.com/v1/me/player/recently-played?limit=10"
)

app = Flask(__name__)


def getAuth():
    return b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_SECRET_ID}".encode()).decode(
        "ascii"
    )


def refreshToken():
    data = {
        "grant_type": "refresh_token",
        "refresh_token": SPOTIFY_REFRESH_TOKEN,
    }

    headers = {"Authorization": "Basic {}".format(getAuth())}

    response = requests.post(SPOTIFY_URL_REFRESH_TOKEN,
                             data=data, headers=headers)
    return response.json()["access_token"]


def recentlyPlayed():
    token = refreshToken()
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(SPOTIFY_URL_RECENTLY_PLAY, headers=headers)

    if response.status_code == 204:
        return {}

    return response.json()


def nowPlaying():
    token = refreshToken()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    response = requests.get(SPOTIFY_URL_NOW_PLAYING, headers=headers)

    if response.status_code == 204:
        return {}
    from pprint import pprint

    pprint(response.json())
    return response.json()


def barGen(barCount):
    barCSS = ""
    left = 1
    for i in range(1, barCount + 1):
        anim = random.randint(1000, 1350)
        barCSS += ".bar:nth-child({})  {{ left: {}px; animation-duration: {}ms; }}".format(
            i, left, anim
        )
        left += 4

    return barCSS


def load_no_music_image(choice):
    if choice == "sleeping":
        image_path = str(pathlib.Path().absolute()) + \
            "/api/static/sleeping.jpeg"
    else:
        image_path = str(pathlib.Path().absolute()) + "/api/static/coding.jpg"

    with open(image_path, "rb") as image_file:
        encoded_string = b64encode(image_file.read()).decode("ascii")
    return encoded_string


def is_time_between(begin_time, end_time, check_time=None):
    # If check time is not given, default to current UTC time
    check_time = check_time or (datetime.utcnow() - timedelta(hours=3)).time()
    if begin_time < end_time:
        return check_time >= begin_time and check_time <= end_time
    else:  # crosses midnight
        return check_time >= begin_time or check_time <= end_time


def loadImageB64(url):
    response = requests.get(url)
    return b64encode(response.content).decode("ascii")


def makeSVG(data):
    barCount = 84
    contentBar = "".join(["<div class='bar'></div>" for i in range(barCount)])
    barCSS = barGen(barCount)

    try:
        item = data["item"]
        currentStatus = "Vibing to:"
        try:
            image = loadImageB64(item["images"][1]["url"])
            artistName = item["show"]["name"].replace("&", "&amp;")
        except:
            image = loadImageB64(item["album"]["images"][1]["url"])
            artistName = item["artists"][0]["name"].replace("&", "&amp;")

        songName = item["name"].replace("&", "&amp;")

    except:
        contentBar = ""  # Shows/Hides the EQ bar if no song is currently playing
        currentStatus = "Last seen playing:"
        artistName = ""
        songName = "Nothing Playing"

        if is_time_between(time(22, 00), time(8, 00)):
            image = load_no_music_image("sleeping")
        else:
            image = load_no_music_image("coding")

    dataDict = {
        "contentBar": contentBar,
        "barCSS": barCSS,
        "artistName": artistName,
        "songName": songName,
        "image": image,
        "status": currentStatus,
    }

    return render_template("spotify.html.j2", **dataDict)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    data = nowPlaying()
    svg = makeSVG(data)

    resp = Response(svg, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "s-maxage=1"

    return resp


if __name__ == "__main__":
    app.run(debug=False)

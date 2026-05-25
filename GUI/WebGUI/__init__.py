from flask import Flask, render_template, Response, request, jsonify
from flaskwebgui import FlaskUI
from Eye import *
import json

app = Flask(__name__)

def IrisDisplay():
    display = Flask(__name__)
    @display.route('/')
    def index():
        return render_template("IrisDisplay.html")

    @display.route('/IrisDisplay')
    def IrisDisplay():
        data = json.load(open("config.json", "r"))
        return Response(data["iris"]["hex"])

    display.run(debug=True)

"""
!!! WIP !!!
"""

def WebApp(lang = "en"):
    iris: Iris = Iris(0, 0, 0, "#000")
    photoreceptor: Photoreceptor = Photoreceptor(True, True)
    lens: Lens = Lens(0)

    eye:Eye = Eye(iris, photoreceptor, lens)
    @app.route("/")
    def index():
        return render_template(f"App{lang.capitalize()}V.html")

    @app.route('/video_feed')
    def video_feed():
        return Response(eye.getImage(), mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.route("/config", methods=["POST"])
    def config():
        data = request.get_json()

        print(data)

        if (data.get("sticks") == "no"): eye.photoreceptor.sticks = True
        else: eye.photoreceptor.sticks = False
        if (data.get("cones") == "no"): eye.photoreceptor.cones = True
        else: eye.photoreceptor.sticks = False

        return jsonify()


    if __name__ == '__main__':
        app.run(debug=True)
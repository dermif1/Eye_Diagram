import os

from Eye import *
from cv2_enumerate_cameras import enumerate_cameras
from GUI import WebGUI
import tkinter as tk
from tkinter import colorchooser
import multiprocessing as mp
import json

def chooseCamera() -> int:
    listOfCameras = enumerate_cameras(cv2.CAP_ANY)

    window = tk.Tk()
    window.title("Choose camera")
    window.geometry("512x512")

    label = tk.Label(window, text="Choose camera", font=("Arial", 20))
    label.pack()

    listbox = tk.Listbox(window, height=6, selectmode=tk.SINGLE, width=250)
    listbox.pack(pady=20)

    response = tk.IntVar()

    for camera in listOfCameras:
        listbox.insert(tk.END, f"Name: {camera.name}")

    btn = tk.Button(
        window,
        text="Submit",
        command=lambda: (
            response.set(listOfCameras[listbox.curselection()[0]].index) if len(listbox.curselection()) > 0 else None,
            window.destroy()
        )
    )
    btn.pack(pady=10)
    window.mainloop()

    return response.get()

class TkinterGUI:
    def __init__(self):
        self.iris: Iris = Iris(0, 0, 0, "#000")
        self.photoreceptor: Photoreceptor = Photoreceptor(True, True)
        self.lens: Lens = Lens(0)

        self.eye: Eye = Eye(self.iris, self.photoreceptor, self.lens, chooseCamera(), debug=True)

        self.process = mp.Process(target=self.eye.getImage)
        self.process.start()

        self.window = tk.Tk()
        self.window.title("Eye diagram: Config")
        self.window.geometry("512x512")

        self.sticks = tk.BooleanVar(value=True)
        self.cones = tk.BooleanVar(value=True)

        frame1 = tk.Label(self.window, text="PHOTORECEPTOR", font=("Arial", 20))
        frame1.pack()
        labelSubHeader1_1 = tk.Checkbutton(self.window, text="Sticks", variable=self.sticks, command=self.photoreceptorSticksChanger, )
        labelSubHeader1_1.pack(pady=20)
        labelSubHeader1_2 = tk.Checkbutton(self.window, text="Cones", variable=self.cones, command=self.photoreceptorConesChanger, )
        labelSubHeader1_2.pack(pady=20)

        pick_button = tk.Button(self.window, text="Change Iris color", command=self.irisChanger, font=("Arial", 12))
        pick_button.pack(pady=20)

        frame2 = tk.LabelFrame(self.window, text="LENS")
        frame2.pack(pady=20)
        scale = tk.Scale(
            frame2,
            from_=-4.5,  # Мінімальне значення (важливо: з підкресленням)
            to=4.5,  # Максимальне значення
            orient="horizontal",  # Напрямок: HORIZONTAL або VERTICAL
            length=500,  # Довжина віджета в пікселях
            tickinterval=0.1,  # Крок міток під повзунком
            resolution=0.1,
            command=self.lensChanger
        )
        scale.set(20)
        scale.pack(pady=20)
        description = tk.Message(self.window, text="ametropia_diopters: Degree of vision impairment (0.0 — perfect, ‘-’ — myopia, ‘+’ — hyperopia).", font=("Arial", 12), width=350)
        description.pack()

    def irisChanger(self):
        colorCode = colorchooser.askcolor(title="New Iris color")
        if colorCode[0]:
            oldData = json.load(open("config.json", "r"))
            oldData["iris"]["r"] = colorCode[0][0]
            oldData["iris"]["g"] = colorCode[0][1]
            oldData["iris"]["b"] = colorCode[0][2]
            with open("config.json", "w") as outfile:
                json.dump(oldData, outfile)

        if colorCode[1]:
            oldData = json.load(open("config.json", "r"))
            oldData["iris"]["hex"] = colorCode[1]
            with open("config.json", "w") as outfile:
                json.dump(oldData, outfile)

    def lensChanger(self, ametropia_diopters):
        oldData = json.load(open("config.json", "r"))
        oldData["lens"]["ametropia_diopters"] = float(ametropia_diopters)
        with open("config.json", "w") as outfile:
            json.dump(oldData, outfile)

    def photoreceptorSticksChanger(self):
        oldData = json.load(open("config.json", "r"))
        oldData["photoreceptor"]["sticks"] = self.sticks.get()
        with open("config.json", "w") as outfile:
            json.dump(oldData, outfile)

    def photoreceptorConesChanger(self):
        oldData = json.load(open("config.json", "r"))
        oldData["photoreceptor"]["cones"] = self.cones.get()
        with open("config.json", "w") as outfile:
            json.dump(oldData, outfile)

    def run(self):
        print("Welcome to Eye diagram")
        self.window.mainloop()
        self.process.join()
        self.process.close()
        os.remove(os.path.abspath("config.json"))
        os.remove(os.path.abspath("config.old.json"))
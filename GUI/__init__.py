from GUI import TkinterGUI
import multiprocessing as mp

if __name__ == "__main__":
    mp.freeze_support()
    TkinterGUI.TkinterGUI().run()
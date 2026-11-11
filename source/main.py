import tkinter as tk

from source.classes.gui import StepModeGUI

if __name__ == "__main__":
    app_root = tk.Tk()
    gui = StepModeGUI(app_root)
    app_root.mainloop()

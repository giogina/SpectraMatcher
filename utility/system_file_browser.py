import tkinter as tk
from tkinter import filedialog, simpledialog
from tkinter import *

from screeninfo import get_monitors

from launcher import Launcher


def open_project_file_dialog(root_path="/"):  # TODO: Instead use https://github.com/hoffstadt/DearPyGui/wiki/Tools-and-Widgets file explorer (for multi selection, matching theme) (also in views/main_menu.py _open_file_dialog)
    root = tk.Tk()
    root.withdraw()  # Hides the tkinter root window
    file_path = filedialog.askopenfilename(
        initialdir=root_path,  # self.settings.get("projectsPath", "/"),
        title="Select project file",
        filetypes=[("SpectraMatcher Projects (.spm)", "*.spm*"), ("All Files", "*.*")]
    )
    root.destroy()
    return file_path


def data_dir_file_dialog(root_path="/"):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askdirectory(
        initialdir=root_path,
        title="Select data directory"
    )
    root.destroy()
    return file_path


def data_files_dialog(root_path="/"):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilenames(
        initialdir=root_path,
        title="Select data files",
        filetypes=[("All Files", "*.*"), ("Gaussian log files", "*.log"), ("Text files", "*.txt*")],
    )
    root.destroy()
    return file_path


def save_as_file_dialog(root_path="/"):
    root = tk.Tk()
    root.withdraw()  # Hides the tkinter root window
    file_path = filedialog.asksaveasfilename(
        initialdir=root_path,
        title="Save project as",
        filetypes=[("SpectraMatcher Project (.spm)", "*.spm*"), ("All Files", "*.*")],
        defaultextension=".spm",
    )
    root.destroy()
    return file_path


def inquire_close_unsaved(project_name: str, root_path="/"):
    """Returns "discard" or "save" or ("save as", file) """
    print("project save inquiry dialog....")
    monitor = get_monitors()[0]
    pos = (int((monitor.width-300)/2), int((monitor.height-200)/2))
    root = tk.Tk()
    root.geometry("+{}+{}".format(pos[0], pos[1]))  # Root does not move yet
    root.overrideredirect(1)
    root.withdraw()
    root.update_idletasks()
    root.withdraw()  # Hide the root window
    dialog = SaveChangesDialog(root, project_name)
    root.destroy()
    choice = dialog.user_choice  # Return the choice
    if choice == "save as":
        path = save_as_file_dialog(root_path)
        if path:
            return "save as", path
        else:
            return inquire_close_unsaved()  # try again
    else:
        return choice


class SaveChangesDialog(simpledialog.Dialog):
    def __init__(self, parent, name):
        self.user_choice = ""
        self.name = name
        super().__init__(parent, title="Save changes?")

    def body(self, master):
        tk.Label(master, text=f"\nWould you like to save changes to {self.name}?\n").pack()
        self.bring_to_front()
        return None  # Override if you need to return a specific widget

    def buttonbox(self):
        box = tk.Frame(self)

        save_button = tk.Button(box, text="Save", width=20, command=lambda: self.ok("save"), default=tk.ACTIVE)
        save_button.pack(side=tk.LEFT, padx=5, pady=5)
        save_as_button = tk.Button(box, text="Save As...", width=20, command=lambda: self.ok("save as"))
        save_as_button.pack(side=tk.LEFT, padx=5, pady=5)
        discard_button = tk.Button(box, text="Discard", width=20, command=lambda: self.ok("discard"))
        discard_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", lambda event, choice="save": self.ok(choice))

        box.pack()

    def ok(self, choice=None):
        self.user_choice = choice  # Store the user's choice
        super().ok()  # This will close the dialog

    def bring_to_front(self):
        self.after(100, lambda: Launcher.bring_window_to_front("Save changes?"))
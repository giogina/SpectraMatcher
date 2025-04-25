import subprocess
import sys
import textwrap
import tkinter as tk
from tkinter import filedialog, simpledialog

from screeninfo import get_monitors

from launcher import Launcher

def open_project_file_dialog(root_path="/"):
    try:
        return _open_project_file_dialog_subprocess(root_path)
    except Exception as e:  # Fallback (worked for Windows)
        _open_project_file_dialog_tk(root_path)

def _open_project_file_dialog_subprocess(initial_path="/"):
    code = textwrap.dedent(f"""
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            initialdir=r'{initial_path}',
            title="Select project file",
            filetypes=[("SpectraMatcher Projects (.smp)", "*.smp"), ("All Files", "*.*")]
        )
        if path:
            print(path)
    """)

    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    return result.stdout.strip() or None

def _open_project_file_dialog_tk(root_path="/"):
    root = tk.Tk()
    root.withdraw()  # Hides the tkinter root window
    file_path = filedialog.askopenfilename(
        initialdir=root_path,  # self.settings.get("projectsPath", "/"),
        title="Select project file",
        filetypes=[("SpectraMatcher Projects (.smp)", "*.smp*"), ("All Files", "*.*")]
    )
    root.destroy()
    return file_path


def data_dir_file_dialog(root_path="/"):
    try:
        return _data_dir_file_dialog_subprocess(root_path)
    except Exception as e:
        return _data_dir_file_dialog_tk(root_path)

def _data_dir_file_dialog_subprocess(initial_path="/"):
    code = textwrap.dedent(f"""
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askdirectory(
            initialdir=r'{initial_path}',
            title="Select data directory"
        )
        if path:
            print(path)
    """)

    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    return result.stdout.strip() or None

def _data_dir_file_dialog_tk(root_path="/"):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askdirectory(
        initialdir=root_path,
        title="Select data directory"
    )
    root.destroy()
    return file_path


def data_files_dialog(root_path="/"):
    try:
        return _data_files_dialog_subprocess(root_path)
    except Exception as e:
        return _data_files_dialog_tk(root_path)

def _data_files_dialog_subprocess(initial_path="/"):
    code = textwrap.dedent(f"""
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        paths = filedialog.askopenfilenames(
            initialdir=r'{initial_path}',
            title="Select data files",
            filetypes=[
                ("All Files", "*.*"),
                ("Gaussian log files", "*.log"),
                ("Text files", "*.txt*")
            ],
        )
        if paths:
            for path in paths:
                print(path)
    """)

    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    # Split multiple lines, strip empty results
    return [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]

def _data_files_dialog_tk(root_path="/"):
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
    try:
        return _save_as_file_dialog_subprocess(root_path)
    except Exception as e:
        print("Subprocess dialog failed, falling back:", e)
        return _save_as_file_dialog_tk(root_path)

def _save_as_file_dialog_subprocess(initial_path="/"):
    code = textwrap.dedent(f"""
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.asksaveasfilename(
            initialdir=r'{initial_path}',
            title="Save project as",
            filetypes=[("SpectraMatcher Project (.smp)", "*.smp*"), ("All Files", "*.*")],
            defaultextension=".smp"
        )
        if path:
            print(path)
    """)

    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    return result.stdout.strip() or None

def _save_as_file_dialog_tk(root_path="/"):
    root = tk.Tk()
    root.withdraw()  # Hides the tkinter root window
    file_path = filedialog.asksaveasfilename(
        initialdir=root_path,
        title="Save project as",
        filetypes=[("SpectraMatcher Project (.smp)", "*.smp*"), ("All Files", "*.*")],
        defaultextension=".smp",
    )
    root.destroy()
    return file_path

def inquire_close_unsaved(project_name: str, root_path="/"):
    """Returns "discard" or "save" or ("save as", file) """
    # print("Project save inquiry dialog....")
    monitor = get_monitors()[0]
    pos = (int((monitor.width-300)/2), int((monitor.height-200)/2))
    root = tk.Tk()
    root.geometry("+{}+{}".format(pos[0], pos[1]))  # Root does not move yet
    root.overrideredirect(1)
    root.withdraw()
    root.update_idletasks()
    root.withdraw()  # Hide the root window
    try:
        while True:
            dialog = SaveChangesDialog(root, project_name)
            choice = dialog.user_choice  # Return the choice
            if choice == "save as":
                path = save_as_file_dialog(root_path)
                if path:
                    return "save as", path
                else:
                    continue  # try again
            else:
                return choice
    finally:
        root.destroy()


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
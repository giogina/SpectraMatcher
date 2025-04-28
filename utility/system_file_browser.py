import subprocess
import textwrap
import tkinter as tk
from tkinter import filedialog, simpledialog
from tkinter import *
from screeninfo import get_monitors


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


def inquire_close_unsaved(project_name, root_path="/"):
    choice = save_or_discard_dialog(project_name)
    if choice == "save as":
        path = save_as_file_dialog(root_path)
        if path:
            return "save as", path
        else:
            return inquire_close_unsaved(project_name, root_path=root_path)  # try again
    elif choice not in ("save", "discard"):
        return "discard"
    else:
        return choice


def save_or_discard_dialog(project_name):
    monitor = get_monitors()[0]
    pos = (int((monitor.width - 300) / 2), int((monitor.height - 200) / 2))
    code = textwrap.dedent(f"""
        import tkinter as tk
        from tkinter import simpledialog

        class SaveDialog(simpledialog.Dialog):
            def body(self, master):
                self.result = "discard"
                tk.Label(master, text="Would you like to save changes to {project_name}?").pack(padx=10, pady=10)
            def buttonbox(self):
                box = tk.Frame(self)
                tk.Button(box, text="Save", width=10, command=lambda: self.ok("save")).pack(side=tk.LEFT, padx=5, pady=5)
                tk.Button(box, text="Save As...", width=10, command=lambda: self.ok("save as")).pack(side=tk.LEFT, padx=5, pady=5)
                tk.Button(box, text="Discard", width=10, command=lambda: self.ok("discard")).pack(side=tk.LEFT, padx=5, pady=5)
                box.pack()
            def ok(self, choice):
                self.result = choice
                self.destroy()

        root = tk.Tk()
        root.title("Save changes to {project_name}?")
        root.geometry("+{pos[0]}+{pos[1]}")
        root.withdraw()
        root.update_idletasks()
        dialog = SaveDialog(root)
        print(dialog.result)
    """)
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)  # possibly , timeout=200 - but unlikely to be necessary.
    return result.stdout.strip()


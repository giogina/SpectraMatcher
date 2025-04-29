import ast
import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, simpledialog
from tkinter import *
from screeninfo import get_monitors


def _run_in_subprocess(function, arg, timeout=180):
    executable = os.path.abspath(sys.argv[0])
    if executable.endswith('.py'):  # Python
        command = [sys.executable, executable, "-dialog", function, arg]
        print(f"{function}, calling py version: ", command)
    else:  # Compiled
        command = [executable, "-dialog", function, arg]
        print(f"{function}, calling exe version: ", command)

    if not os.path.isfile(command[0]):
        print(f"Executable not found: {command[0]}")
        return None
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Subprocess failed for {function} {arg} with return code {e.returncode}: {e.stderr}.\nAttempting fallback.")
        try:
            return run_directly(function, arg)
        except Exception as f:
            print(f"Fallback for {function} {arg} failed: {f}")
            return None
    except subprocess.TimeoutExpired:
        print(f"Subprocess timed out after {timeout} seconds.")
        return None


def run_directly(function, arg):
    result = ""
    if function == "open_project_file":
        result = _open_project_file_dialog_tk(arg)
    elif function == "open_directory_dialog":
        result = _data_dir_file_dialog_tk(arg)
    elif function == "open_files_dialog":
        result = _data_files_dialog_tk(arg)
    elif function == "save_as_file_dialog":
        result = _save_as_file_dialog_tk(arg)
    elif function == "inquire_close_unsaved":
        result = _inquire_close_unsaved_tk(arg)
    return result


def open_project_file_dialog(root_path=os.path.expanduser("~")):
    return _run_in_subprocess("open_project_file", root_path)


def _open_project_file_dialog_tk(root_path=os.path.expanduser("~")):  # DO NOT print anything here - that would mess with subprocess results.
    root = tk.Tk()
    root.withdraw()  # Hides the tkinter root window
    file_path = filedialog.askopenfilename(
        initialdir=root_path,
        title="Select project file",
        filetypes=[("SpectraMatcher Projects (.smp)", "*.smp*"), ("All Files", "*.*")]
    )
    root.destroy()
    return file_path


def data_dir_file_dialog(root_path=os.path.expanduser("~")):
    return _run_in_subprocess("open_directory_dialog", root_path)


def _data_dir_file_dialog_tk(root_path=os.path.expanduser("~")):   # DO NOT print anything here - that would mess with subprocess results.
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askdirectory(
        initialdir=root_path,
        title="Select data directory"
    )
    root.destroy()
    return file_path


def data_files_dialog(root_path=os.path.expanduser("~")):
    result = _run_in_subprocess("open_files_dialog", root_path)
    if type(result) != str:
        return []
    result = ast.literal_eval(result)
    print(f"Multi files: {type(result)}\n", result)
    if result is not None:
        return [line.strip() for line in result if line.strip() and os.path.exists(line.strip())]
    else:
        return []


def _data_files_dialog_tk(root_path=os.path.expanduser("~")):   # DO NOT print anything here - that would mess with subprocess results.
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilenames(
        initialdir=root_path,
        title="Select data files",
        filetypes=[("All Files", "*.*"), ("Gaussian log files", "*.log"), ("Text files", "*.txt*")],
    )
    root.destroy()
    return file_path


def save_as_file_dialog(root_path=os.path.expanduser("~")):
    return _run_in_subprocess("save_as_file_dialog", root_path)


def _save_as_file_dialog_tk(root_path=os.path.expanduser("~")):  # DO NOT print anything here - that would mess with subprocess results.
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


def inquire_close_unsaved(project_name, root_path=os.path.expanduser("~")):
    print("Inquire closed unsaved:", project_name, root_path)
    choice = _run_in_subprocess("inquire_close_unsaved", project_name)

    print("Choice: ", choice)
    if choice == "save as":
        path = save_as_file_dialog(root_path)
        if path and len(str(path)) > 4:
            return "save as", path
        else:
            return inquire_close_unsaved(project_name, root_path=root_path)  # try again
    elif choice not in ("save", "discard"):
        return "discard"
    else:
        return choice


def _inquire_close_unsaved_tk(project_name):
    monitor = get_monitors()[0]
    pos = (int((monitor.width - 300) / 2), int((monitor.height - 200) / 2))

    root = tk.Tk()
    root.title(f"Save changes to {project_name}?")
    root.geometry(f"+{pos[0]}+{pos[1]}")
    root.withdraw()
    root.update_idletasks()
    dialog = SaveDialog(root)
    return dialog.result


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


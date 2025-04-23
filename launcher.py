import sys
import subprocess
import os
import time

import psutil

from models.settings_manager import SettingsManager

win32gui = None
win32con = None

def import_win_libraries():
    global win32gui, win32con
    try:
        import win32gui as _win32gui
        import win32con as _win32con
        win32gui = _win32gui
        win32con = _win32con
        return True
    except ImportError:
        return False

class Launcher:

    @staticmethod
    def get_executable():
        executable = os.path.abspath(sys.argv[0])
        if executable.endswith('.py'):
            command = [sys.executable, executable]
        else:
            command = [executable]
        return command

    @staticmethod
    def launch(flag, *args):
        lock = False
        if flag.strip() == "-open":
            lock = Launcher.check_for_lock_file(args[0])
        if not lock:
            command = Launcher.get_executable()
            command.append(flag.strip())
            command.extend(args)
            log_file = Launcher.get_logfile_path(args[0]) if len(args) else SettingsManager().get_default_log_path(flag)
            print(f'Launching: {command}')
            with open(log_file, "w") as f:
                subprocess.Popen(command, stdout=f, stderr=subprocess.STDOUT)

    @staticmethod
    def get_logfile_path(path):
        logpath = os.path.abspath(path)
        dirname, logfile = os.path.split(logpath)
        logfile = (logfile + '.log').replace(' ', '_')
        if sys.platform.startswith("linux") or sys.platform == "darwin":
            if not logfile.startswith("."):
                logfile = "." + logfile
        logpath = os.path.join(dirname, logfile)
        return logpath

    @staticmethod
    def get_lockfile_path(path):
        return Launcher.get_logfile_path(path).replace('.log', '.lock')

    @staticmethod
    def show_in_explorer(path_inp):
        try:
            path = os.path.abspath(path_inp)
            if sys.platform.startswith('win'):
                if os.path.isdir(path):
                    subprocess.Popen(["explorer", path], stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen(["explorer", "/select,", path], stderr=subprocess.DEVNULL)
            elif sys.platform.startswith('linux'):
                subprocess.Popen(['xdg-open', path], stderr=subprocess.DEVNULL)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', path], stderr=subprocess.DEVNULL)
            else:
                print(f"Unsupported OS: cannot open file {path}")
        except Exception as e:
            print(f"Failed to open file {path}: {e}")

    @staticmethod
    def launch_new():
        Launcher.launch("-new")

    @staticmethod
    def open(file):
        Launcher.launch('-open', file)

    @staticmethod
    def check_for_lock_file(file):
        lockfile = Launcher.get_lockfile_path(file)
        print("Checking for: ", lockfile)
        if os.path.exists(lockfile):  # Check for lock file
            with open(lockfile, "r") as lock_file:
                lines = lock_file.read().splitlines()
                window_title = lines[0].strip() if len(lines) > 0 else ""
                try:
                    pid = int(lines[1].strip()) if len(lines) > 1 else -1
                except ValueError:
                    pid = -1
            window_switched = Launcher.bring_window_to_front(window_title)
            if window_switched:
                return True
            elif psutil.pid_exists(pid):
                print("Process still running.")
                with open(lockfile, "w") as lock_file:
                    lock_file.write(window_title)
                return True
            else:
                os.remove(lockfile)  # faulty lock
                print("Spurious lock file deleted")
        return False

    @staticmethod
    def bring_window_to_front(window_title):
        if sys.platform.startswith("win"):
            if not import_win_libraries():
                return False
            hwnd = win32gui.FindWindow(None, window_title)
            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return True
            else:
                hwnd = win32gui.FindWindow(None, "*" + window_title)
                if hwnd:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    return True
                else:
                    print(f"Window with title '{window_title}' not found.")
                    return False
        elif sys.platform.startswith("linux"):
            try:
                result = subprocess.run(["wmctrl", "-a", window_title])
                if result.returncode != 0:
                    # optional fallback: notify user
                    subprocess.run(["notify-send", "SpectraMatcher", "Already running — please switch to it."])
                return result.returncode == 0
            except FileNotFoundError:
                print("wmctrl not installed. Cannot raise window.")
                return False
        else:
            print(f"Platform '{sys.platform}' not supported for window focus.")
            return False

    @staticmethod
    def maximize_window(window_title):
        if not import_win_libraries():
            return True
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return True

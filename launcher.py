import datetime
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
    log_file_path = None

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
            print(f'Launching: {command}')
            try:
                subprocess.Popen(command, close_fds=True)
            except Exception as e:
                print("Error while launching: ", e)

    @staticmethod
    def get_log_dir():
        base_dir = os.path.abspath(SettingsManager().get("projectsPath", os.getcwd()))
        if sys.platform.startswith("linux") or sys.platform == "darwin":
            log_dirname = ".log"
        else:
            log_dirname = "log"
        log_dir = os.path.join(base_dir, log_dirname)
        try:
            if not os.path.exists(log_dir):  # Create the directory if it doesn't exist
                os.makedirs(log_dir, exist_ok=True)
            if sys.platform.startswith("win"):  # On Windows, set the hidden attribute
                try:
                    subprocess.check_call(["attrib", "+h", log_dir])
                except Exception as e:
                    print(f"Warning: Could not set hidden attribute on {log_dir}: {e}")
        except Exception as e:
            print("Log directory could not be created: ", e)
        return os.path.abspath(log_dir)

    @staticmethod
    def get_logfile_path(path):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        _, logfile = os.path.split(path)
        logfile = os.path.splitext(str(logfile))[0].replace(' ', '_')  # Remove extension
        logfile = f"{logfile}_{timestamp}.log"
        log_path = os.path.join(Launcher.get_log_dir(), logfile)
        Launcher.log_file_path = log_path
        print("Log file: ", log_path)
        return log_path

    @staticmethod
    def show_log_file():
        path = Launcher.log_file_path
        if path is not None and os.path.exists(path):
            Launcher.show_in_explorer(path)
        else:
            log_dir = Launcher.get_log_dir()
            Launcher.show_in_explorer(log_dir)

    @staticmethod
    def cleanup_old_logs(max_age_days=1):
        log_dir = Launcher.get_log_dir()
        if not os.path.exists(log_dir):
            print(f"Could not clean log dir: Directory {log_dir} does not exist.")
            return
        now = time.time()
        max_age_seconds = max_age_days * 86400
        _, own_log = os.path.split(Launcher.log_file_path) if Launcher.log_file_path else ""

        for filename in os.listdir(log_dir):
            file_path = os.path.join(log_dir, filename)
            if (filename != own_log) and os.path.isfile(file_path) and (os.path.splitext(file_path)[1] == ".log"):
                try:
                    file_mtime = os.path.getmtime(file_path)
                    if now - file_mtime > max_age_seconds:
                        os.remove(file_path)
                except Exception as e:
                    print(f"Warning: Could not delete {file_path}: {e}")

    @staticmethod
    def get_lockfile_path(file):
        dirname, lockfile = os.path.split(file)
        lockfile = (lockfile + '.lock').replace(' ', '_')
        if sys.platform.startswith("linux") or sys.platform == "darwin":
            if not lockfile.startswith("."):
                lockfile = "." + lockfile
        lock_path = os.path.join(dirname, lockfile)
        return lock_path

    @staticmethod
    def show_in_explorer(path_inp):
        try:
            path = os.path.normpath(os.path.abspath(path_inp))
            if sys.platform.startswith('win'):
                if os.path.isdir(path):
                    subprocess.Popen(["explorer", path], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen(["explorer", "/select,", path], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        print("Checking for lock file: ", repr(lockfile))
        try:
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
                    try:
                        with open(lockfile, "w") as lock_file:
                            lock_file.write(window_title)
                        return True
                    except Exception as e:
                        return False
                else:
                    try:
                        os.remove(lockfile)  # faulty lock
                        print("Spurious lock file deleted")
                    except Exception as e:
                        print("Lock file couldn't be deleted! ", e)
                        return False
        except Exception as e:
            print("Error in lock file check! ", e)
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

    @staticmethod
    def notify_linux_user(message):
        if sys.platform.startswith("linux"):
            try:
                subprocess.Popen(["notify-send", "SpectraMatcher", message])
            except FileNotFoundError:
                print("notify-send not available. Could not show system notification.")

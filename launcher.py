import sys
import subprocess
import os

from pandas.compat import is_platform_windows

from models.settings_manager import SettingsManager


class Launcher:

    @staticmethod
    def get_executable():
        executable = sys.argv[0]
        if executable.endswith('.py'):
            command = f'python {executable} '
        else:
            command = f'{executable} '
        return command

    @staticmethod
    def launch(flag, *args):
        lock = False
        if flag.strip() == "-open":
            lock = Launcher.check_for_lock_file(args[0])
        if not lock:
            command = Launcher.get_executable() + flag
            for a in args:
                arg = a.strip("'").strip('"')
                command += f' "{arg}"'
            log_file = args[0]+".log" if len(args) else (SettingsManager().get("projectsPath").replace("\\", "/")+"/spec").replace("//", "/")+flag.strip()+".log"
            log_file = log_file.replace(" ", "_")
            command += f' >{log_file} 2>&1'
            print(f'Launching: {command}')
            subprocess.Popen(command, shell=True)

    @staticmethod
    def launch_new():
        Launcher.launch("-new")

    @staticmethod
    def open(file):
        Launcher.launch('-open', file)

    @staticmethod
    def check_for_lock_file(file):
        if os.path.exists(file + ".lock"):  # Check for lock file
            with open(file + ".lock", "r") as lock_file:
                window_title = lock_file.readline().strip()
            window_switched = Launcher.bring_window_to_front(window_title)
            if window_switched:
                return True
            else:
                os.remove(file + ".lock")  # faulty lock
                print("Spurious lock file deleted")
        return False



    @staticmethod
    def bring_window_to_front(window_title):
        if not is_platform_windows():
            return True
        import win32gui
        import win32con
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

    @staticmethod
    def maximize_window(window_title):
        if not is_platform_windows():
            return True
        import win32gui
        import win32con
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return True

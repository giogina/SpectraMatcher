import json
import os
import tempfile
import logging
import threading
import time
import ctypes
from models.settings_manager import SettingsManager


# Define an observer interface
class ProjectObserver:
    def update(self, event_type, *args):
        pass


class Project:
    def __init__(self, project_file):
        self._project_file_lock = threading.Lock()
        self._data_lock = threading.Lock()
        self._logger = logging.getLogger(__name__)
        self._observers = {}
        self._is_unsaved = False

        self._settings = SettingsManager()
        self.project_file = project_file
        self._autosave_file = self._get_autosave_file_path()
        self._lock_file_path = self.project_file + ".lock"

        self._data = None

        self._autosave_interval = self._settings.get('autoSaveInterval', 60)  # Default 60 seconds
        self._autosave_thread = threading.Thread(target=self._autosave_loop)
        self._autosave_thread.daemon = True  # Set as a daemon thread

        try:  # Restoring backups needs to happen before checking for autosaves.
            if os.path.exists(self.project_file + ".backup") and not os.path.exists(self.project_file):
                os.rename(self.project_file + ".backup", self.project_file)
            if os.path.exists(self._autosave_file + ".backup") and not os.path.exists(self._autosave_file):
                os.rename(self._autosave_file + ".backup", self._autosave_file)
        except Exception as e:
            logging.error("restoring .backup file failed")

        self._data_defaults = {
            "name": "Untitled",
            "open data folders": [],
        }

        self.window_title = ""  # For bringing that window to the front in Windows

    def load(self, auto=False):
        """Load project file"""
        self._logger.info(f"file: {self.project_file}, exsits={os.path.exists(self.project_file)}")
        self._data = dict()
        with self._project_file_lock:
            self._settings.add_recent_project(self.project_file)
            try:
                if auto and os.path.exists(self._autosave_file):
                    if os.path.exists(self.project_file):
                        os.remove(self.project_file)
                    os.rename(self._autosave_file, self.project_file)
                if os.path.exists(self.project_file):
                    with open(self.project_file, "r") as file:
                        self._data = json.load(file)
                        print(f"Loaded project data: {self._data}")
                    self.window_title = self._assemble_window_title()
                    self._mark_project_as_open()
                elif os.path.exists(self._autosave_file):
                    self._logger.warning("Project file not found. Attempting to restore autosave file...")
                    self.load(auto=True)
                else:
                    self._logger.error(f"Error: Project file {self.project_file} not found.")
                    self._notify_observers("Project file not found")
            except (IOError, OSError) as e:
                self._logger.error(f"Error accessing project file: {e}")
                if not auto and os.path.exists(self._autosave_file):
                    self._logger.warning("Attempting to restore autosave file...")
                    self.load(auto=True)
            except json.JSONDecodeError as e:
                self._logger.error(f"Error decoding project JSON: {e}")
                if not auto and os.path.exists(self._autosave_file):
                    self._logger.warning("Attempting to restore autosave file...")
                    self.load(auto=True)
        self._autosave_thread.start()
        return self

    def new(self, name, import_data=[]):
        self._data = {"name": name, "open data folders": import_data}
        self.save()

    def _get_autosave_file_path(self):
        directory, filename = os.path.split(self.project_file)
        file_base, file_extension = os.path.splitext(filename)
        autosave_filename = f"{file_base}_autosave{file_extension}"
        autosave_file_path = os.path.join(directory, autosave_filename)
        return autosave_file_path

    def _autosave_loop(self):
        while True:
            time.sleep(self._autosave_interval)
            self.save(auto=True)

    def save(self, auto=False):
        with self._data_lock:
            snapshot = dict(self._data)
        save_thread = threading.Thread(target=self._save_project, args=(snapshot, auto,))
        save_thread.start()

    def _assemble_window_title(self):
        title = self.get("name") + f" [{self.project_file}]"
        if not title:
            title = self.project_file
        title += " - SpectraMatcher"
        return title

    def _save_project(self, snapshot, auto):
        if auto and not self._is_unsaved:
            return  # no use auto-saving if nothing has changed
        with self._project_file_lock:
            temp_file_path = ""
            if auto:
                target_file = self._autosave_file
            else:
                target_file = self.project_file
            try:
                dir_name, file_name = os.path.split(target_file)
                temp_fd, temp_file_path = tempfile.mkstemp(dir=dir_name)
                with os.fdopen(temp_fd, 'w') as temp_file:
                    json.dump(snapshot, temp_file, indent=4)
                if os.path.exists(target_file):
                    backup_file = target_file + ".backup"
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename(target_file, backup_file)
                    os.rename(temp_file_path, target_file)
                    os.remove(backup_file)
                else:
                    os.rename(temp_file_path, target_file)
                if auto:
                    self._hide(self._autosave_file)
                self._logger.info(f"Save successful.")
            except (IOError, OSError) as e:
                self._logger.error(f"Error saving project: {e}")
                if temp_file_path:
                    os.remove(temp_file_path)

    def _hide(self, file):
        FILE_ATTRIBUTE_HIDDEN = 0x02

        if isinstance(file, str):
            c_filepath = ctypes.create_unicode_buffer(file)
        else:
            c_filepath = file
        try:
            ctypes.windll.kernel32.SetFileAttributesW(c_filepath, FILE_ATTRIBUTE_HIDDEN)
        except Exception as e:
            self._logger.warning(f"Hiding file {file} failed: {e}")

    ############### Observers ###############

    def add_observer(self, observer, event_type):
        if event_type not in self._observers:
            self._observers[event_type] = []
        self._observers[event_type].append(observer)

    def remove_observer(self, observer, event_type):
        if event_type in self._observers:
            self._observers[event_type].remove(observer)

    def _notify_observers(self, event_type, *args):
        if event_type in self._observers:
            for observer in self._observers[event_type]:
                observer.update(event_type, args)

    def _project_unsaved(self, changed=True):
        self._is_unsaved = changed
        self._notify_observers("project_unsaved", changed)

    def _mark_project_as_open(self):
        try:
            if os.path.exists(self._lock_file_path):
                os.remove(self._lock_file_path)
            with open(self._lock_file_path, 'w') as lock_file:
                lock_file.write(self.window_title)
            self._hide(self._lock_file_path)
        except Exception as e:
            logging.warning(f"Couldn't write lock file! {e}")

    def check_newer_autosave(self):
        if os.path.exists(self._autosave_file):
            autosave_mod_time = os.path.getmtime(self._autosave_file)
            if os.path.exists(self.project_file):
                project_mod_time = os.path.getmtime(self.project_file)
                if autosave_mod_time <= project_mod_time:
                    return False
                else:
                    return True
            else:
                return True
        else:
            return False

    def save_as(self, new_file):
        print(f"Project received save as request: {new_file}")

        self.project_file = new_file
        self.save()

        self._settings.add_recent_project(self.project_file)
        self.window_title = self._assemble_window_title()
        self._project_unsaved(False)

        # Rename autosave
        old_autosave = self._autosave_file
        self._autosave_file = self._get_autosave_file_path()
        if os.path.exists(old_autosave):
            os.rename(old_autosave, self._autosave_file)  # might as well just keep it for safety...

        # Mark new project file as open
        if os.path.exists(self._lock_file_path):
            os.remove(self._lock_file_path)
        self._lock_file_path = self.project_file + ".lock"
        self._mark_project_as_open()

    def save_and_close_project(self):
        print("Save and close called")
        with self._data_lock:
            snapshot = dict(self._data)
        # save synced-ly this time to make sure it executes before program closes.
        self._save_project(snapshot, auto=False)
        self.close_project()

    def close_project(self, close_anyway=False):
        with self._project_file_lock:
            if not self.check_newer_autosave() or close_anyway:
                if os.path.exists(self._autosave_file):
                    os.remove(self._autosave_file)
            if os.path.exists(self._lock_file_path):
                os.remove(self._lock_file_path)

    def get(self, key, default=None):
        with self._data_lock:
            if key in self._data:
                return self._data[key]
            else:
                if key in self._data_defaults:
                    self._logger.warning(f"Project data key {key} not found, using defaults.")
                    return self._data_defaults[key]
                else:
                    self._logger.error(f"Project data key {key} not found in get")
                    return default

    def set(self, key, value):
        if key not in self._data:
            self._logger.info(f"Used an unknown project data key '{key}'. Added it anyway.")
        with self._data_lock:
            self._data[key] = value
        self._project_unsaved()

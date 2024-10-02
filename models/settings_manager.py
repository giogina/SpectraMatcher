import glob
import json
import os
import tempfile
# import logging
import threading
import copy


class Settings:
    """Keys of settings"""
    PROJECTS_PATH = "projectsPath"
    DATA_PATH = "dataPath"
    RECENT_PROJECTS = "recentProjects"
    AUTO_SAVE_INTERVAL = "autoSaveInterval"
    SHORTCUTS = "shortcuts"
    FILE_EXPLORER_COLUMNS = "file explorer columns"
    CHECKS = "sanity checks"


class SettingsManager:
    _DEFAULT_SETTINGS = {
        Settings.PROJECTS_PATH: os.path.join(os.path.expanduser("~"), "SpectraMatcher").replace("\\", "/"),
        Settings.DATA_PATH: os.path.expanduser("~"),
        Settings.RECENT_PROJECTS: [],
        Settings.AUTO_SAVE_INTERVAL: 60,  # Seconds
        Settings.SHORTCUTS: {
            (16, 17, 79): "Open",
            (17, 83): "Save",
            (16, 17, 83): "Save as",

        },  # 17: Ctrl, 16: Shift, 18: Alt
        Settings.CHECKS: True,
        Settings.FILE_EXPLORER_COLUMNS: [["Icons", 16, 16, True],  # [Label, start/current width, min width, default show value]
                                         ["File", 372, 200, True],
                                         ["Status", 60, 50, True],
                                         ["State", 70, 50, True],
                                         ["Job", 70, 50, True],
                                         ["Method", 164, 50, True],
                                         ["Keywords", 70, 50, False],
                                         ["Molecule", 70, 50, True],
                                         ["Multiplicity", 70, 30, False],
                                         ["0-0 Energy / cm⁻¹", 160, 80, True],
                                         ["Wavenumbers / cm⁻¹", 265, 160, True],
                                         ]
    }

    _instance = None
    _is_initialized = False

    def __new__(cls):  # Make SettingsManager a Singleton.
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._is_initialized:
            self.update_lock = threading.Lock()  # Lock for updating settings in memory
            self.file_lock = threading.Lock()  # Lock for file operations

            # self.logger = logging.getLogger(__name__)
            appdata_path = os.getenv('APPDATA')
            spectra_matcher_path = os.path.join(appdata_path, 'SpectraMatcher')
            config_path = os.path.join(spectra_matcher_path, 'config')
            os.makedirs(config_path, exist_ok=True)
            self.settings_file = os.path.join(config_path, 'settings.json')

            self._settings_dict = self._load_settings()
            # self.logger.info(f"Settings loaded. {self._settings_dict}")

            projects_path = self.get(Settings.PROJECTS_PATH)
            if not os.path.exists(projects_path):
                os.makedirs(projects_path, exist_ok=True)

            self._is_initialized = True

    def _load_settings(self):
        print("Load settings")
        with self.file_lock:
            try:
                if os.path.exists(self.settings_file):
                    with open(self.settings_file, "r") as file:
                        print(f"Attempting to read{self.settings_file}...")
                        temp_settings = copy.deepcopy(SettingsManager._DEFAULT_SETTINGS)
                        temp_settings.update(self._convert_keys_to_tuple(json.load(file)))
                        return temp_settings
                else:
                    return self._create_default_settings()
            except (IOError, OSError) as e:
                print(f"Error accessing settings file: {e}")
            except json.JSONDecodeError as e:
                print(f"Error decoding settings JSON: {e}")
            return self._create_default_settings()

    def _create_default_settings(self):
        print(f"Creating default settings file...")
        try:
            settings = copy.deepcopy(SettingsManager._DEFAULT_SETTINGS)
            with open(self.settings_file, "w") as file:
                json.dump(self._convert_dict_keys_to_string(settings), file, indent=4)
        except (IOError, OSError) as e:
            print(f"Error creating default settings file: {e}")
        return settings

    def _convert_dict_keys_to_string(self, d):
        """Converts dictionary keys from tuples to strings."""
        if d.get("shortcuts"):
            d["shortcuts"] = {str(key) if isinstance(key, tuple) else key: value for key, value in d["shortcuts"].items()}
        return d

    def _convert_keys_to_tuple(self, d):
        """Converts keys from strings back to tuples if possible."""
        if d.get("shortcuts"):
            new_dict = {}
            for key, value in d["shortcuts"].items():
                if key.startswith("(") and key.endswith(")"):
                    try:
                        new_key = tuple(map(int, key.replace(",)", ")")[1:-1].split(", ")))
                    except ValueError:
                        new_key = key
                else:
                    new_key = key
                new_dict[new_key] = value
            d["shortcuts"] = new_dict
        return d

    def _save_settings_async(self):
        with self.update_lock:
            settings_snapshot = copy.deepcopy(self._settings_dict)
        settings_snapshot = self._convert_dict_keys_to_string(settings_snapshot)
        save_thread = threading.Thread(target=self._save_settings, args=(settings_snapshot,))
        save_thread.start()

    def _delete_temp_files(self, directory):
        pattern = os.path.join(directory, 'tmp*')
        temp_files = glob.glob(pattern)
        for file_path in temp_files:
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

    def _save_settings(self, settings_snapshot):
        with self.file_lock:
            temp_file_path = ""
            try:
                # Create a temporary file in the same directory as the target file
                dir_name, file_name = os.path.split(self.settings_file)
                self._delete_temp_files(dir_name)
                temp_fd, temp_file_path = tempfile.mkstemp(dir=dir_name)

                with os.fdopen(temp_fd, 'w') as temp_file:
                    json.dump(settings_snapshot, temp_file, indent=4)

                # Rename the temp file to the target file
                backup_file = self.settings_file + ".backup"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(self.settings_file, backup_file)
                os.rename(temp_file_path, self.settings_file)
                os.remove(backup_file)

            except Exception as e:
                print(f"Error saving settings: {e}")
                if temp_file_path:
                    os.remove(temp_file_path)

    def get(self, key, default=None):
        """Always returns deepcopy"""
        if key in self._settings_dict:
            return copy.deepcopy(self._settings_dict[key])
        elif key in SettingsManager._DEFAULT_SETTINGS:
            self._settings_dict[key] = copy.deepcopy(SettingsManager._DEFAULT_SETTINGS[key])
            return copy.deepcopy(self._settings_dict[key])
        else:
            print(f"Tried to get setting {key} which did not exist.")
            return default

    def update_settings(self, new_settings):
        for key in new_settings:
            if key not in SettingsManager._DEFAULT_SETTINGS:
                print(f"Used an unknown setting '{key}' which is not in default settings")
            if key in [Settings.RECENT_PROJECTS]:
                print(f"Attempted to assign protected setting '{key}'. Ignoring.")
                return
            with self.update_lock:
                self._settings_dict[key] = copy.deepcopy(new_settings[key])
        self._save_settings_async()

    def reset_shortcuts(self):
        del self._settings_dict[Settings.SHORTCUTS]
        self._save_settings_async()
        self._settings_dict[Settings.SHORTCUTS] = copy.deepcopy(SettingsManager._DEFAULT_SETTINGS[Settings.SHORTCUTS])

    def set_shortcut(self, action: str, shortcut: tuple):
        if self._settings_dict.get(Settings.SHORTCUTS):
            dels = []
            for key, value in self._settings_dict[Settings.SHORTCUTS].items():
                if value == action:
                    dels.append(key)
            for key in dels:
                del self._settings_dict[Settings.SHORTCUTS][key]
        else:
            self._settings_dict[Settings.SHORTCUTS] = copy.deepcopy(SettingsManager._DEFAULT_SETTINGS[Settings.SHORTCUTS])
        self._settings_dict[Settings.SHORTCUTS][shortcut] = action
        self._save_settings_async()

    def add_recent_project(self, project_file):
        project_file = project_file.replace("\\", "/")  # Just to keep things consistent
        with self.update_lock:
            if self._settings_dict[Settings.RECENT_PROJECTS] and self._settings_dict[Settings.RECENT_PROJECTS][0] == project_file:
                return
            if project_file in self._settings_dict[Settings.RECENT_PROJECTS]:
                self._settings_dict[Settings.RECENT_PROJECTS].remove(project_file)
            self._settings_dict[Settings.RECENT_PROJECTS].insert(0, project_file)
        self._save_settings_async()

    def set_sanity_checks(self, check: bool):
        self._settings_dict[Settings.CHECKS] = check
        self._save_settings_async()


import copy
import json
import os
import sys
import tempfile
import threading
import time
import ctypes

# import psutil

from launcher import Launcher
from models.molecular_data import ModeList
from models.settings_manager import SettingsManager
from models.data_file_manager import DataFileManager, FileObserver, File
from models.state import State
from models.experimental_spectrum import ExperimentalSpectrum
from utility.labels import Labels
from utility.matcher import Matcher
from utility.noop import noop
from utility.wavenumber_corrector import WavenumberCorrector
from utility.spectrum_plots import SpecPlotter

last_cpu_times = {}

# def print_thread_info(threshold=0.5):
#     proc = psutil.Process(os.getpid())
#     interval = 3
#     while True:
#         print("======== Threads ========")
#
#         tid_to_name = {t.native_id: t.name for t in threading.enumerate() if hasattr(t, 'native_id')}
#
#         current = {}
#         for t in proc.threads():
#             tid = t.id
#             cpu_time = t.user_time + t.system_time
#             current[tid] = cpu_time
#
#             last = last_cpu_times.get(tid, 0.0)
#             delta = cpu_time - last
#             usage_percent = (delta / interval) * 100
#
#             if usage_percent > threshold:
#                 name = tid_to_name.get(tid, "(unknown)")
#                 print(f"Thread ID {tid:<8} | ΔCPU: {delta:.2f}s | CPU%: {usage_percent:5.1f}% | {name}")
#
#         last_cpu_times.clear()
#         last_cpu_times.update(current)
#         time.sleep(interval)


class ProjectObserver:
    def update(self, event_type, *args):
        pass


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        # if isinstance(obj, StateData):
        #     state_data_dict = copy.deepcopy(obj.__dict__)
        #     state_data_dict['__StateData__'] = True
        #     for key in obj.EXCLUDE:
        #         if key in state_data_dict.keys():
        #             del state_data_dict[key]
        #     # del state_data_dict["EXCLUDE"]
        #     return state_data_dict
        # if isinstance(obj, ExpPeak):
        #     exp_pair = (obj.wavenumber, obj.intensity, obj.index, obj.prominence)
        #     return exp_pair

        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def my_decoder(dct):
    # if '__StateData__' in dct:
    #     return StateData(**dct)
    # if '__ExperimentalSpectrum__' in dct:
    #     return ExperimentalSpectrum(**dct)
    return dct


class Project(FileObserver):
    def __init__(self, project_file):
        self._project_file_lock = threading.Lock()
        self._data_lock = threading.Lock()
        self._observers = {}
        self._is_unsaved = False

        self._settings = SettingsManager()
        self.data_file_manager = DataFileManager()
        self.data_file_manager.add_observer(self, "directory structure changed")
        SpecPlotter.add_observer(self)
        self.project_file = project_file
        self._autosave_file = self._get_autosave_file_path()
        self._lock_file_path = Launcher.get_lockfile_path(self.project_file)

        self._data = None

        self._autosave_interval = self._settings.get('autoSaveInterval', 60)  # Default 60 seconds
        self._autosave_thread = threading.Thread(target=self._autosave_loop)
        self._autosave_thread.daemon = True  # Set as a daemon thread

        self.load_failed_callback = noop

        try:  # Restoring backups needs to happen before checking for autosaves.
            if os.path.exists(self.project_file + ".backup") and not os.path.exists(self.project_file):
                os.rename(self.project_file + ".backup", self.project_file)
            if os.path.exists(self._autosave_file + ".backup") and not os.path.exists(self._autosave_file):
                os.rename(self._autosave_file + ".backup", self._autosave_file)
        except Exception as e:
            print("restoring .backup file failed")

        self._data_defaults = {
            "name": "Untitled",
            "open data folders": [],
            "open data files": [],
            "experimental spectra": {},
            "ground state path": None,
            "progress": "start",
            "active emission plotter": None,  # half_width, x_min, x_max, x_step=1
            "active excitation plotter": None,  # half_width, x_min, x_max, x_step=1
        }

        self.window_title = ""  # For bringing that window to the front in Windows
        self._json_lock = threading.Lock()
        self._last_saved_json = None
        self._auto_saved_json = None
        self._last_change = None

    def abspath(self, path):
        if type(path) == str and path.startswith("."):
            altpath = os.path.split(self.project_file)[0] + path[1:]
            if os.path.exists(altpath):
                return altpath
        return path

    # react to observations from my data file manager / SpecPlotter
    def update(self, event_type, *args):
        if event_type == "directory structure changed":
            self._data["open data folders"] = [d.path for _, d in self.data_file_manager.top_level_directories.items()]
            self._data["open data files"] = [file.path for _, file in self.data_file_manager.top_level_files.items()]
            self.project_changed(True)
        elif event_type == SpecPlotter.active_plotter_changed_notification:
            if args[1]:  # is_emission = True
                self._data["active emission plotter"] = args[0]
            else:
                self._data["active excitation plotter"] = args[0]
            self.project_changed(True)

    def load(self, auto=False):
        """Load project file"""
        print(f"file: {self.project_file}, exsits={os.path.exists(self.project_file)}")
        self._data = dict()
        with self._project_file_lock:
            self._settings.add_recent_project(self.project_file)
            try:
                if auto and os.path.exists(self._autosave_file):
                    if os.path.exists(self.project_file):
                        os.remove(self.project_file)
                    os.rename(self._autosave_file, self.project_file)
                if os.path.exists(self.project_file):
                    try:
                        with open(self.project_file, "r") as file:
                            self._data = json.load(file, object_hook=my_decoder)
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"Failed to load project file: {e}")
                        self.load_failed_callback()
                        return
                    self._last_saved_json = json.dumps(self._data, sort_keys=True, indent=4, separators=(",", ":"), cls=MyEncoder).strip()
                    self.window_title = self._assemble_window_title()
                    self._mark_project_as_open()
                    self._notify_observers("project data changed")
                    self._notify_observers("state data changed")
                    self._notify_observers("experimental data changed")
                elif os.path.exists(self._autosave_file):
                    print("Project file not found. Attempting to restore autosave file...")
                    self.load(auto=True)
                else:
                    print(f"Error: Project file {self.project_file} not found.")
                    self._notify_observers("Project file not found")
            except (IOError, OSError) as e:
                print(f"Error accessing project file: {e}")
                if not auto and os.path.exists(self._autosave_file):
                    print("Attempting to restore autosave file...")
                    self.load(auto=True)
            except json.JSONDecodeError as e:
                print(f"Error decoding project JSON: {e}")
                if not auto and os.path.exists(self._autosave_file):
                    print("Attempting to restore autosave file...")
                    self.load(auto=True)
        self._autosave_thread.start()

        # threading.Thread(target=print_thread_info, daemon=True).start()

        # Initialize everything based on loaded data!
        if "ignored" not in self._data.keys():
            self._data["ignored"] = []
        else:
            self._data["ignored"] = [self.abspath(f) for f in self._data["ignored"]]
        if "files marked as emission" not in self._data.keys():
            self._data["files marked as emission"] = []
        else:
            self._data["files marked as emission"] = [self.abspath(f) for f in self._data["files marked as emission"]]
        if "files marked as excitation" not in self._data.keys():
            self._data["files marked as excitation"] = []
        else:
            self._data["files marked as excitation"] = [self.abspath(f) for f in self._data["files marked as excitation"]]
        self._data["open data files"] = [self.abspath(f) for f in self._data["open data files"]]
        self._data["open data folders"] = [self.abspath(f) for f in self._data["open data folders"]]
        if "experiment settings" not in self._data.keys():  # Excited states
            self._data["experiment settings"] = []
        for s in self._data["experiment settings"]:
            path = self.abspath(s.get("path"))
            # s["path"] = path
            marked = None
            if path in self._data["files marked as excitation"]:
                marked = "excitation"
            elif path in self._data["files marked as emission"]:
                marked = "emission"
            if path is not None and os.path.exists(path):
                file = File(path=path, parent="Project", depth=-1, mark_as_exp=marked)  # will call exp.assimilate_file_data when done parsing
                ExperimentalSpectrum(file, s)
            else:
                print(f"WARNING: Experimental file {path} not found. Ignoring.")
        if "ground state path" not in self._data.keys():
            self._data["ground state path"] = None
        State({"freq file": self.abspath(self._data["ground state path"])})
        if "State class info" not in self._data.keys():
            self._data["State class info"] = {"molecule": None, "ground state energy": None}
        State.molecule_and_method = self._data["State class info"]
        if "state settings" not in self._data.keys():  # Excited states
            self._data["state settings"] = [{}]
        for s in self._data["state settings"]:
            for key, value in s.items():
                if key.endswith("file"):
                    s[key] = self.abspath(value)
            State(s)
        if "directory toggle states" not in self._data.keys():
            self._data["directory toggle states"] = {}
        if "progress" not in self._data.keys():
            self._data["progress"] = "start"
        self._notify_observers("progress updated")
        if self.get("active emission plotter") is not None:
            SpecPlotter.set_active_plotter(True, *self.get("active emission plotter"))
        if self.get("active excitation plotter") is not None:
            SpecPlotter.set_active_plotter(False, *self.get("active excitation plotter"))
        if "wavenumber correction factors" not in self._data.keys():
            self._data["wavenumber correction factors"] = {True: {'bends': 0.986, 'H stretches': 0.975, 'others': 0.996},
                                                           False: {'bends': 0.986, 'H stretches': 0.975, 'others': 0.996}}
        elif 'true' in self._data["wavenumber correction factors"].keys():
            self._data["wavenumber correction factors"] = {True: self._data["wavenumber correction factors"]['true'],
                                                           False: self._data["wavenumber correction factors"]['false']}
        WavenumberCorrector.correction_factors = self._data["wavenumber correction factors"]
        if "IR order" not in self._data.keys():
            self._data["IR order"] = []
        ModeList.IR_order = self._data["IR order"]
        if "label settings" not in self._data.keys():
            self._data["label settings"] = {True: Labels.defaults(),
                                            False: Labels.defaults()}
        elif 'true' in self._data["label settings"].keys():
            self._data["label settings"] = {True: self._data["label settings"]['true'],
                                            False: self._data["label settings"]['false']}
        Labels.settings = self._data["label settings"]
        Labels.notify_changed_callback = self.project_changed
        if "peak detection settings" not in self._data.keys():
            self._data["peak detection settings"] = {True:  ExperimentalSpectrum.defaults(),
                                                     False: ExperimentalSpectrum.defaults()}
        elif 'true' in self._data["peak detection settings"].keys():
            self._data["peak detection settings"] = {True: self._data["peak detection settings"]['true'],
                                                     False: self._data["peak detection settings"]['false']}
        ExperimentalSpectrum._settings = self._data["peak detection settings"]
        ExperimentalSpectrum.notify_changed_callback = self.project_changed
        if "matcher settings" not in self._data.keys():
            self._data["matcher settings"] = {True:  Matcher.defaults(),
                                              False: Matcher.defaults()}
        elif 'true' in self._data["matcher settings"].keys():
            self._data["matcher settings"] = {True: self._data["matcher settings"]['true'],
                                              False: self._data["matcher settings"]['false']}
        Matcher.settings = self._data["matcher settings"]
        Matcher.notify_changed_callback = self.project_changed
        # Automatically keeps file manager dicts updated in self._data!
        self.data_file_manager.directory_toggle_states = self._data["directory toggle states"]
        self.data_file_manager.ignored_files_and_directories = self._data["ignored"]
        self.data_file_manager.files_marked_as_emission = self._data["files marked as emission"]
        self.data_file_manager.files_marked_as_excitation = self._data["files marked as excitation"]
        self.data_file_manager.open_directories(self._data.get("open data folders", []),
                                                self._data.get("open data files", []))
        if "experimental spectra" not in self._data.keys():
            self._data["experimental spectra"] = copy.deepcopy(self._data_defaults["experimental spectra"])
        self._notify_observers("project loaded")
        return self

    def new(self, name, import_data_dirs=None, import_data_files=None):
        if import_data_files is None:
            import_data_files = []
        if import_data_dirs is None:
            import_data_dirs = []
        self._data = {"name": name, "open data folders": import_data_dirs, "open data files": import_data_files}
        self.save(new_file=True)

    def _get_autosave_file_path(self):
        directory, filename = os.path.split(self.project_file)
        file_base, file_extension = os.path.splitext(filename)
        autosave_filename = f"{file_base}_autosave{file_extension}"
        if sys.platform.startswith("linux") or sys.platform == "darwin":
            autosave_filename = "." + autosave_filename
        autosave_file_path = os.path.join(directory, autosave_filename)
        return autosave_file_path

    def _autosave_loop(self):
        while True:
            # time.sleep(self._autosave_interval)
            time.sleep(0.5)
            if self._last_change is not None and time.time()-self._last_change > 0.5:
                self.save(auto=True)

    def save(self, auto=False, new_file=False):
        # self.gather_extra_data()
        # Instead: Ensure all important data in sub-models is mutable variables assigned to self._data!
        with self._data_lock:
            snapshot = copy.deepcopy(self._data)
        current_json = json.dumps(snapshot, sort_keys=True, indent=4, separators=(",", ":"), cls=MyEncoder).strip()
        if auto:
            if current_json == self._auto_saved_json:
                return  # Nothing actually changed since last auto save
            is_unsaved = current_json != self._last_saved_json
            self.project_unsaved(is_unsaved)
            self._auto_saved_json = current_json
            # print("Changed data; calling for auto-save")
        else:
            self._last_saved_json = current_json
        self._last_change = None

        save_thread = threading.Thread(target=self._save_project, args=(current_json, auto, new_file))
        save_thread.start()

    def _assemble_window_title(self):
        title = self.get("name") + f" [{self.project_file}]"
        if not title:
            title = self.project_file
        title += " - SpectraMatcher"
        return title

    def _save_project(self, current_json, auto, new_file=False):
        if not new_file:
            if not os.path.exists(self.project_file):
                return

        project_path = os.path.split(self.project_file)[0]
        current_json = current_json.replace(project_path, ".")  # use relative paths when possible
        with self._project_file_lock:
            temp_file_path = ""
            if auto:
                target_file = self._autosave_file
            else:
                target_file = self.project_file
            try:
                dir_name, file_name = os.path.split(target_file)
                temp_fd, temp_file_path = tempfile.mkstemp(dir=dir_name)
                with open(temp_fd, 'w') as temp_file:
                    temp_file.write(current_json)
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
                # self._logger.info(f"Save successful.")
                if not auto:
                    self.project_unsaved(False)
            except Exception as e:
                print(f"Error saving project: {e}")
                if temp_file_path:
                    try:
                        os.remove(temp_file_path)
                    except Exception as e:
                        print(f"Error removing temp file {temp_file_path}: {e}")

    def _hide(self, file):
        if sys.platform.startswith("win"):
            FILE_ATTRIBUTE_HIDDEN = 0x02
            if isinstance(file, str):
                c_filepath = ctypes.create_unicode_buffer(file)
            else:
                c_filepath = file
            try:
                ret = ctypes.windll.kernel32.SetFileAttributesW(c_filepath, FILE_ATTRIBUTE_HIDDEN)
                if ret == 0:
                    raise ctypes.WinError()
            except Exception as e:
                print(f"[Windows] Hiding file {file} failed: {e}")

    ############### Observers ###############

    def add_observer(self, observer, event_type):
        if event_type not in self._observers:
            self._observers[event_type] = []
        self._observers[event_type].append(observer)

    def remove_observer(self, observer, event_type):
        if event_type in self._observers:
            self._observers[event_type].remove(observer)

    def  _notify_observers(self, event_type, *args):
        if event_type in self._observers:
            for observer in self._observers[event_type]:
                observer.update(event_type, args)

    def project_changed(self, changed=True):
        '''Set marker for potential change'''
        if changed:
            self._last_change = time.time()
        else:
            self._last_change = None

    def project_unsaved(self, is_unsaved=True):
        if self._is_unsaved != is_unsaved:
            self._is_unsaved = is_unsaved
            self._notify_observers("project_unsaved", is_unsaved)

    def _mark_project_as_open(self):
        try:
            if os.path.exists(self._lock_file_path):
                os.remove(self._lock_file_path)
            with open(self._lock_file_path, 'w') as lock_file:
                lock_file.write(self.window_title+"\n"+str(os.getpid()))
            self._hide(self._lock_file_path)
        except Exception as e:
            print(f"Couldn't write lock file! {e}")

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

    def save_as(self, new_file, at_shutdown=False):
        print(f"Project received save as request: {new_file}")

        try:
            self.project_file = new_file
            name = os.path.splitext(os.path.split(new_file)[1])[0]
            with self._data_lock:
                self._data["name"] = name

            self.save(auto=False, new_file=True)
            self._settings.add_recent_project(self.project_file)
            if not at_shutdown:
                self.window_title = self._assemble_window_title()
                self.project_unsaved(True)  # Causes window title update
                self.project_unsaved(False)

                # Rename autosave
                old_autosave = self._autosave_file
                self._autosave_file = self._get_autosave_file_path()
                if os.path.exists(old_autosave):
                    os.rename(old_autosave, self._autosave_file)  # might as well just keep it for safety...

                # Mark new project file as open
                if os.path.exists(self._lock_file_path):
                    os.remove(self._lock_file_path)
                self._lock_file_path = Launcher.get_lockfile_path(self.project_file)
                self._mark_project_as_open()
        except Exception as e:
            print(f"Error saving as {new_file}:, {e}")

    def save_and_close_project(self):
        print("Save and close called")
        with self._data_lock:
            snapshot = copy.deepcopy(self._data)
        current_json = json.dumps(snapshot, sort_keys=True, indent=4, separators=(",", ":"), cls=MyEncoder).strip()
        # save synced-ly this time to make sure it executes before program closes.
        self._save_project(current_json, auto=False)
        self.close_project()

    def close_project(self, close_anyway=False):
        with self._project_file_lock:
            if close_anyway:
                try:
                    os.utime(self.project_file, None)  # update to current time
                except Exception as e:
                    print("Could not update project file timestamp:", e)
            # if not self.check_newer_autosave() or close_anyway:
            #     if os.path.exists(self._autosave_file):
            #         os.remove(self._autosave_file)  # Just keep it - won't be loaded if it's older.
            if os.path.exists(self._lock_file_path):
                try:
                    os.remove(self._lock_file_path)
                except Exception as e:
                    print(f"Error closing lock file {self._lock_file_path}: {e}")

    def get(self, key, default=None):
        with self._data_lock:
            if key in self._data.keys():
                return self._data[key]
            else:
                if key in self._data_defaults.keys():
                    print(f"Project data key {key} not found, using defaults.")
                    return self._data_defaults[key]
                else:
                    print(f"Project data key {key} not found in get")
                    return default

    def set(self, key, value):
        if key not in self._data:
            print(f"Used an unknown project data key '{key}'. Added it anyway.")
        with self._data_lock:
            self._data[key] = value
        self.project_changed()

    def select_ground_state_file(self, path):
        print(f"Setting ground state path in project: {path}")
        self._data["ground state path"] = path
        self.project_changed()

    def get_selected_ground_state_file(self):
        return self._data.get("ground state path")

    def copy_state_settings(self):
        """Store paths etc of State instances into _data (necessary when new set of states is created)"""
        self._data["state settings"] = []
        if len(State.state_list):
            self._data["ground state path"] = State.state_list[0].settings["freq file"]
        for state in State.state_list[1:]:
            self._data["state settings"].append(state.settings)
        self.project_changed()

    def copy_experiment_settings(self):
        """Store paths etc of ExperimentalSpectrum instances into _data"""
        self._data["experiment settings"] = []
        for exp in ExperimentalSpectrum.spectra_list:
            self._data["experiment settings"].append(exp.settings)
        self.project_changed()

    def update_progress(self, progress):
        self._data["progress"] = progress
        self._notify_observers("progress updated")

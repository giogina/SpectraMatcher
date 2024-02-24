import os
from os.path import isfile, join
import re
from enum import Enum
from utility.experimental_spectrum_parser import ExperimentParser
from utility.read_write_lock import PathLockManager
from utility.async_manager import AsyncManager
from utility.gaussian_parser import GaussianParser


class FileType:
    OTHER = "Other"
    EXPERIMENT_EMISSION = "experiment emission"
    EXPERIMENT_EXCITATION = "experiment excitation"
    GAUSSIAN_LOG = "Gaussian log"
    GAUSSIAN_INPUT = "Gaussian input"
    GAUSSIAN_CHECKPOINT = "Gaussian chk"
    FREQ_GROUND = "Frequency ground state"
    FREQ_EXCITED = "Frequency excited state"
    FREQ_GROUND_ANHARM = "Frequency ground state anharm"
    FREQ_EXCITED_ANHARM = "Frequency excited state anharm"
    FC_EXCITATION = "FC excitation"
    FC_EMISSION = "FC emission"
    LOG_TYPES = (GAUSSIAN_LOG, FC_EMISSION, FC_EXCITATION,
                 FREQ_GROUND, FREQ_EXCITED, FREQ_GROUND_ANHARM, FREQ_EXCITED_ANHARM)


class GaussianLog(Enum):
    STATUS = "status"
    HAS_HPMODES = "hpmodes"
    FINISHED = "finished"
    ERROR = "error"
    RUNNING = "running"
    NEGATIVE_FREQUENCY = "negative frequency"


class DataFileManager:
    def __init__(self):
        self.top_level_directories = {}
        self.top_level_files = {}
        self._observers = {}
        self.last_path = "/"  # Last added data path; for file dialog root dirs
        # Set from parent Project instance, directly coupled to its _data:
        self.directory_toggle_states = {}  # "directory tag": bool - is dir toggled open?
        self.ignored_files_and_directories = []
        self.all_files = {}  # lookup files in a flat structure

        self.lock_manager = PathLockManager()

    def open_directories(self, open_data_dirs, open_data_files=None):
        print(f"Opening: {open_data_dirs, open_data_files}")
        path = None
        if open_data_dirs:
            for path in open_data_dirs:
                directory = Directory(path, self)
                self.top_level_directories[directory.tag] = directory  # queue gets filled in here
                print(f"Added directory: {directory.tag}")
        if open_data_files:
            for path in open_data_files:
                file = File(path, self)
                self.top_level_files[file.tag] = file
        self.last_path = os.path.dirname(path) if path else "/"

        # notify file explorer viewmodel to re-populate the entire list, and parent project to update top level paths.
        self.notify_observers("directory structure changed")

        for file in self.all_files.values():
            file.submit_what_am_i(observers=self.get_event_observers("file changed"), notification="file changed")  # Need to do this after directory structure notification, or it'll be too fast!

    def open_directories_or_files(self, paths: list):
        new_paths = []
        new_files = []
        for path in paths:
            if type(path) == str:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        new_paths.append(path)
                    elif os.path.isfile(path):
                        new_files.append(path)
        self.open_directories(new_paths, new_files)

    def close_directory(self, directory_tag):
        if directory_tag in self.top_level_directories.keys():
            self._forget_directory_info(self.top_level_directories[directory_tag])
            del self.top_level_directories[directory_tag]
            self.notify_observers("directory structure changed", True)

    def close_file(self, file_tag):
        if file_tag in self.top_level_files.keys():
            del self.top_level_files[file_tag]
            self.notify_observers("directory structure changed")

    def toggle_directory(self, directory_tag, is_open):
        self.directory_toggle_states[directory_tag] = is_open

    def is_directory_toggled_open(self, directory_tag):
        return self.directory_toggle_states.get(directory_tag, True)

    def ignore(self, tag, ignore=True):
        print(f"Ignore: {tag, ignore, tag in self.ignored_files_and_directories}")
        if ignore and (tag not in self.ignored_files_and_directories):
            self.ignored_files_and_directories.append(tag)
        if not ignore and (tag in self.ignored_files_and_directories):
            self.ignored_files_and_directories.remove(tag)
        self.notify_observers("directory structure changed")

    def is_ignored(self, tag):
        return tag in self.ignored_files_and_directories

    def mark_file_as_excitation(self, tag, excitation=True):
        file = self.get_file(tag)
        print(f"File {file} for tag {tag}")
        if file:
            if excitation and file.type == FileType.EXPERIMENT_EMISSION:
                file.type = FileType.EXPERIMENT_EXCITATION
            if not excitation and file.type == FileType.EXPERIMENT_EXCITATION:
                file.type = FileType.EXPERIMENT_EMISSION
            self.notify_observers("file changed", file)

    def _forget_directory_info(self, directory):
        if directory.tag in self.directory_toggle_states.keys():
            del self.directory_toggle_states[directory.tag]
        if directory.tag in self.ignored_files_and_directories:
            self.ignored_files_and_directories.remove(directory.tag)
        for f in directory.content_files.values():
            if f.tag in self.ignored_files_and_directories:
                self.ignored_files_and_directories.remove(f.tag)
        for i, d in directory.content_dirs.items():
            self._forget_directory_info(d)

    def get_file(self, tag):
        return self.all_files.get(tag)

    # magic!
    def make_readable(self, tag):
        file = self.all_files.get(tag)
        file.is_human_readable = True
        self.notify_observers("file changed", file)
        if file:
            AsyncManager.submit_task(f"make {file.path} readable", self._make_readable, file.path)

    def _make_readable(self, path):
        if os.path.exists(path):
            tmp_file_path = f"{path}.tmp"
            self.lock_manager.acquire_write(path)
            try:
                with open(path, 'r') as orig_log:
                    lines = orig_log.readlines()
                with open(tmp_file_path, 'w') as new_log:
                    for line in lines:
                        newline = line.rstrip('\n').rstrip('\r')
                        if len(newline):
                            new_log.write(newline + '\r\n')
                os.replace(tmp_file_path, path)
            finally:
                self.lock_manager.release_write(path)

    ############### Observers ###############

    def add_observer(self, observer, event_type):
        if event_type not in self._observers:
            self._observers[event_type] = []
        self._observers[event_type].append(observer)

    def remove_observer(self, observer, event_type):
        if event_type in self._observers:
            self._observers[event_type].remove(observer)

    def notify_observers(self, event_type, *args):
        if event_type in self._observers:
            for observer in self._observers[event_type]:
                observer.update(event_type, args)

    def get_event_observers(self, event_type):
        obs = []
        if event_type in self._observers:
            for observer in self._observers[event_type]:
                obs.append(observer)
        return obs


# Observer interface
class FileObserver:
    def update(self, event_type, *args):
        pass


class Directory:
    def __init__(self, path, manager: DataFileManager, name=None, parent=None, depth=0):
        self.content_dirs = {}
        self.content_files = {}
        self.path = path.replace("/", "\\")
        self.manager = manager
        self.tag = f"dir_{path}_{depth}"
        self.depth = depth
        if name:
            self.name = name
        else:
            self.name = os.path.basename(path)
        self.parent_directory = parent

        auto_ignore = False
        if self.path.find("\\ignore") > -1 or self.path.find("\\old") > -1:
            print(f"Ignoring directory by path>: {self.path}")
            self.manager.ignore(self.tag)
            self.manager.toggle_directory(directory_tag=self.tag, is_open=False)
            auto_ignore = True

        self.crawl_contents(path, auto_ignore)

    def crawl_contents(self, path, auto_ignore=False):
        dirs = {}
        files = {}
        for item in os.listdir(path):
            if isfile(join(path, item)):
                file = File(join(path, item), name=item, parent=self.tag, depth=self.depth+1)
                files[file.tag] = file
                self.manager.all_files[file.tag] = file
                if auto_ignore:
                    self.manager.ignore(file.tag)
            else:
                directory = Directory(join(path, item), self.manager, name=item, parent=self.tag, depth=self.depth+1)
                dirs[directory.tag] = directory
        self.content_dirs = dirs
        self.content_files = files


class File:
    def __init__(self, path, name=None, parent=None, depth=0):
        self.properties = {}
        self.is_human_readable = True  # \n instead of \r\n making it ugly in notepad
        self.type = None
        self.path = path.replace("/", "\\")
        self.routing_info = {}
        self.geometry = None  # input or last opt / freq log geom
        self.initial_geom = None  # FC initial state geometry
        self.final_geom = None    # FC final state geometry
        self.molecular_formula = None
        self.depth = depth
        self.error = None  # Contains error string if present
        self.tag = f"file_{path}_{depth}"
        self.start_lines = {}
        if name:
            self.name = name
        else:
            self.name = os.path.basename(path)
        self.parent_directory = parent
        name, self.extension = os.path.splitext(self.name)
        self.charge = 0
        self.multiplicity = ""
        self.lines = None  # remember read lines (for project files)

    def submit_what_am_i(self, observers, notification):
        AsyncManager.submit_task(f"File {self.tag} what_am_I", self._what_am_i, observers=observers, notification=notification)

    def submit_get_vibrational_modes(self, observers, notification):
        AsyncManager.submit_task(f"File {self.tag} get_vib_modes", self._get_vibrational_modes, observers=observers, notification=notification)

    def get_FC_spectrum(self, is_emission, observers, notification):
        AsyncManager.submit_task(f"File {self.tag} get_fc_spec", self.get_FC_spectrum, observers=observers, notification=notification)

    def _get_FC_spectrum(self):
        if self.lines is None:
            self._what_am_i(remember_lines=True)
        if self.type not in (FileType.FC_EMISSION, FileType.FC_EXCITATION):
            print(f"Warning: Tried calling get_FC_spectrum on non-FC file {self.path}")
            return
        is_emission = self.type == FileType.FC_EMISSION
        GaussianParser.get_FC_spectrum(self.lines, is_emission, start_line=self.start_lines.get("FC transitions", 0))

    def _get_vibrational_modes(self):
        if self.lines is None:
            self._what_am_i(remember_lines=True)
        GaussianParser.get_vibrational_modes(self.lines, hpmodes_start=self.start_lines.get("hp freq"), lpmodes_start=self.start_lines.get("lp freq"), geometry=self.geometry)

    def _what_am_i(self, remember_lines=False):
        properties = {}
        is_table = False
        if self.extension == ".log":  # Gaussian log
            self.type = FileType.GAUSSIAN_LOG

            PathLockManager.acquire_read(self.path)
            try:
                with open(self.path, 'rb') as file:
                    content = file.read(1024)
                    self.is_human_readable = b'\r\n' in content
                with open(self.path, 'r') as f:
                    lines = f.readlines()
            except Exception as e:
                print(f"File {self.path} couldn't be read! {e}")
            finally:
                PathLockManager.release_read(self.path)

            finished, self.error, self.routing_info, self.charge, self.multiplicity, self.start_lines = GaussianParser.scan_log_file(lines)
            for job in self.routing_info.get("jobs", []):
                if job.startswith("freq"):
                    if re.search(r"(?<![a-zA-Z])(fc|fcht|ht)", job):
                        if job.find("emission") > -1:
                            self.type = FileType.FC_EMISSION  # TODO: FC files always treat current state as ground state; and contain corresponding geom & freqs. Read from there (maybe just as backup).
                        else:
                            self.type = FileType.FC_EXCITATION
                    elif self.routing_info.get("td") is not None:
                        if job.find("anharm") > -1:
                            self.type = FileType.FREQ_EXCITED_ANHARM
                        else:
                            self.type = FileType.FREQ_EXCITED
                    else:
                        if job.find("anharm") > -1:
                            self.type = FileType.FREQ_GROUND_ANHARM
                        else:
                            self.type = FileType.FREQ_GROUND
            print(self.start_lines)
            if "initial state geom" in self.start_lines.keys():
                self.initial_geom = GaussianParser.extract_geometry(lines, self.start_lines["initial state geom"])
                self.molecular_formula = self.initial_geom.get_molecular_formula(self.charge)
            if "final state geom" in self.start_lines.keys():
                self.final_geom = GaussianParser.extract_geometry(lines, self.start_lines["final state geom"])
                if self.molecular_formula is None:
                    self.molecular_formula = self.final_geom.get_molecular_formula(self.charge)
            if "last geom" in self.start_lines.keys():
                self.geometry = GaussianParser.extract_geometry(lines, self.start_lines["last geom"])
                if self.molecular_formula is None:
                    self.molecular_formula = self.geometry.get_molecular_formula(self.charge)

            if finished:
                properties[GaussianLog.STATUS] = GaussianLog.FINISHED
            elif self.error is not None:
                self.error = self.error
                properties[GaussianLog.STATUS] = GaussianLog.ERROR
            else:
                properties[GaussianLog.STATUS] = GaussianLog.RUNNING

        elif self.extension in [".gjf", ".com"]:
            self.type = FileType.GAUSSIAN_INPUT
            lines = []
            PathLockManager.acquire_read(self.path)
            try:
                with open(self.path, 'r') as f:
                    lines = f.readlines()
            except Exception as e:
                print(f"File {self.path} couldn't be read! {e}")
            finally:
                PathLockManager.release_read(self.path)
            self.routing_info, self.charge, self.multiplicity, self.geometry = GaussianParser.parse_input(lines)
            if self.geometry is not None:
                self.molecular_formula = self.geometry.get_molecular_formula(self.charge)
        elif self.extension == ".chk":
            self.type = FileType.GAUSSIAN_CHECKPOINT
        elif self.extension == ".txt":
            try:
                delim, is_table = ExperimentParser.guess_delimiter_and_check_table(self.path)
                self.properties["delimiter"] = delim
            except Exception as e:
                print(f"File {self.path} couldn't be read! {e}")
        elif self.extension in ['.csv', '.tsv', '.xlsx', '.xls', '.xlsm', '.xltx', '.xltm', '.ods']:  # TODO> Document available formats.
            is_table = True
        else:
            self.type = FileType.OTHER

        if is_table:
            if re.search(r'DF_|fluor|emmi', self.name, re.IGNORECASE):
                self.type = FileType.EXPERIMENT_EMISSION
            else:
                self.type = FileType.EXPERIMENT_EXCITATION
        self.properties = properties

        if remember_lines:
            self.lines = lines

        return self



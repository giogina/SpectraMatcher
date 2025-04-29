import os
import sys
from os.path import isfile, join
import re
from enum import Enum

from models.settings_manager import SettingsManager, Settings
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
        self.last_path = SettingsManager().get(Settings.DATA_PATH, os.path.expanduser("~"))  # Last added data path; for file dialog root dirs
        # Set from parent Project instance, directly coupled to its _data:
        self.directory_toggle_states = {}  # "directory tag": bool - is dir toggled open?
        self.ignored_files_and_directories = []
        self.files_marked_as_excitation = []
        self.files_marked_as_emission = []
        self.all_files = {}  # lookup files in a flat structure

    def open_directories(self, open_data_dirs, open_data_files=None):
        print(f"Opening: {open_data_dirs, open_data_files}")
        path = None
        refresh = self.top_level_files == {}
        if open_data_dirs:
            for path in open_data_dirs:
                directory = Directory(path, self)
                self.top_level_directories[directory.tag] = directory  # queue gets filled in here
                print(f"Added directory: {directory.tag}")
        if open_data_files:
            for path in open_data_files:
                file = File(path)
                self.top_level_files[file.tag] = file
        self.last_path = os.path.dirname(path) if path else "/"

        # notify file explorer viewmodel to re-populate the entire list, and parent project to update top level paths.
        self.notify_observers("directory structure changed", refresh)

        # for file in self.all_files.values():
        #     file.submit_what_am_i(observers=self.get_event_observers("file changed"), notification="file changed")  # Need to do this after directory structure notification, or it'll be too fast!

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
            self.notify_observers("directory structure changed", True)

    def toggle_directory(self, directory_tag, is_open):
        self.directory_toggle_states[directory_tag] = is_open

    def is_directory_toggled_open(self, directory_tag):
        return self.directory_toggle_states.get(directory_tag, True)

    def ignore(self, tag, ignore=True):
        if ignore and (tag not in self.ignored_files_and_directories):
            self.ignored_files_and_directories.append(tag)
        if not ignore and (tag in self.ignored_files_and_directories):
            self.ignored_files_and_directories.remove(tag)
        file = self.get_file(tag)
        if file is not None:
            file.ignored = ignore
            file.notify_observers()
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
            file.notify_observers()
        if excitation:
            if file.path in self.files_marked_as_emission:
                self.files_marked_as_emission.remove(file.path)
            self.files_marked_as_excitation.append(file.path)
        else:
            if file.path in self.files_marked_as_excitation:
                self.files_marked_as_excitation.remove(file.path)
            self.files_marked_as_emission.append(file.path)

    def _forget_directory_info(self, directory):
        if directory.tag in self.directory_toggle_states.keys():
            del self.directory_toggle_states[directory.tag]
        if directory.tag in self.ignored_files_and_directories:
            self.ignored_files_and_directories.remove(directory.tag)
        for f in directory.content_files.values():
            if f.tag in self.ignored_files_and_directories:
                self.ignored_files_and_directories.remove(f.tag)
            if f.path in self.files_marked_as_emission:
                self.files_marked_as_emission.remove(f.path)
            if f.path in self.files_marked_as_excitation:
                self.files_marked_as_excitation.remove(f.path)
        for i, d in directory.content_dirs.items():
            self._forget_directory_info(d)

    def get_file(self, tag):
        return self.all_files.get(tag)

    def get_file_by_path(self, path):
        path = os.path.normpath(path)
        for file in self.all_files.values():
            if os.path.normpath(file.path) == path:
                return file
        return None

    # magic!
    def make_readable(self, tag):
        file = self.all_files.get(tag)
        file.submit_make_readable()

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
        self.path = os.path.normpath(path)
        self.manager = manager
        self.tag = f"dir_{path}_{depth}"
        self.depth = depth
        if name:
            self.name = name
        else:
            self.name = os.path.basename(path)
        self.parent_directory = parent

        auto_ignore = False
        if self.path.find("ignore") > -1 or self.path.find("old") > -1:
            print(f"Ignoring directory by path: {self.path}")
            self.manager.ignore(self.tag)
            self.manager.toggle_directory(directory_tag=self.tag, is_open=False)
            auto_ignore = True

        self.crawl_contents(path, auto_ignore)

    def crawl_contents(self, path, auto_ignore=False):
        dirs = {}
        files = {}
        for item in sorted(os.listdir(path)):
            if isfile(join(path, item)):
                file_path = os.path.join(path, item)
                marked = None
                if file_path in self.manager.files_marked_as_excitation:
                    marked = "excitation"
                elif file_path in self.manager.files_marked_as_emission:
                    marked = "emission"
                file = File(path=file_path, name=item, parent=self.tag, depth=self.depth+1, mark_as_exp=marked)
                files[file.tag] = file
                self.manager.all_files[file.tag] = file
                if auto_ignore:
                    self.manager.ignore(file.tag)
                if self.manager.is_ignored(file.tag):
                    file.ignored = True
            else:
                directory = Directory(join(path, item), self.manager, name=item, parent=self.tag, depth=self.depth+1)
                dirs[directory.tag] = directory
        self.content_dirs = dirs
        self.content_files = files


class File:
    _observers = []
    notification = "file changed"
    molecule_energy_votes = {}  # (molecular formula, int(ground state energy)):
                                            # {delta_E: [freq, fc files], 0: [ground freq file]}
    freq_voters_waiting = []  # can be attached to one of the above sub-dict entries once the delta_E's are known
    experiment_files = []
    nr_unparsed_files = 0

    def __init__(self, path, name=None, parent=None, depth=0, state=None, experiment=None, mark_as_exp=None):
        File.nr_unparsed_files += 1
        self.properties = {}
        self.is_human_readable = True  # \n instead of \r\n making it ugly in notepad
        self.type = None
        self.path = os.path.normpath(path)
        if name:
            self.name = name
        else:
            self.name = os.path.basename(path)
        self.ignored = False
        self.marked_exp = mark_as_exp  # marker for user-denoted excitation and emission experimental files
        self.routing_info = {}
        self.geometry = None  # input or last opt / freq log geom
        self.initial_geom = None  # FC initial state geometry
        self.final_geom = None    # FC final state geometry
        self.molecular_formula = None
        self.depth = depth
        self.error = None  # Contains error string if present
        self.tag = f"file_{path}_{depth}"
        self.start_lines = {}
        self.parent_directory = parent
        name, self.extension = os.path.splitext(self.name)
        self.charge = 0
        self.multiplicity = ""
        self.ground_state_energy = None  # Energy of associated ground state; == self.energy except for FREQ_EXCITED
        self.energy = None
        self.lines = None
        self.spectrum = None
        self.modes = None
        self.progress = "start"
        self.state = state  # When imported into project, references state this file belongs to.
        self.experiment = experiment  # When imported into project, references experiment this file belongs to.
        self.columns = None  # For experimental file

        self.submit_what_am_i()

    def update(self, event_type, *args):   # "file changed" notification received: start next step after what_am_I is done
        if event_type == "what_am_i done":  # Only the submitting file receives this
            self.submit_analyse_data()      # Start next step of parsing the data
            self.notify_observers()
            self.progress = event_type
        elif event_type == "parsing done":
            self.progress = event_type
            if self.state is not None:
                self.state.assimilate_file_data(self)
            if self.experiment is not None:
                self.experiment.assimilate_file_data(self)
            File.nr_unparsed_files -= 1
            self.notify_observers()  # Notify all observers of File of the update

    ############### Observers ###############

    @classmethod
    def add_observer(cls, observer):
        cls._observers.append(observer)

    @classmethod
    def remove_observer(cls, observer):
        cls._observers.remove(observer)

    def notify_observers(self):
        for observer in self._observers:
            observer.update(self.notification, self)

    def submit_what_am_i(self):
        AsyncManager.submit_task(f"File {self.tag} what_am_I", self._what_am_i, observers=[self], notification="what_am_i done")

    def submit_analyse_data(self):
        AsyncManager.submit_task(f"Analyse project file {self.tag}", self._analyse_data, observers=[self], notification="parsing done")

    def _read_file_lines(self):
        PathLockManager.acquire_read(self.path)
        lines = []
        try:
            if sys.platform.startswith("win"):
                with open(self.path, 'rb') as file:
                    content = file.read(1024)
                    self.is_human_readable = b'\r\n' in content
            with open(self.path, 'r', encoding='utf-8') as f:
                tmp_lines = [line.rstrip("\r\n") for line in f]
                if self.type in FileType.LOG_TYPES:
                    lines = [line for line in tmp_lines if line.rstrip("\r\n")]
                else:
                    lines = tmp_lines
        except Exception as e:
            print(f"File {self.path} couldn't be read! {e}")
        finally:
            PathLockManager.release_read(self.path)
        return lines

    def submit_make_readable(self):
        self.is_human_readable = True
        self.notify_observers()
        AsyncManager.submit_task(f"make {self.path} readable", self._make_readable)

    def _make_readable(self):
        path = self.path
        if os.path.exists(path):
            tmp_file_path = f"{path}.tmp"
            try:
                lines = self._read_file_lines()
                with open(tmp_file_path, 'w') as new_log:
                    for line in lines:
                        if len(line):
                            new_log.write(line.rstrip('\r\n') + '\r\n')
                os.rename(path, path+".backup")
                os.rename(tmp_file_path, path)
                os.remove(path+".backup")
            except Exception as e:
                print(f"Exception during _make_readable: {e}")

    def _what_am_i(self):
        properties = {}
        is_table = False
        lines = None
        if self.extension == ".log":  # Gaussian log
            self.type = FileType.GAUSSIAN_LOG

            lines = self._read_file_lines()

            finished, self.error, self.routing_info, self.charge, self.multiplicity, self.start_lines, self.energy = GaussianParser.scan_log_file(lines)
            for job in self.routing_info.get("jobs", []):
                if job.startswith("freq"):
                    if re.search(r"(?<![a-zA-Z])(fc|fcht|ht)", job):
                        if job.find("emission") > -1:
                            self.type = FileType.FC_EMISSION
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
            lines = self._read_file_lines()
            self.routing_info, self.charge, self.multiplicity, self.geometry = GaussianParser.parse_input(lines)
            if self.geometry is not None:
                self.molecular_formula = self.geometry.get_molecular_formula(self.charge)

        elif self.extension == ".chk":
            self.type = FileType.GAUSSIAN_CHECKPOINT
        elif self.extension == ".txt":
            try:
                lines = self._read_file_lines()
                delim, is_table = ExperimentParser.guess_delimiter_and_check_table(lines)
                properties["delimiter"] = delim
            except Exception as e:
                print(f"File {self.path} couldn't be read! {e}")
        elif self.extension in ['.csv', '.tsv', '.xlsx', '.xls', '.xlsm', '.xltx', '.xltm', '.ods']:
            is_table = True
        else:
            self.type = FileType.OTHER

        if is_table:
            if self.marked_exp is not None:
                if self.marked_exp == "excitation":
                    self.type = FileType.EXPERIMENT_EXCITATION
                else:
                    self.type = FileType.EXPERIMENT_EMISSION
            else:
                if re.search(r'DF_|fluor|emmi', self.name, re.IGNORECASE):
                    self.type = FileType.EXPERIMENT_EMISSION
                else:
                    self.type = FileType.EXPERIMENT_EXCITATION
            if self.path not in [f.path for f in File.experiment_files]:
                File.experiment_files.append(self)
        self.properties = properties
        self.lines = lines

        return self

    def _analyse_data(self):
        if self.type in FileType.LOG_TYPES and \
                (type(self.properties) != dict or self.properties.get(GaussianLog.STATUS) != GaussianLog.FINISHED):
            print(f"Skipping analysis of incomplete file {self.path}")
            return
        if self.start_lines == {}:
            self._what_am_i()
        if self.lines is None:
            self.lines = self._read_file_lines()
        if self.type in (FileType.FC_EMISSION, FileType.FC_EXCITATION):
            is_emission = self.type == FileType.FC_EMISSION
            if self.spectrum is None:
                self.spectrum = GaussianParser.get_FC_spectrum(self.lines, is_emission, start_line=self.start_lines.get("FC transitions", 0))
        if self.type in (FileType.FREQ_GROUND, FileType.FREQ_EXCITED, FileType.FC_EMISSION, FileType.FC_EXCITATION):
            if self.modes is None:
                self.modes = GaussianParser.get_vibrational_modes(self.lines, hpmodes_start=self.start_lines.get("hp freq"), lpmodes_start=self.start_lines.get("lp freq"), geometry=self.geometry)
            if self.modes.get_wavenumbers(1)[0] < 0:
                self.properties[GaussianLog.STATUS] = GaussianLog.NEGATIVE_FREQUENCY
        self.lines = None  # Forget lines now that file has been parsed.
        if self.type in (FileType.EXPERIMENT_EXCITATION, FileType.EXPERIMENT_EMISSION):
            print(f"Parsing exp file: {self.path}")
            columns = ExperimentParser.read_file_as_arrays(self.path, self.extension, self.properties.get("delimiter"))
            if columns is None:  # ran into a parsing error
                self.type = FileType.OTHER
            else:
                self.columns = columns

        if self.type in (FileType.FREQ_GROUND, FileType.FC_EMISSION, FileType.FC_EXCITATION):
            self.ground_state_energy = self.energy
            if self.energy is not None and self.molecular_formula is not None:
                molecule_energy_key = (self.molecular_formula, int(self.energy))
                delta_E = 0 if self.type == FileType.FREQ_GROUND else int(self.spectrum.zero_zero_transition_energy)
                if molecule_energy_key in self.molecule_energy_votes:
                    if delta_E in self.molecule_energy_votes[molecule_energy_key]:
                        if self.path not in [f.path for f in self.molecule_energy_votes[molecule_energy_key][delta_E]]:
                            self.molecule_energy_votes[molecule_energy_key][delta_E].append(self)
                    else:
                        self.molecule_energy_votes[molecule_energy_key][delta_E] = [self]
                else:
                    self.molecule_energy_votes[molecule_energy_key] = {delta_E: [self]}
                for waiting_freq in self.freq_voters_waiting:
                    if waiting_freq.molecular_formula == self.molecular_formula:
                        if abs(abs(waiting_freq.energy - self.energy) - delta_E) < 10:
                            self.molecule_energy_votes[molecule_energy_key][delta_E].append(waiting_freq)
                            self.freq_voters_waiting.remove(waiting_freq)
                            break
        elif self.type == FileType.FREQ_EXCITED:
            self.freq_voters_waiting.append(self)
            for key, de in self.molecule_energy_votes.items():
                if self.molecular_formula == key[0]:
                    ground_state_energy = key[1]
                    for delta_E, file_list in de.items():
                        if abs(abs(self.energy - ground_state_energy) - delta_E) < 10:
                            self.ground_state_energy = file_list[0].ground_state_energy  # get accurate one
                            if self.path not in [f.path for f in self.molecule_energy_votes[key][delta_E]]:
                                self.molecule_energy_votes[key][delta_E].append(self)
                            if self in self.freq_voters_waiting:
                                self.freq_voters_waiting.remove(self)
                            break

        return self

    @classmethod
    def get_molecule_energy_options(cls):
        ml_options = []
        for key, v in cls.molecule_energy_votes.items():
            loth_file = None
            nr_files = 0
            for file_list in v.values():
                for file in file_list:
                    if not file.ignored:
                        nr_files += 1
                        if file.type in (FileType.FREQ_GROUND, FileType.FREQ_EXCITED) and file.ground_state_energy is not None and file.progress in ("what_am_i done", "parsing done"):  # knows level of theory & basis set
                            loth_file = file
            if loth_file is not None and not nr_files == 0:
                ml_options.append((nr_files, key, f"{loth_file.molecular_formula}\t\t{loth_file.routing_info['loth']}\t\tE₀ = {int(loth_file.ground_state_energy/219474.63*100)/100.}"))
        ml_options.sort(key=lambda m: m[0], reverse=True)
        return {m[2]: m[1] for m in ml_options}  # display string: key




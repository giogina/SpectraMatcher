import os

from models.data_file_manager import File, FileType
import time


class State:
    molecular_formula = None  # todo: sync with Project Setup formula display
    ground_state_energy = None  # Used for identification of matching files. Set only by ground state file.
    state_list = []
    _observers = []
    imported_file_changed_notification = "State file changed"
    imported_files_changed_notification = "State files changed"

    # Init with parsed files
    def __init__(self, freq_file=None, emission_file=None, excitation_file=None, anharm_file=None):
        self.freq_file = freq_file
        self.anharm_file = anharm_file
        self.emission_file = emission_file
        self.excitation_file = excitation_file
        self.freq_hint = "Drag & drop file here, or click 'auto import'"
        self.anharm_hint = "Drag & drop file here, or click 'auto import'"
        self.emission_hint = "Drag & drop file here, or click 'auto import'"
        self.excitation_hint = "Drag & drop file here, or click 'auto import'"
        self.vibrational_modes = None
        self.anharm_levels = None
        self.emission_spectrum = None
        self.excitation_spectrum = None
        self.ground_geometry = None
        self.excited_geometry = None
        self.is_ground = len(self.state_list) == 0
        self.excited_state_energy = None
        self.delta_E = None
        self.tag = f"state {time.time()} {len(self.state_list)}"
        self.state_list.append(self)
        self.name = None
        self.own_ground_state_energy = None
        State.sort_states_by_energy()

        # Load from paths, if supplied.
        for path in (freq_file, emission_file, excitation_file, anharm_file):
            if path is not None:
                print(f"Reading File {path}, state {self.tag}")
                if os.path.exists(path):
                    File(path=path, parent="Project", state=self)  # will call assimilate_file_data when done parsing
                else:
                    print(f"WARNING: File {path} not found. Ignoring.")

        self._notify_observers(self.imported_files_changed_notification)  # New state, redraw all

    @classmethod
    def add_observer(cls, observer):
        cls._observers.append(observer)

    @classmethod
    def remove_observer(cls, observer):
        cls._observers.remove(observer)

    def _notify_observers(self, message):
        for o in self._observers:
            print(f"Updating state observers: {message}")
            o.update(message, self)

    def import_file(self, file):
        print(f"Importing file: {file.name, file.type, file.progress}")
        file.state = self
        if file.progress == "parsing done":
            self.assimilate_file_data(file)  # if not, the file will call that function upon completion.

    # todo: further checks:
    #  * all states need the same ground state energy (select? Majority vote?)
    #  * are subsequent states the same? (Correlate spectra)
    #  * automatic scan & add (group by delta_E? Once I have general ground state energy, that'd be easy)

    def assimilate_file_data(self, file: File):
        if file.progress != "parsing done":
            print(f"Warning in molecular_data assimilate_file_data: File wasn't done parsing yet: {file.path}")
            return
        if file.type == FileType.FREQ_GROUND:
            if not self.is_ground:
                print("File rejected: Can't have two ground states.")
                self.freq_hint = "File rejected: Can't have two ground states."
                return
            self.freq_file = file.path
            self.molecular_formula = file.molecular_formula
            self.ground_state_energy = file.energy
            self.own_ground_state_energy = file.energy
            self.delta_E = 0  # just to keep it in the front
            self.vibrational_modes = file.modes

            for s in self.state_list:
                if s.own_ground_state_energy is not None:
                    if abs(s.own_ground_state_energy - self.ground_state_energy) > 1:
                        print(f"Imported new ground state file with different energy! Wiping {s.name}.")
                        s.wipe()

        elif file.type == FileType.FREQ_EXCITED:
            gse = self.ground_state_energy if self.ground_state_energy is not None else self.own_ground_state_energy
            if gse is not None:
                delta_E = abs(file.energy - gse) * 219474.63
                if self.delta_E is not None:  # 0-0 transition energy known from FC file
                    if abs(delta_E - self.delta_E) > 20:
                        self.freq_hint = "File rejected: New freq file energy does not match previously added files."
                        self._notify_observers(self.imported_file_changed_notification)
                        return
                else:
                    self.delta_E = delta_E
                State.sort_states_by_energy()
            self.freq_file = file.path
            self.vibrational_modes = file.modes
        elif file.type == FileType.FC_EXCITATION:
            if self.delta_E is not None:
                if abs(self.delta_E - file.spectrum.zero_zero_transition_energy) > 20:
                    self.excitation_hint = "File rejected: New file 0-0 transition energy doesn't match previously added files."
                    self._notify_observers(self.imported_file_changed_notification)
                    return
            if self.ground_state_energy is not None and abs(self.ground_state_energy - file.energy) > 1:
                self.excitation_hint = "File rejected: Ground state energy doesn't match selected ground state."
                self._notify_observers(self.imported_file_changed_notification)
                return
            self.excitation_file = file.path
            self.delta_E = file.spectrum.zero_zero_transition_energy  # just to get the accurate one
            self.own_ground_state_energy = file.energy  # in case of being added before ground state file
            State.sort_states_by_energy()
            self.excitation_spectrum = file.spectrum
            self.excited_geometry = file.final_geom
            self.ground_geometry = file.initial_geom
        elif file.type == FileType.FC_EMISSION:
            if self.delta_E is not None:
                if abs(self.delta_E - file.spectrum.zero_zero_transition_energy) > 20:
                    self.emission_hint = "File rejected: 0-0 transition energy doesn't match previously added files."
                    self._notify_observers(self.imported_file_changed_notification)
                    return
            if self.ground_state_energy is not None and abs(self.ground_state_energy - file.energy) > 1:
                self.emission_hint = "File rejected: Ground state energy doesn't match selected ground state."
                self._notify_observers(self.imported_file_changed_notification)
                return
            self.emission_file = file.path
            self.delta_E = file.spectrum.zero_zero_transition_energy
            self.own_ground_state_energy = file.energy
            State.sort_states_by_energy()
            self.emission_spectrum = file.spectrum
            self.excited_geometry = file.initial_geom
            self.ground_geometry = file.final_geom
        self._notify_observers(self.imported_file_changed_notification)

    @classmethod
    def sort_states_by_energy(cls):
        cls.state_list.sort(key=lambda x: (x.delta_E is None, x.delta_E))
        for i, state in enumerate(cls.state_list):
            if i == 0:
                if not state.is_ground:
                    print("WARNING: 0th state somehow not ground state")
                state.name = "Ground state"
            elif i == 1:
                state.name = "1st excited state"
            elif i == 2:
                state.name = "2nd excited state"
            elif i == 3:
                state.name = "3rd excited state"
            else:
                state.name = f"{i}th excited state"

    def wipe(self):
        """Restore a clean slate"""
        self.freq_file = None
        self.anharm_file = None
        self.emission_file = None
        self.excitation_file = None
        self.freq_hint = "Drag & drop file here, or click 'auto import'"
        self.anharm_hint = "Drag & drop file here, or click 'auto import'"
        self.emission_hint = "Drag & drop file here, or click 'auto import'"
        self.excitation_hint = "Drag & drop file here, or click 'auto import'"
        self.vibrational_modes = None
        self.anharm_levels = None
        self.emission_spectrum = None
        self.excitation_spectrum = None
        self.ground_geometry = None
        self.excited_geometry = None
        self.excited_state_energy = None
        self.delta_E = None
        self.name = None
        self.own_ground_state_energy = None
        self._notify_observers(self.imported_file_changed_notification)

    # def load_from_paths(self, state_data: StateData):
    #     pass  # todo
    #

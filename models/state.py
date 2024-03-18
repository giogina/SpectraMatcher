import math
import os

from models.data_file_manager import File, FileType
from utility.spectrum_plots import hsv_to_rgb
import time


class State:
    # Used for identification of matching files. Set only by select_molecule_and_ground_state_energy, or from project.
    molecule_and_method = {"molecule": None, "ground state energy": None}  # coupled to project._data
    state_list = []
    _observers = []
    imported_file_changed_notification = "State file changed"
    imported_files_changed_notification = "State files changed"
    state_ok_notification = "State ok"

    # Init with parsed files
    # def __init__(self, freq_file=None, emission_file=None, excitation_file=None, anharm_file=None):
    def __init__(self, settings=None):
        if settings is None:
            settings = {}
        self.settings = settings  # coupled to project._data
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
        self.delta_E = 0 if self.is_ground else None
        self.tag = f"state {time.time()} {len(self.state_list)}"
        self.state_list.append(self)
        self.name = None
        self.own_molecular_formula = None
        self.own_ground_state_energy = None
        self.ok = False
        self.errors = []
        self.color = None
        State.sort_states_by_energy()

        # Load from paths, if supplied.
        for path_key in ("freq file", "emission file", "excitation file", "anharm file"):
            path = self.settings.get(path_key)
            if path is not None:
                print(f"Reading File {path}, state {self.tag}")
                if os.path.exists(path):
                    File(path=path, parent="Project", state=self, depth=-len(State.state_list)-1)  # will call assimilate_file_data when done parsing
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

    def get_spectrum(self, is_emission):
        if is_emission and self.emission_spectrum is not None:
            return self.emission_spectrum
        elif not is_emission and self.excitation_spectrum is not None:
            return self.excitation_spectrum
        return None

    def check(self):
        """Confirm integrity of own data"""
        self.errors = []
        if self.molecule_and_method.get("ground state energy") is None:
            self.errors.append("Ground state energy unknown")
            self.ok = False
            return self.ok
        if self.molecule_and_method.get("molecule") is None:
            self.errors.append("Molecule unknown")
            self.ok = False
            return self.ok
        if self.own_ground_state_energy is None:
            self.errors.append("Own ground state energy unknown")
            self.ok = False
            return self.ok
        if not math.isclose(self.own_ground_state_energy, self.molecule_and_method.get("ground state energy"), abs_tol=10):
            self.errors.append(f"Wrong ground state energy: {self.own_ground_state_energy} vs. global {self.molecule_and_method.get('ground state energy')}")
        if not self.molecule_and_method.get("molecule") == self.own_molecular_formula:
            self.errors.append(f"Wrong molecule: {self.own_molecular_formula} vs. global {self.molecule_and_method.get('molecule')}")
        if self.vibrational_modes is None:
            self.errors.append(f"No vibrational modes found.")
        if not self.is_ground and self.excitation_spectrum is None:
            self.errors.append(f"No excitation spectrum found.")
        if not self.is_ground and self.emission_spectrum is None:
            self.errors.append(f"No emission spectrum found.")

        self.ok = len(self.errors) == 0
        if not self.ok:
            print(f"Error in self-check of {self.name}:")
            for error in self.errors:
                print(error)
        if self.ok:
            if not self.is_ground:
                ground = State.state_list[0]
                if ground.is_ground and ground.ok:
                    self.emission_spectrum.set_vibrational_modes(ground.vibrational_modes)
                self.excitation_spectrum.set_vibrational_modes(self.vibrational_modes)
            else:
                for state in State.state_list[1:]:
                    if state.ok and state.emission_spectrum is not None:
                        state.emission_spectrum.set_vibrational_modes(self.vibrational_modes)
            self._notify_observers(self.state_ok_notification)
        return self.ok

    def import_file(self, file):
        file.state = self
        if file.progress == "parsing done":
            self.assimilate_file_data(file)  # if not, the file will call that function upon completion.

    @classmethod
    def select_molecule_and_ground_state_energy(cls, molecule, ground_state_energy):
        cls.molecule_and_method["molecule"] = molecule
        cls.molecule_and_method["ground state energy"] = ground_state_energy
        cls.state_list = [s  # wipe states that won't fit.
                          if (s.own_ground_state_energy is None or abs(s.own_ground_state_energy - ground_state_energy) < 1)
                          and (s.own_molecular_formula is None or s.own_molecular_formula == molecule) else s.wipe()
                          for s in cls.state_list]

    def assimilate_file_data(self, file: File):
        if file.progress != "parsing done":
            print(f"Warning in molecular_data assimilate_file_data: File wasn't done parsing yet: {file.path}")
            return
        if State.molecule_and_method.get("molecule") is None:
            if file.ground_state_energy is not None:  # allow file choice to select molecule
                State.select_molecule_and_ground_state_energy(file.molecular_formula, file.ground_state_energy)
        elif file.molecular_formula != State.molecule_and_method["molecule"]:
            print("File rejected: Different molecule!")
            self.freq_hint = "File rejected: Different molecule!"
            self._notify_observers(self.imported_file_changed_notification)
            return
        elif file.ground_state_energy is not None and abs(file.ground_state_energy - State.molecule_and_method.get("ground state energy"))>1:
            print("File rejected: Belongs to a different ground state energy!")
            self.freq_hint = "File rejected: Belongs to a different ground state energy!"
            self._notify_observers(self.imported_file_changed_notification)
            return
        old_order = [x.delta_E for x in self.state_list]

        if file.type == FileType.FREQ_GROUND:
            if not self.is_ground:
                print("File rejected: Can't have two ground states.")
                self.freq_hint = "File rejected: Can't have two ground states."
                self._notify_observers(self.imported_file_changed_notification)
                return

            self.settings["freq file"] = file.path
            self.own_molecular_formula = file.molecular_formula
            self.own_ground_state_energy = file.energy
            self.delta_E = 0  # just to keep it in the front
            self.vibrational_modes = file.modes

        elif file.type == FileType.FREQ_EXCITED:
            gse = file.ground_state_energy if file.ground_state_energy is not None else self.own_ground_state_energy
            if gse is not None:
                delta_E = abs(file.energy - gse)
                if self.delta_E is not None:  # 0-0 transition energy known from FC file
                    if abs(delta_E - self.delta_E) > 20:
                        self.freq_hint = "File rejected: New freq file energy does not match previously added files."
                        self._notify_observers(self.imported_file_changed_notification)
                        return
                else:
                    self.delta_E = delta_E
                State.sort_states_by_energy()
            self.settings["freq file"] = file.path
            self.own_molecular_formula = file.molecular_formula
            self.vibrational_modes = file.modes
        elif file.type == FileType.FC_EXCITATION:
            if self.delta_E is not None:
                if abs(self.delta_E - file.spectrum.zero_zero_transition_energy) > 20:
                    self.excitation_hint = "File rejected: New file 0-0 transition energy doesn't match previously added files."
                    self._notify_observers(self.imported_file_changed_notification)
                    return
            if self.own_ground_state_energy is not None and abs(self.own_ground_state_energy - file.energy) > 1:
                self.excitation_hint = "File rejected: Ground state energy doesn't match selected ground state."
                self._notify_observers(self.imported_file_changed_notification)
                return
            self.settings["excitation file"] = file.path
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
            if self.own_ground_state_energy is not None and abs(self.own_ground_state_energy - file.energy) > 1:
                self.emission_hint = "File rejected: Ground state energy doesn't match selected ground state."
                self._notify_observers(self.imported_file_changed_notification)
                return
            self.settings["emission file"] = file.path
            self.delta_E = file.spectrum.zero_zero_transition_energy
            self.own_ground_state_energy = file.energy

            State.sort_states_by_energy()

            self.emission_spectrum = file.spectrum
            self.excited_geometry = file.initial_geom
            self.ground_geometry = file.final_geom
        if old_order != [x.delta_E for x in self.state_list]:
            self._notify_observers(self.imported_files_changed_notification)
        else:
            self._notify_observers(self.imported_file_changed_notification)
        file.state = None  # remove state from file to avoid future interferences
        self.check()

    @classmethod
    def sort_states_by_energy(cls):
        cls.state_list.sort(key=lambda x: (x.delta_E is None, x.delta_E))
        for state in cls.state_list:
            print("Color before: ", state.color)
        for i, state in enumerate(cls.state_list):
            # if state.settings.get("color") is None:
            # state.settings["color"] = hsv_to_rgb((i-1)/(len(cls.state_list)), 0.9, 0.9)
            state.color = hsv_to_rgb(i/len(cls.state_list), 0.9, 0.9)
            print("Determine colors: ", i, len(cls.state_list), i/len(cls.state_list)*255, state.color)
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

        for state in cls.state_list:
            print("Color after: ", state.color)

    def wipe(self):
        """Restore a clean slate"""
        self.settings = {}
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

    @classmethod
    def auto_import(cls):
        ground_state_energy = cls.molecule_and_method.get("ground state energy")
        if ground_state_energy is not None:
            chosen_key = (cls.molecule_and_method.get("molecule"), int(ground_state_energy))
            file_structure = File.molecule_energy_votes.get(chosen_key)
            if file_structure is not None:
                for state in State.state_list:
                    del state
                State.state_list = []
                delta_E_list = list(file_structure.keys())
                if len(delta_E_list) > 0:
                    delta_E_list.sort()
                    if delta_E_list[0] == 0:  # there is a ground state file
                        for file in file_structure[delta_E_list[0]]:
                            if not file.ignored:
                                s = State()
                                s.is_ground = True
                                s.assimilate_file_data(file)
                                break
                        delta_E_list = delta_E_list[1:]
                    for delta_E in delta_E_list:
                        s = State()
                        s.is_ground = False
                        for file in file_structure.get(delta_E, []):
                            if not file.ignored:
                                s.assimilate_file_data(file)

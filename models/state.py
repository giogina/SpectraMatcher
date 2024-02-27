from models.data_file_manager import File, FileType


class State:
    molecular_formula = None  # todo: sync with Project Setup formula display

    # Init with parsed files
    def __init__(self):
        self.freq_file = None
        self.anharm_file = None
        self.emission_file = None
        self.excitation_file = None
        self.vibrational_modes = None
        self.anharm_levels = None
        self.emission_spectrum = None
        self.excitation_spectrum = None
        self.ground_geometry = None
        self.excited_geometry = None
        self.is_ground = False
        self.ground_state_energy = None
        self.excited_state_energy = None
        self.delta_E = None

    # todo: check energy from

    def import_file(self, file):
        print(f"Importing file: {file.name, file.type, file.progress}")
        file.state = self
        if file.type in (FileType.FREQ_GROUND, FileType.FREQ_EXCITED):
            self.freq_file = file
        elif file.type == FileType.FC_EXCITATION:
            self.excitation_file = file
        elif file.type == FileType.FC_EMISSION:
            self.emission_file = file
        if file.progress == "parsing done":
            self.assimilate_file_data(file)  # if not, the file will call that function upon completion.

    def assimilate_file_data(self, file: File):
        if file.progress != "parsing done":
            print(f"Warning in molecular_data assimilate_file_data: File wasn't done parsing yet: {file.path}")
            return
        if file.type == FileType.FREQ_GROUND:
            self.is_ground = True
            self.ground_state_energy = file.energy
            self.vibrational_modes = file.modes
        elif file.type == FileType.FREQ_EXCITED:
            delta_E = abs(file.energy - self.ground_state_energy) * 219474.63
            print(delta_E, self.delta_E)
            if self.ground_state_energy is not None:  # ground state & 0-0 transition energy known from FC file
                if abs(delta_E - self.delta_E) > 20:
                    print("File rejected: New freq file energy does not match previously added files.")
                    return
            self.delta_E = delta_E
            self.vibrational_modes = file.modes
            self.is_ground = False
        elif file.type == FileType.FC_EXCITATION:
            print(file.spectrum.zero_zero_transition_energy, self.delta_E)
            if self.delta_E is not None:
                if abs(self.delta_E - file.spectrum.zero_zero_transition_energy) > 20:
                    print("File rejected: New file 0-0 transition energy doesn't match previously added files.")
                    return
            self.delta_E = file.spectrum.zero_zero_transition_energy  # just to get the accurate one
            self.ground_state_energy = file.energy
            self.excitation_spectrum = file.spectrum
            self.excited_geometry = file.final_geom
            self.ground_geometry = file.initial_geom
        elif file.type == FileType.FC_EMISSION:
            print(file.spectrum.zero_zero_transition_energy, self.delta_E)
            if self.delta_E is not None:
                if abs(self.delta_E - file.spectrum.zero_zero_transition_energy) > 20:
                    print("File rejected: 0-0 transition energy doesn't match previously added files.")
                    return
            self.delta_E = file.spectrum.zero_zero_transition_energy
            self.ground_state_energy = file.energy
            self.emission_spectrum = file.spectrum
            self.excited_geometry = file.initial_geom
            self.ground_geometry = file.final_geom



    # def load_from_paths(self, state_data: StateData):
    #     pass  # todo
    #

from models.settings_manager import SettingsManager, Settings
from models.project import Project, ProjectObserver, StateData, ExperimentalSpectrum
from models.data_file_manager import File, DataFileManager
from models.state import State
from copy import deepcopy


def noop(*args, **kwargs):
    pass


class StateViewModel:

    def __init__(self, state: StateData):
        self.state = 0  # 0: Ground, 1+: excited
        self.freq_file_path = None
        self.fc_emission_path = None
        self.fc_excitation_path = None
        for key, value in state.__dict__.items():
            setattr(self, key, deepcopy(value))


class ExperimentalSpectrumViewModel:

    def __init__(self, exp: ExperimentalSpectrum):
        for key, value in exp.__dict__.items():
            setattr(self, key, deepcopy(value))


class ProjectSetupViewModel(ProjectObserver):

    def __init__(self, project: Project):
        self._callbacks = {
            "update project": noop,
            "update state data": noop,
            "update states data": noop,
            "update experimental data": noop
        }
        self._project = project
        self._project.add_observer(self, "project data changed")
        self._project.add_observer(self, "state data changed")
        self._project.add_observer(self, "experimental data changed")
        State.add_observer(self)
        File.add_observer(self)
        self.settings = SettingsManager()

        # # todo> temp
        # self.states = {0: State(), 1: State(), 2: State()}
        # self.states[0].is_ground = True

    def set_callback(self, key, callback):
        if key in self._callbacks.keys():
            self._callbacks[key] = callback
        else:
            print(f"Warning: In ProjectSetupViewModel: Attempted to set unknown callback key {key}")

    def update(self, event_type, *args):
        print(f"ProjectSetupViewModel observed event: {event_type, *args}")
        if event_type == "project data changed":
            if self._project is not None:
                self._callbacks.get("update project")()
        elif event_type == "file changed":
            self._callbacks.get("update project")()
        elif event_type == State.imported_file_changed_notification:
            print(args[0].freq_file, args[0].excitation_file, args[0].emission_file)
            self._callbacks.get("update project")()
            self._callbacks.get("update state data")(args[0])
        elif event_type == State.imported_files_changed_notification:
            self._callbacks.get("update project")()
            self._callbacks.get("update states data")()
        # elif event_type == "state data changed":
        #     if len(args) and len(args[0]) and type(args[0][0]) == int:  # Update only one
        #         state = self._project.get("states", {}).get(args[0][0])
        #         if state is not None:
        #             self._callbacks.get("update state data")(StateViewModel(state))
        #     else:  # update all of them
        #         states_data = {k: StateViewModel(s) for k, s in self._project.get("states").items()}
        #         self._callbacks.get("update states data")(states_data)
        # elif event_type == "experimental data changed":
        #     exp_data = {k: ExperimentalSpectrumViewModel(e) for k, e in self._project.get("experimental spectra").items()}
        #     self._callbacks.get("update experimental data")(exp_data)

    # todo: "reset states" option (called when user changes molecule&loth selection, or on button press)

    def get_project_name(self):
        return self._project.get("name", "")

    def get_mlo_list(self):
        return [f"{mlo[0]}    {mlo[2].routing_info['loth']}     ---     {mlo[2].path}" for mlo in File.molecule_loth_options]

    def get_selected_mlo_path(self):
        return self._project.get_selected_ground_state_file()
        # if selected_path is not None:
        #     file = DataFileManager.get_file_by_path(selected_path)
        # if file is not None:
        #     return f"{file.molecular_formula}    {file.routing_info['loth']}     ---     {file.path}"

    def print_args(self, *args):
        print(f"project setup viewmodel got: {args}")

    def add_state(self):
        self._project.add_state()

    def select_ground_state_file(self, list_str):
        """Ground state file selected in top-level dropdown"""
        path = list_str.split('   ---   ')[-1].strip()
        for m in File.molecule_loth_options:
            if m[2].path == path:
                self.import_state_file(m[2], State.state_list[0])
                break

    def import_state_file(self, file, state: State):
        state.import_file(file)
        if state.is_ground:
            self._project.select_ground_state_file(file.path)
        else:
            self._project.copy_state_files()
        self._callbacks.get("update project")()

    def delete_state(self, state: int):
        self._project.delete_state(state)

    def set_experimental_file(self, file_path):
        print(file_path)
        self._project.set_experimental_file(file_path)

    def delete_experimental_file(self, file_path):
        self._project.delete_experimental_file(file_path)


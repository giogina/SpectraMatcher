from models.settings_manager import SettingsManager, Settings
from models.project import Project, ProjectObserver, StateData, ExperimentalSpectrum
from models.data_file_manager import FileType
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
            "update state data": noop,
            "update states data": noop,
            "update experimental data": noop
        }
        self._project = project
        self._project.add_observer(self, "state data changed")
        self._project.add_observer(self, "experimental data changed")
        self.settings = SettingsManager()

    def get_project_name(self):
        return self._project.get("name", "")

    def set_callback(self, key, callback):
        if key in self._callbacks.keys():
            self._callbacks[key] = callback
        else:
            print(f"Warning: In ProjectSetupViewModel: Attempted to set unknown callback key {key}")

    def update(self, event_type, *args):
        print(f"ProjectSetupViewModel observed event: {event_type, *args}")
        if event_type == "state data changed":
            if len(args) and len(args[0]) and type(args[0][0]) == int:  # Update only one
                state = self._project.get("states", {}).get(args[0][0])
                if state is not None:
                    self._callbacks.get("update state data")(StateViewModel(state))
            else:  # update all of them
                states_data = {k: StateViewModel(s) for k, s in self._project.get("states").items()}
                self._callbacks.get("update states data")(states_data)
        elif event_type == "experimental data changed":
            exp_data = {k: ExperimentalSpectrumViewModel(e) for k, e in self._project.get("experimental spectra").items()}
            self._callbacks.get("update experimental data")(exp_data)

    def add_state(self):
        self._project.add_state()

    def import_state_file(self, path, file_type, state: int):
        self._project.set_state_file(path, file_type, state)

    def delete_state(self, state: int):
        self._project.delete_state(state)

    def set_experimental_file(self, file_path):
        print(file_path)
        self._project.set_experimental_file(file_path)

    def delete_experimental_file(self, file_path):
        self._project.delete_experimental_file(file_path)


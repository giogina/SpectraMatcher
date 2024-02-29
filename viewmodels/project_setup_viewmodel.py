from models.settings_manager import SettingsManager
from models.project import Project, ProjectObserver
from models.data_file_manager import File
from models.state import State
from copy import deepcopy


def noop(*args, **kwargs):
    pass

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
        self.mlo_options = {}  # temporary storage of Energy / molecule / level of theory options: {display string: key}

    def set_callback(self, key, callback):
        if key in self._callbacks.keys():
            self._callbacks[key] = callback
        else:
            print(f"Warning: In ProjectSetupViewModel: Attempted to set unknown callback key {key}")

    def update(self, event_type, *args):
        # print(f"ProjectSetupViewModel observed event: {event_type, *args}")
        if event_type == "project data changed":
            if self._project is not None:
                self._callbacks.get("update project")()
        elif event_type == "file changed":
            self._callbacks.get("update project")()
        elif event_type == State.imported_file_changed_notification:
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

    def auto_import(self):
        if len(self.mlo_options.keys()) == 0:
            print("Auto-import failure: Ground state energy could not be identified.")
            return
        if State.molecule_and_method.get("ground state energy") is None:  # Nothing selected, act as if first mlo was clicked
            self.select_mlo(list(self.mlo_options.keys())[0])
        State.auto_import()
        self._project.copy_state_settings()

    def get_project_name(self):
        return self._project.get("name", "")

    def print_args(self, *args):
        print(f"project setup viewmodel got: {args}")

    def add_state(self):
        State()
        self._callbacks.get("update states data")()
        self._project.copy_state_settings()

    def get_mlo_list(self):
        self.mlo_options = File.get_molecule_energy_options()
        dropdown_items = list(self.mlo_options.keys())
        if len(dropdown_items) == 0:
            return [], None
        chosen_str = dropdown_items[0]
        chosen_key = (State.molecule_and_method.get("molecule"), int(State.molecule_and_method.get("ground state energy", -1)))
        if chosen_key in self.mlo_options.values():  # Previously selected entry
            chosen_str = dropdown_items[list(self.mlo_options.values()).index(chosen_key)]
        print(f"MLO chosen key: {chosen_key}, string: {chosen_str}")
        return dropdown_items, chosen_str

    def select_mlo(self, list_str):  #todo: auto import: also treat as selecteing a key. Doublecheck state sanity checks.
        """Molecule & level of theory option selected in top-level dropdown"""
        key = self.mlo_options.get(list_str)
        State.select_molecule_and_ground_state_energy(*key)
        self._project.project_unsaved()

    def import_state_file(self, file, state: State):
        state.import_file(file)
        if state.is_ground:
            self._project.select_ground_state_file(file.path)
        else:
            self._project.copy_state_settings()
        self._callbacks.get("update project")()

    def hide_state(self, state: State, hide=True):
        state.settings["hidden"] = hide
        self._callbacks.get("update state data")(state)

    def delete_state(self, state: State):
        if state in State.state_list:
            State.state_list.remove(state)
        self._callbacks.get("update states data")()
        self._project.copy_state_settings()

    def set_experimental_file(self, file_path):
        print(file_path)
        self._project.set_experimental_file(file_path)

    def delete_experimental_file(self, file_path):
        self._project.delete_experimental_file(file_path)


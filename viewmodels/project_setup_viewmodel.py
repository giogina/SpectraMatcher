from models.experimental_spectrum import ExperimentalSpectrum
from models.settings_manager import SettingsManager
from models.project import Project, ProjectObserver
from models.data_file_manager import File, FileType
from models.state import State


def noop(*args, **kwargs):
    pass


class ProjectSetupViewModel(ProjectObserver):

    def __init__(self, project: Project):
        self._callbacks = {
            "dialog": noop,
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
        ExperimentalSpectrum.add_observer(self)
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
        elif event_type == ExperimentalSpectrum.new_spectrum_notification:
            self._callbacks.get("update experimental data")()

    def auto_import(self, *args):
        ExperimentalSpectrum.spectra_list = []
        for file in File.experiment_files:
            if not file.ignored and file.type in (FileType.EXPERIMENT_EMISSION, FileType.EXPERIMENT_EXCITATION):
                ExperimentalSpectrum(file)
        self._project.copy_experiment_settings()

        if len(self.mlo_options.keys()) == 0:
            print("Auto-import failure: Ground state energy could not be identified.")
            return
        if State.molecule_and_method.get("ground state energy") is None:  # Nothing selected, act as if first mlo was clicked
            self.select_mlo(list(self.mlo_options.keys())[0])
        State.auto_import()
        self._project.copy_state_settings()

    def get_project_name(self):
        return self._project.get("name", "")

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
        if State.molecule_and_method.get("ground state energy") is not None:
            chosen_key = (State.molecule_and_method.get("molecule"), int(State.molecule_and_method.get("ground state energy", -1)))
            if chosen_key in self.mlo_options.values():  # Previously selected entry
                chosen_str = dropdown_items[list(self.mlo_options.values()).index(chosen_key)]
            return dropdown_items, chosen_str
        else:
            return [], ""

    def select_mlo(self, list_str):
        """Molecule & level of theory option selected in top-level dropdown"""
        key = self.mlo_options.get(list_str)
        State.select_molecule_and_ground_state_energy(*key)
        self._project.project_unsaved()

    def import_state_file(self, file, state_index):
        state = State.state_list[state_index]
        state.import_file(file)
        if state.is_ground:
            self._project.select_ground_state_file(file.path)
        else:
            self._project.copy_state_settings()
        self._callbacks.get("update project")()

    def hide_state(self, state_index, hide=True):
        state = State.state_list[state_index]
        state.settings["hidden"] = hide
        self._callbacks.get("update state data")(state)

    def delete_state(self, state_index):
        state = State.state_list[state_index]
        if state in State.state_list:
            State.state_list.remove(state)
        self._callbacks.get("update states data")()
        self._project.copy_state_settings()

    def import_experimental_file(self, file: File):
        ExperimentalSpectrum(file)
        self._project.copy_experiment_settings()

    def delete_experimental_file(self, exp: ExperimentalSpectrum):
        if exp in ExperimentalSpectrum.spectra_list:
            ExperimentalSpectrum.remove(exp)
        self._callbacks.get("update experimental data")()
        self._project.copy_experiment_settings()

    def import_done(self, *args):
        for state in State.state_list:
            if not state.check():
                self._callbacks.get("dialog")(title=f"Errors in data of {state.name}", message='\n'.join(state.errors))
                return
        for spec in ExperimentalSpectrum.spectra_list:
            if not spec.check():
                self._callbacks.get("dialog")(title=f"Errors in data of {spec.name}", message='\n'.join(spec.errors))
                return
        self._project.update_progress("import done")

from models.settings_manager import SettingsManager, Settings
from models.project import Project, ProjectObserver


def noop(*args, **kwargs):
    pass


class ProjectSetupViewModel(ProjectObserver):
    _callbacks = {
        "update project data": noop
    }

    def __init__(self, project: Project):
        self._project = project
        self._project.add_observer(self, "imported project data changed")
        self.settings = SettingsManager()

    def set_callback(self, key, callback):
        if key in self._callbacks.keys():
            self._callbacks[key] = callback
        else:
            print(f"Warning: In ProjectSetupViewModel: Attempted to set unknown callback key {key}")

    def update(self, event_type, *args):
        print(f"ProjectSetupViewModel observed event: {event_type, *args}")
        if event_type == "imported project data changed":  # TODO> Send notification from project
            self._callbacks.get("update project data")(*args)


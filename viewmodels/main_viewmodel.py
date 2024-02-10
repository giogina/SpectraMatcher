from models.project import ProjectObserver
from models.project import Project
from models.settings_manager import SettingsManager
from launcher import Launcher
import time

def noop(*args, **kwargs):
    pass

class MainViewModel(ProjectObserver):
    def __init__(self, path, title_callback=noop, inquire_close_unsaved_project_callback=noop):
        self.path = path
        self._project = None
        self._project_unsaved = False

        self._settings = SettingsManager()

        self._title_callback = title_callback
        self._message_callback = noop
        self._inquire_close_unsaved_project = inquire_close_unsaved_project_callback

    def load_project(self):
        self._project = Project(self.path)
        if self._project.check_newer_autosave():
            print(f"attempting to set message...")
            self._message_callback(title="Newer autosave detected!", message="Restore autosave?",
                                   buttons=[("Yes", self._restore_autosave),
                                            ("No", self._load)])
        else:
            self._load()

    def _load(self, auto=False):
        self._project.load(auto)
        self._project.add_observer(self, "project_unsaved")
        self._title_callback(self._assemble_window_title())

    def _restore_autosave(self):
        self._load(auto=True)

    def _assemble_window_title(self):
        title = self._project.window_title
        if self._project_unsaved:
            title = "*" + title
        return title

    def update(self, event_type="all", *args):
        if event_type == "all":
            self._title_callback(self._assemble_window_title())
        elif event_type == "project_unsaved":
            if args and not args[0] == self._project_unsaved:  # If saved status changed, adjust window title.
                self._project_unsaved = args[0]
                self._title_callback(self._assemble_window_title())
        elif event_type == "Project file not found":
            pass
            #TODO> Dialog, close project / open another

    def set_title_callback(self, callback):
        self._title_callback = callback

    def set_message_callback(self, callback):
        self._message_callback = callback

    def set_inquire_close_unsaved_callback(self, callback):
        self._inquire_close_unsaved_project = callback

    def on_save(self):
        self._project.save()

    def on_save_as(self, file):
        self._project.save_as(new_file=file)

    def on_new(self):
        Launcher.launch_new()

    def on_open(self, file):
        Launcher.open(file)

    def on_close(self):
        if self._project is None:
            return True
        if self._project_unsaved or self._project.check_newer_autosave():
            response = self._inquire_close_unsaved_project()  # User either saves, discards (return true) or cancels
            if response == "discard":
                self._project.close_project(close_anyway=True)
                return True
            elif response == "save":
                self._project.save_and_close_project()
                return True
            elif type(response) == tuple and response[0] == "save as":
                self._project.save_as(response[1])
                return True
            else:
                return False
        else:
            self._project.close_project()
            return True

    def get_setting(self, key, default=None):
        return self._settings.get(key, default)

    def get(self, key, default=None):
        return self._project.get(key, None)

    def restore_default_shortcuts(self):
        self._settings.reset_shortcuts()

    def set_shortcut(self, action, shortcut):
        self._settings.set_shortcut(action, shortcut)

    def get_shortcuts(self):
        return self._settings.get("shortcuts")

    def get_recents(self):
        """List of recently opened paths without the current one."""
        current = self.path.replace("\\", "/")
        recents = self.get_setting("recentProjects")
        recents.remove(current)
        return recents




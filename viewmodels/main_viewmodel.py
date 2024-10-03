from models.project import ProjectObserver
from models.project import Project
from models.settings_manager import SettingsManager
from utility.icons import Icons
from viewmodels.data_files_viewmodel import DataFileViewModel
from viewmodels.plots_overview_viewmodel import PlotsOverviewViewmodel
from viewmodels.project_setup_viewmodel import ProjectSetupViewModel
from launcher import Launcher
from utility.system_file_browser import inquire_close_unsaved
from utility.async_manager import AsyncManager


def noop(*args, **kwargs):
    pass


class MainViewModel(ProjectObserver):
    def __init__(self, path, title_callback=noop, inquire_close_unsaved_project_callback=noop):
        self.path = path
        self._project = Project(self.path)
        self._project_unsaved = False
        self.project_setup_viewmodel = None
        self._settings = SettingsManager()

        AsyncManager.start()

        self._title_callback = title_callback
        self._message_callback = noop
        self._switch_tab_callback = noop

    # Spawn child view models responsible for child windows.
    def get_file_manager_viewmodel(self):
        return DataFileViewModel(self._project.data_file_manager, self._project)

    def get_project_setup_viewmodel(self):
        if self.project_setup_viewmodel is None:
            self.project_setup_viewmodel = ProjectSetupViewModel(self._project)
            self.project_setup_viewmodel.set_callback("dialog", self._message_callback)
        return self.project_setup_viewmodel

    def get_plots_overview_viewmodel(self, is_emission):
        return PlotsOverviewViewmodel(self._project, is_emission)

    def load_project(self):
        if self._project.check_newer_autosave():
            print(f"attempting to set message...")
            self._message_callback(title="Newer autosave detected!", message="Restore autosave?",
                                   buttons=[("Yes", self._restore_autosave),
                                            ("No", self._load)])
        else:
            self._load()

    def _load(self, auto=False):
        self._project.add_observer(self, "project_unsaved")
        self._project.add_observer(self, "progress updated")
        self._project.add_observer(self, "Project file not found")
        self._project.load(auto)
        self._title_callback(self._assemble_window_title())

    def _restore_autosave(self):
        self._load(auto=True)

    def _assemble_window_title(self):
        title = self._project.window_title
        if self._project_unsaved:
            title = "*" + title
        return title

    def update(self, event_type="all", *args):
        # print(f"Main VM received event: {event_type, args}")
        if event_type == "all":
            self._title_callback(self._assemble_window_title())
        elif event_type == "project_unsaved":
            if args and not args[0][0] == self._project_unsaved:  # If saved status changed, adjust window title.
                self._project_unsaved = args[0][0]
                self._title_callback(self._assemble_window_title())
        elif event_type == "Project file not found":
            self._message_callback("Project file not found", "This project file does not exist.", icon=Icons.x_circle, buttons=[("Ok", noop)])
        elif event_type == "progress updated":
            self._switch_tab_callback(self._project.get("progress"))

    def set_title_callback(self, callback):
        self._title_callback = callback

    def set_message_callback(self, callback):
        self._message_callback = callback
        if self.project_setup_viewmodel is not None:
            self.project_setup_viewmodel.set_callback("dialog", callback)

    def set_switch_tab_callback(self, callback):
        self._switch_tab_callback = callback

    def on_save(self):
        self._project.save()

    def on_save_as(self, file):
        self._project.save_as(new_file=file)

    def on_new(self):
        Launcher.launch_new()

    def on_open(self, file):
        Launcher.open(file)

    def on_close(self):
        AsyncManager.shutdown()
        if self._project is None:
            return True
        if self._project_unsaved or self._project.check_newer_autosave():
            response = inquire_close_unsaved(project_name=self.get("name"), root_path=self.get_setting("projectsPath", "/"))  # User either saves, discards (return true) or cancels
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
        if current in recents:
            recents.remove(current)
        return recents

    def toggle_sanity_checks(self):
        return self._settings.toggle_sanity_checks()



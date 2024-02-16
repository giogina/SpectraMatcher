from models.data_file_manager import DataFileManager, FileObserver
from models.settings_manager import SettingsManager, Settings
from utility.system_file_browser import data_dir_file_dialog, data_files_dialog


def noop(*args, **kwargs):
    pass


class DataFileViewModel(FileObserver):
    _callbacks = {
        "populate file explorer": noop,
        "update file": noop
    }

    def __init__(self, data_file_manager: DataFileManager):
        self._data_file_manager = data_file_manager
        self._data_file_manager.add_observer(self, "file changed")  # Only properties of one existing file need updating
        self._data_file_manager.add_observer(self, "directory structure changed")  # Need to re-populate the entire list
        self.settings = SettingsManager()
        self.table_columns = self.settings.get(Settings.FILE_EXPLORER_COLUMNS)

    def update_column_settings(self):
        self.settings.update_settings({Settings.FILE_EXPLORER_COLUMNS: self.table_columns})

    def set_callback(self, key, callback):
        if key in self._callbacks.keys():
            self._callbacks[key] = callback
        else:
            print(f"Warning: In DataFileViewModel: Attempted to set unknown callback key {key}")

    def update(self, event_type, *args):
        print(f"DataFileViewModel observed event: {event_type}")
        if event_type == "directory structure changed":
            self._populate_file_explorer(args)
        if event_type == "file changed":
            self._callbacks.get("update file")(args[0][0])

    def toggle_directory(self, directory_tag, is_open):
        print(f"Toggling: {directory_tag, is_open}, {self._data_file_manager.directory_toggle_states}")
        self._data_file_manager.directory_toggle_states[directory_tag] = is_open

    def get_dir_state(self, directory_tag):
        return self._data_file_manager.directory_toggle_states.get(directory_tag, True)
    #
    # def toggle_column_visibility(self, column_index: int, show: bool):
    #     pass
    #
    # def toggle_column_visibility(self, column_index: int, show: bool):
    #     pass

    def inquire_open_data_directory(self):
        path = data_dir_file_dialog(self._data_file_manager.last_path)
        if path:
            print(f"Adding folder: {path}")
            self._data_file_manager.open_directories([path])

    def inquire_open_data_files(self):
        files = data_files_dialog(self._data_file_manager.last_path)
        if files and len(files):
            print(f"Adding files: {files}")
            self._data_file_manager.open_directories(open_data_dirs=[], open_data_files=list(files))

    def _populate_file_explorer(self, *args):
        self._callbacks.get("populate file explorer", noop)(self._data_file_manager.top_level_directories,
                                                            self._data_file_manager.top_level_files)

    # TODO: Turn Files and Directories into dicts (independent deep-copies)
    #   pre-decide icons, colors etc
    #



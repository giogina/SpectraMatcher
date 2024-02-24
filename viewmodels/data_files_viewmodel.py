from models.data_file_manager import DataFileManager, FileObserver, File, Directory, GaussianLog, FileType
from models.settings_manager import SettingsManager, Settings
from utility.system_file_browser import data_dir_file_dialog, data_files_dialog


def noop(*args, **kwargs):
    pass


class FileViewModel:
    def __init__(self, file: File):
        for key, value in file.__dict__.items():
            setattr(self, key, value)


class DirectoryViewModel:
    def __init__(self, directory: Directory):
        for key, value in directory.__dict__.items():
            if key == "content_dirs":
                content_dir_vms = {}
                for tag, d in directory.content_dirs.items():
                    content_dir_vms[tag] = DirectoryViewModel(d)
                self.content_dirs = content_dir_vms
            elif key == "content_files":
                content_file_vms = {}
                for tag, file in directory.content_files.items():
                    content_file_vms[tag] = FileViewModel(file)
                self.content_files = content_file_vms
            else:
                setattr(self, key, value)


class DataFileViewModel(FileObserver):
    def __init__(self, data_file_manager: DataFileManager):
        self._callbacks = {
            "populate file explorer": noop,
            "reset file explorer": noop,
            "update file": noop,
            "update directory ignore status": noop,
        }
        self._data_file_manager = data_file_manager
        self._data_file_manager.add_observer(self, "file changed")  # Only properties of one existing file need updating
        self._data_file_manager.add_observer(self, "directory changed")  # Only properties of one existing dir need updating
        self._data_file_manager.add_observer(self, "directory structure changed")  # Need to re-populate the entire list
        self.settings = SettingsManager()
        self.table_columns = self.settings.get(Settings.FILE_EXPLORER_COLUMNS)
        self._all_files = {}

    def update_column_settings(self):
        self.settings.update_settings({Settings.FILE_EXPLORER_COLUMNS: self.table_columns})

    def set_callback(self, key, callback):
        if key in self._callbacks.keys():
            self._callbacks[key] = callback
        else:
            print(f"Warning: In DataFileViewModel: Attempted to set unknown callback key {key}")

    def update(self, event_type, *args):
        # print(f"DataFileViewModel observed event: {event_type, *args}")
        if event_type == "directory structure changed":
            self._populate_file_explorer(*args)
        if event_type == "file changed":
            if type(args[0]) == File:
                file_vm = FileViewModel(args[0])
            elif type(args[0][0]) == File:
                file_vm = FileViewModel(args[0][0])
            self._callbacks.get("update file")(file_vm)

    def remove_directory(self, directory_tag):
        self._data_file_manager.close_directory(directory_tag)

    def remove_file(self, file_tag):
        self._data_file_manager.close_file(file_tag)

    def toggle_directory(self, directory_tag, is_open):
        self._data_file_manager.toggle_directory(directory_tag, is_open)

    def get_dir_state(self, directory_tag):
        return self._data_file_manager.is_directory_toggled_open(directory_tag)

    def ignore_tag(self, tag, ignore=True):
        self._data_file_manager.ignore(tag, ignore=ignore)
        file = self._data_file_manager.get_file(tag)
        if file:
            self._callbacks.get("update file")(file)

    def ignore_directory(self, d, ignore=True):  # Careful: This is an old version of directory from when the callback was created. Only use immuted properties like content_dirs.
        self._data_file_manager.ignore(d.tag, ignore=ignore)
        if isinstance(d, DirectoryViewModel):
            self._callbacks.get("update directory ignore status")(d.tag)
            for dd in d.content_dirs.values():
                self.ignore_directory(dd, ignore=ignore)
            for f in d.content_files.values():
                self.ignore_tag(f.tag, ignore=ignore)

    def is_ignored(self, tag):
        return self._data_file_manager.is_ignored(tag)

    def mark_file_as_excitation(self, tag, excitation):
        self._data_file_manager.mark_file_as_excitation(tag, excitation)

    def inquire_open_data_directory(self):
        path = data_dir_file_dialog(self._data_file_manager.last_path)
        if path:
            self._data_file_manager.open_directories([path])

    def add_directory_or_file(self, paths):
        self._data_file_manager.open_directories_or_files(paths)

    def make_file_readable(self, tag):
        self._data_file_manager.make_readable(tag)

    def inquire_open_data_files(self):
        files = data_files_dialog(self._data_file_manager.last_path)
        if files and len(files):
            self._data_file_manager.open_directories(open_data_dirs=[], open_data_files=list(files))

    def _populate_file_explorer(self, reset=False):
        dir_vms = {t: DirectoryViewModel(d) for t, d in self._data_file_manager.top_level_directories.items()}
        file_vms = {t: FileViewModel(file) for t, file in self._data_file_manager.top_level_files.items()}

        if reset:
            self._callbacks.get("reset file explorer", noop)(dir_vms, file_vms)
        else:
            print(f"Calling update file explorer, {dir_vms, file_vms}")
            self._callbacks.get("populate file explorer", noop)(dir_vms, file_vms)



from models.data_file_manager import DataFileManager, FileObserver


def noop(*args, **kwargs):
    pass


class DataFileViewModel(FileObserver):
    _callbacks = {
        "populate file explorer": noop
    }

    def __init__(self, data_file_manager: DataFileManager):
        self._data_file_manager = data_file_manager
        self._data_file_manager.add_observer(self, "files changed")  # Only properties of existing entries need updating
        self._data_file_manager.add_observer(self, "directory structure changed")  # Need to re-populate the entire list

    def set_callback(self, key, callback):
        if key in self._callbacks.keys():
            self._callbacks[key] = callback
        else:
            print(f"Warning: In DataFileViewModel: Attempted to set unknown callback key {key}")

    def update(self, event_type, *args):
        print(f"DataFileViewModel observed event: {event_type}")
        if event_type == "directory structure changed":
            self._populate_file_explorer(args)

    def _populate_file_explorer(self, *args):
        self._callbacks.get("populate file explorer", noop)(self._data_file_manager.top_level_directories,
                                                            self._data_file_manager.top_level_files)





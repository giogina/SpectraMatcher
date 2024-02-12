from models.data_file_manager import DataFileManager, FileObserver


def noop(*args, **kwargs):
    pass


class DataFileViewModel(FileObserver):
    _callbacks = {
        "populate file explorer": noop
    }

    def __init__(self, data_file_manager: DataFileManager):
        self._data_file_manager = data_file_manager
        self._data_file_manager.add_observer(self, "files changed")

    def set_callback(self, key, callback):
        if key in self._callbacks.keys():
            self._callbacks[key] = callback
        else:
            print(f"Warning: In DataFileViewModel: Attempted to set unknown callback key {key}")

    def update(self, event_type, *args):
        print(f"DataFileViewModel observed event: {event_type}")




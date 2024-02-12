import os
from os.path import isfile, join


class DataFileManager:
    top_level_directories = []
    top_level_files = []
    _observers = {}

    def __init__(self):
        pass

    def open_directories(self, open_data_dirs, open_data_files=None):
        for path in open_data_dirs:
            self.top_level_directories.append(Directory(path))
            if open_data_files:
                self.top_level_files.append(File(path))
        # TODO> Temp test
        self._notify_observers("files changed")

    ############### Observers ###############

    def add_observer(self, observer, event_type):
        if event_type not in self._observers:
            self._observers[event_type] = []
        self._observers[event_type].append(observer)

    def remove_observer(self, observer, event_type):
        if event_type in self._observers:
            self._observers[event_type].remove(observer)

    def _notify_observers(self, event_type, *args):
        if event_type in self._observers:
            for observer in self._observers[event_type]:
                observer.update(event_type, args)


# Observer interface
class FileObserver:
    def update(self, event_type, *args):
        pass


class Directory:
    contents = []
    name = ""
    path = ""
    parent_directory = None
    tag = ""  # Unique identifier

    def __init__(self, path, name=None, parent=None):
        self.path = path
        self.tag = f"dir_{path}"
        if name:
            self.name = name
        else:
            self.name = os.path.dirname(path)
        self.parent_directory = parent
        print(f"Found directory: {name}")
        self.crawl_contents(path)

    def crawl_contents(self, path):
        dirs = []
        files = []
        for item in os.listdir(path):
            if isfile(join(path, item)):
                files.append(File(join(path, item), name=item, parent=self.tag))
            else:
                dirs.append(Directory(join(path, item), name=item, parent=self.tag))
        self.contents = dirs + files


class File:
    name = ""
    path = ""
    parent_directory = None
    tag = ""  # Unique identifier

    def __init__(self, path, name=None, parent=None):
        self.path = path
        self.tag = f"file_{path}"
        if name:
            self.name = name
        else:
            self.name = os.path.basename(path)
        self.parent_directory = parent
        print(f"Found file: {name}")
        self.what_am_i()

    def what_am_i(self):
        pass  # TODO: whats this file equivalent of evaluating itself.

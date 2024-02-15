import os
from os.path import isfile, join
import asyncio
from asyncio import Queue
import re


class DataFileManager:
    top_level_directories = {}
    top_level_files = {}
    _observers = {}
    file_queue = None
    num_workers = 5
    last_path = "/"  # Last added data path; for file dialog root dirs
    directory_toggle_states = {}  # "directory label": bool - is dir toggled open?

    def __init__(self):
        pass
        # self._update_open_data_files_callback = update_open_data_files_callback

    def open_directories(self, open_data_dirs, open_data_files=None):
        asyncio.run(self._open_directories_async(open_data_dirs, open_data_files))

    # def remove_data_files(self, files: tuple):  # TODO
    #     for file_path in files:
    #         if file in self.top_level_files:
    #             self.top_level_files.remove(file)
    #     self._update_open_data_files_callback(files=self.top_level_files)

    # def remove_data_files(self, files: tuple): # TODO
    #     for file in files:
    #         if file in self.top_level_files:
    #             self.top_level_files.remove(file)
    #     self._update_open_data_files_callback(files=self.top_level_files)

    ############### Observers ###############

    def add_observer(self, observer, event_type):
        if event_type not in self._observers:
            self._observers[event_type] = []
        self._observers[event_type].append(observer)

    def remove_observer(self, observer, event_type):
        if event_type in self._observers:
            self._observers[event_type].remove(observer)

    def notify_observers(self, event_type, *args):
        if event_type in self._observers:
            for observer in self._observers[event_type]:
                observer.update(event_type, args)

    ############### Async setup ###############

    async def worker(self):
        while True:
            file = await self.file_queue.get()
            await file.what_am_i()
            self.file_queue.task_done()

    async def _open_directories_async(self, open_data_dirs=None, open_data_files=None):
        self.file_queue = Queue()

        path = None
        if open_data_dirs:
            for path in open_data_dirs:
                directory = Directory(path, self)
                self.top_level_directories[directory.tag] = directory  # queue gets filled in here
        if open_data_files:
            for path in open_data_files:
                file = File(path, self)
                self.top_level_files[file.tag] = file
        self.last_path = os.path.dirname(path) if path else "/"

        # notify file explorer viewmodel to re-populate the entire list, and parent project to update top level paths.
        self.notify_observers("directory structure changed")

        workers = [asyncio.create_task(self.worker()) for _ in range(self.num_workers)]

        await self.file_queue.join()  # wait for all items to be processed
        for worker in workers:        # Cleanup
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)


# Observer interface
class FileObserver:
    def update(self, event_type, *args):
        pass


class Directory:
    content_dirs = {}
    content_files = {}
    name = ""
    path = ""
    depth = 0
    parent_directory = None
    tag = ""  # Unique identifier

    def __init__(self, path, manager: DataFileManager, name=None, parent=None, depth=0):
        self.path = path.replace('\\', '/')
        self.manager = manager
        self.tag = f"dir_{path}"
        self.depth = depth
        if name:
            self.name = name
        else:
            self.name = os.path.basename(path)
        self.parent_directory = parent
        self.crawl_contents(path)

    def crawl_contents(self, path):
        dirs = {}
        files = {}
        for item in os.listdir(path):
            if isfile(join(path, item)):
                file = File(join(path, item), self.manager, name=item, parent=self.tag, depth=self.depth+1)
                files[file.tag] = file
            else:
                directory = Directory(join(path, item), self.manager, name=item, parent=self.tag, depth=self.depth+1)
                dirs[directory.tag] = directory
        self.content_dirs = dirs
        self.content_files = files


class FileType:
    OTHER = "Other"
    GAUSSIAN_LOG = "Gaussian log"
    GAUSSIAN_INPUT = "Gaussian input"
    GAUSSIAN_CHECKPOINT = "Gaussian chk"


class GaussianLog:
    CONTENTS = "contents"
    STATUS = "status"
    HAS_HPMODES = "hpmodes"
    ANHARM = "anharm"
    FINISHED = "finished"
    ERROR = "error"
    RUNNING = "running"
    NEGATIVE_FREQUENCY = "negative frequency"
    FREQ_GROUND = "Frequency ground state"
    FREQ_EXCITED = "Frequency excited state"
    FC_EXCITATION = "FC excitation"
    FC_EMISSION = "FC emission"


class File:
    name = ""
    path = ""
    parent_directory = None
    tag = ""  # Unique identifier
    depth = 0
    properties = {}
    extension = ""

    type = None

    def __init__(self, path, manager: DataFileManager, name=None, parent=None, depth=0):
        self.path = path.replace('\\', '/')
        self.manager = manager
        self.depth = depth
        self.tag = f"file_{path}"
        if name:
            self.name = name
        else:
            self.name = os.path.basename(path)
        self.parent_directory = parent
        name, self.extension = os.path.splitext(self.name)

        self.manager.file_queue.put_nowait(self)

    async def what_am_i(self):
        properties = {}
        if self.extension == ".log":  # Gaussian log
            self.type = FileType.GAUSSIAN_LOG
            properties[GaussianLog.CONTENTS] = None
            properties[GaussianLog.ANHARM] = False
            properties[GaussianLog.HAS_HPMODES] = False

            nr_jobs = 1  # keep track of Gaussian starting new internal jobs
            nr_finished = 0
            error = False
            has_freqs = False
            has_fc = False
            emission = False
            excited = False
            try:
                with open(self.path, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if re.search('Frequencies --', line):
                            has_freqs = True
                            if re.search('Frequencies ---', line):
                                properties[GaussianLog.HAS_HPMODES] = True  # TODO: Check for negative frequencies (set state to GaussianLog.NEGATIVE_FREQUENCY, update file)
                        if re.search('anharmonic', line):
                            properties[GaussianLog.ANHARM] = True
                        if re.search('Excited', line):
                            excited = True
                        if re.search('Final Spectrum', line):
                            has_fc = True
                        if re.search('emission', line):
                            emission = True
                        if re.search('Proceeding to internal job step number', line):
                            nr_jobs += 1
                        if re.search('Normal termination', line):
                            nr_finished += 1
                        if re.search('Error termination', line):
                            error = True
                if has_fc:
                    if emission:
                        properties[GaussianLog.CONTENTS] = GaussianLog.FC_EMISSION  # TODO: FC files always treat current state as ground state; and contain corresponding geom & freqs. Read from there (maybe just as backup).
                    else:
                        properties[GaussianLog.CONTENTS] = GaussianLog.FC_EXCITATION
                elif has_freqs:
                    if excited:
                        properties[GaussianLog.CONTENTS] = GaussianLog.FREQ_EXCITED
                    else:
                        properties[GaussianLog.CONTENTS] = GaussianLog.FREQ_GROUND
                if nr_jobs == nr_finished:
                    properties[GaussianLog.STATUS] = GaussianLog.FINISHED
                elif error:
                    properties[GaussianLog.STATUS] = GaussianLog.ERROR
                else:
                    properties[GaussianLog.STATUS] = GaussianLog.RUNNING

            except Exception as e:
                print(f"File {self.path} couldn't be read! {e}")
        elif self.extension in [".gjf", ".com"]:
            self.type = FileType.GAUSSIAN_INPUT
        elif self.extension == ".chk":
            self.type = FileType.GAUSSIAN_CHECKPOINT
        else:
            self.type = FileType.OTHER
        self.properties = properties
        self.manager.notify_observers("file changed", self)



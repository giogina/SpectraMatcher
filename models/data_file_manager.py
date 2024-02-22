import os
from os.path import isfile, join
import asyncio
import aiofiles
import threading
from asyncio import Queue
import re
from enum import Enum
from utility.experimental_spectrum_parser import ExperimentParser
from utility.read_write_lock import PathLockManager


class FileType:
    OTHER = "Other"
    EXPERIMENT_EMISSION = "experiment emission"
    EXPERIMENT_EXCITATION = "experiment excitation"
    GAUSSIAN_LOG = "Gaussian log"
    GAUSSIAN_INPUT = "Gaussian input"
    GAUSSIAN_CHECKPOINT = "Gaussian chk"
    FREQ_GROUND = "Frequency ground state"
    FREQ_EXCITED = "Frequency excited state"
    FREQ_GROUND_ANHARM = "Frequency ground state anharm"
    FREQ_EXCITED_ANHARM = "Frequency excited state anharm"
    FC_EXCITATION = "FC excitation"
    FC_EMISSION = "FC emission"
    LOG_TYPES = (GAUSSIAN_LOG, FC_EMISSION, FC_EXCITATION,
                 FREQ_GROUND, FREQ_EXCITED, FREQ_GROUND_ANHARM, FREQ_EXCITED_ANHARM)


class GaussianLog(Enum):
    STATUS = "status"
    HAS_HPMODES = "hpmodes"
    FINISHED = "finished"
    ERROR = "error"
    RUNNING = "running"
    NEGATIVE_FREQUENCY = "negative frequency"


class DataFileManager:
    def __init__(self):
        self.top_level_directories = {}
        self.top_level_files = {}
        self._observers = {}
        self.file_queue = None
        self.num_workers = 5
        self.last_path = "/"  # Last added data path; for file dialog root dirs
        # Set from parent Project instance, directly coupled to its _data:
        self.directory_toggle_states = {}  # "directory tag": bool - is dir toggled open?
        self.ignored_files_and_directories = []
        self.all_files = {}  # lookup files in a flat structure

        self.lock_manager = PathLockManager()

    def open_directories(self, open_data_dirs, open_data_files=None):
        print(f"Opening: {open_data_dirs, open_data_files}")
        asyncio.run(self._open_directories_async(open_data_dirs, open_data_files))

    def open_directories_or_files(self, paths: list):
        new_paths = []
        new_files = []
        for path in paths:
            if type(path) == str:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        new_paths.append(path)
                    elif os.path.isfile(path):
                        new_files.append(path)
        self.open_directories(new_paths, new_files)

    def close_directory(self, directory_tag):
        if directory_tag in self.top_level_directories.keys():
            self._forget_directory_info(self.top_level_directories[directory_tag])
            del self.top_level_directories[directory_tag]
            self.notify_observers("directory structure changed", True)

    def close_file(self, file_tag):
        if file_tag in self.top_level_files.keys():
            del self.top_level_files[file_tag]
            self.notify_observers("directory structure changed")

    def toggle_directory(self, directory_tag, is_open):
        self.directory_toggle_states[directory_tag] = is_open

    def is_directory_toggled_open(self, directory_tag):
        return self.directory_toggle_states.get(directory_tag, True)

    def ignore(self, tag, ignore=True):
        print(f"Ignore: {tag, ignore, tag in self.ignored_files_and_directories}")
        if ignore and (tag not in self.ignored_files_and_directories):
            self.ignored_files_and_directories.append(tag)
        if not ignore and (tag in self.ignored_files_and_directories):
            self.ignored_files_and_directories.remove(tag)
        self.notify_observers("directory structure changed")

    def is_ignored(self, tag):
        return tag in self.ignored_files_and_directories

    def mark_file_as_excitation(self, tag, excitation=True):
        file = self.get_file(tag)
        print(f"File {file} for tag {tag}")
        if file:
            if excitation and file.type == FileType.EXPERIMENT_EMISSION:
                file.type = FileType.EXPERIMENT_EXCITATION
            if not excitation and file.type == FileType.EXPERIMENT_EXCITATION:
                file.type = FileType.EXPERIMENT_EMISSION
            self.notify_observers("file changed", file)

    def _forget_directory_info(self, directory):
        if directory.tag in self.directory_toggle_states.keys():
            del self.directory_toggle_states[directory.tag]
        if directory.tag in self.ignored_files_and_directories:
            self.ignored_files_and_directories.remove(directory.tag)
        for f in directory.content_files.values():
            if f.tag in self.ignored_files_and_directories:
                self.ignored_files_and_directories.remove(f.tag)
        for i, d in directory.content_dirs.items():
            self._forget_directory_info(d)

    def get_file(self, tag):
        return self.all_files.get(tag)

    # magic!
    def make_readable(self, tag):
        file = self.all_files.get(tag)
        file.is_human_readable = True
        self.notify_observers("file changed", file)
        if file:
            loop = asyncio.new_event_loop()
            t = threading.Thread(target=self._start_file_rewrite_loop, args=(loop, file.path), daemon=True)
            t.start()

    def _start_file_rewrite_loop(self, loop, path):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._make_readable(path))
        loop.close()

    async def _make_readable(self, path):
        if os.path.exists(path):
            tmp_file_path = f"{path}.tmp"
            self.lock_manager.acquire_write(path)
            try:
                async with aiofiles.open(path, 'r') as reader:
                    async with aiofiles.open(tmp_file_path, 'w') as writer:
                        async for line in reader:
                            newline = line.rstrip('\n').rstrip('\r')
                            if len(newline):
                                await writer.write(newline + '\r\n')
                os.replace(tmp_file_path, path)
            finally:
                self.lock_manager.release_write(path)


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
            try:
                await file.what_am_i_async_wrapper()  # Ensure this is an async operation
            except Exception as e:
                print(f"Worker caught an exception: {e}")
                break
            finally:
                self.file_queue.task_done()

    async def _open_directories_async(self, open_data_dirs=None, open_data_files=None):
        self.file_queue = Queue()

        path = None
        if open_data_dirs:
            for path in open_data_dirs:
                directory = Directory(path, self)
                self.top_level_directories[directory.tag] = directory  # queue gets filled in here
                print(f"Added directory: {directory.tag}")
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
    def __init__(self, path, manager: DataFileManager, name=None, parent=None, depth=0):
        self.content_dirs = {}
        self.content_files = {}
        self.path = path.replace("/", "\\")
        self.manager = manager
        self.tag = f"dir_{path}_{depth}"
        self.depth = depth
        if name:
            self.name = name
        else:
            self.name = os.path.basename(path)
        self.parent_directory = parent

        if self.path.find("\\ignore") > -1 or self.path.find("\\old") > -1:
            print(f"Ignoring directory by path>: {self.path}")
            self.manager.ignore(self.tag)
            self.manager.toggle_directory(directory_tag=self.tag, is_open=False)

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


class File:
    def __init__(self, path, manager: DataFileManager, name=None, parent=None, depth=0):
        self.properties = {}
        self.is_human_readable = True  # \n instead of \r\n making it ugly in notepad
        self.type = None
        self.path = path.replace("/", "\\")
        self.manager = manager
        self.depth = depth
        self.tag = f"file_{path}_{depth}"
        if name:
            self.name = name
        else:
            self.name = os.path.basename(path)
        self.parent_directory = parent
        name, self.extension = os.path.splitext(self.name)
        self.manager.all_files[self.tag] = self

        if self.path.find("\\ignore") > -1 or self.path.find("\\old") > -1:
            self.manager.ignore(self.tag)

        self.manager.file_queue.put_nowait(self)

    async def what_am_i_async_wrapper(self):
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self.what_am_i)
        except Exception as e:
            print(f"An exception occurred: {e}")

    def what_am_i(self):
        properties = {}
        is_table = False
        if self.extension == ".log":  # Gaussian log
            self.type = FileType.GAUSSIAN_LOG
            anharm = False
            properties[GaussianLog.HAS_HPMODES] = False

            nr_jobs = 1  # keep track of Gaussian starting new internal jobs
            nr_finished = 0
            error = False
            has_freqs = False
            has_fc = False
            emission = False
            excited = False
            self.manager.lock_manager.acquire_read(self.path)
            try:
                with open(self.path, 'rb') as file:
                    content = file.read(1024)
                    self.is_human_readable = b'\r\n' in content
                with open(self.path, 'r') as f:
                    lines = f.readlines()
                for line in lines:
                    if re.search('Frequencies --', line):
                        has_freqs = True
                        if re.search('Frequencies ---', line):
                            properties[GaussianLog.HAS_HPMODES] = True  # TODO: Check for negative frequencies (set state to GaussianLog.NEGATIVE_FREQUENCY, update file; set state to ERROR or negfreq!)
                    if re.search('anharmonic', line):
                        anharm = True
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
                        self.type = FileType.FC_EMISSION  # TODO: FC files always treat current state as ground state; and contain corresponding geom & freqs. Read from there (maybe just as backup).
                    else:
                        self.type = FileType.FC_EXCITATION
                elif has_freqs:
                    if excited:
                        if anharm:
                            self.type = FileType.FREQ_EXCITED_ANHARM
                        else:
                            self.type = FileType.FREQ_EXCITED
                    else:
                        if anharm:
                            self.type = FileType.FREQ_GROUND_ANHARM
                        else:
                            self.type = FileType.FREQ_GROUND
                if nr_jobs == nr_finished:
                    properties[GaussianLog.STATUS] = GaussianLog.FINISHED
                elif error:
                    properties[GaussianLog.STATUS] = GaussianLog.ERROR
                else:
                    properties[GaussianLog.STATUS] = GaussianLog.RUNNING

            except Exception as e:
                print(f"File {self.path} couldn't be read! {e}")
            finally:
                self.manager.lock_manager.release_read(self.path)
        elif self.extension in [".gjf", ".com"]:
            self.type = FileType.GAUSSIAN_INPUT
        elif self.extension == ".chk":
            self.type = FileType.GAUSSIAN_CHECKPOINT
        elif self.extension == ".txt":
            try:
                delim, is_table = ExperimentParser.guess_delimiter_and_check_table(self.path)
                self.properties["delimiter"] = delim
            except Exception as e:
                print(f"File {self.path} couldn't be read! {e}")
        elif self.extension in ['.csv', '.tsv', '.xlsx', '.xls', '.xlsm', '.xltx', '.xltm', '.ods']:  # TODO> Document available formats.
            is_table = True
        else:
            self.type = FileType.OTHER

        if is_table:
            if re.search(r'DF_|fluor|emmi', self.name, re.IGNORECASE):
                self.type = FileType.EXPERIMENT_EMISSION
            else:
                self.type = FileType.EXPERIMENT_EXCITATION
        self.properties = properties
        self.manager.notify_observers("file changed", self)



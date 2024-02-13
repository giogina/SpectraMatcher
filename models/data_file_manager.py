import os
from os.path import isfile, join
import asyncio
from asyncio import Queue


class DataFileManager:
    top_level_directories = []
    top_level_files = []
    _observers = {}
    file_queue = None
    num_workers = 5

    def __init__(self):
        pass

    def open_directories(self, open_data_dirs, open_data_files=None):
        asyncio.run(self._open_directories_async(open_data_dirs, open_data_files))

    async def _open_directories_async(self, open_data_dirs, open_data_files=None):
        self.file_queue = Queue()

        for path in open_data_dirs:
            self.top_level_directories.append(Directory(path, self))  # queue gets filled in here
            if open_data_files:
                self.top_level_files.append(File(path, self))
        self.notify_observers("directory structure changed")  # re-populate the entire list
        workers = [asyncio.create_task(self.worker()) for _ in range(self.num_workers)]

        await self.file_queue.join()  # wait for all items to be processed
        for worker in workers:        # Cleanup
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

    ############### Observers ###############

    def add_observer(self, observer, event_type):
        if event_type not in self._observers:
            self._observers[event_type] = []
        self._observers[event_type].append(observer)

    def remove_observer(self, observer, event_type):
        if event_type in self._observers:
            self._observers[event_type].remove(observer)

    def notify_observers(self, event_type, *args):
        print(f"Notify called! {event_type, args}")
        if event_type in self._observers:
            for observer in self._observers[event_type]:
                observer.update(event_type, args)

    ############### Async setup ###############

    async def worker(self):
        while True:
            file = await self.file_queue.get()
            await file.what_am_i()
            self.file_queue.task_done()


# Observer interface
class FileObserver:
    def update(self, event_type, *args):
        pass


class Directory:
    content_dirs = []
    content_files = []
    name = ""
    path = ""
    depth = 0
    parent_directory = None
    tag = ""  # Unique identifier

    def __init__(self, path, manager: DataFileManager, name=None, parent=None, depth=0):
        self.path = path
        self.manager = manager
        self.tag = f"dir_{path}"
        self.depth = depth
        if name:
            self.name = name
        else:
            self.name = os.path.dirname(path)
        self.parent_directory = parent
        self.crawl_contents(path)

    def crawl_contents(self, path):
        dirs = []
        files = []
        for item in os.listdir(path):
            if isfile(join(path, item)):
                files.append(File(join(path, item), self.manager, name=item, parent=self.tag, depth=self.depth+1))
            else:
                dirs.append(Directory(join(path, item), self.manager, name=item, parent=self.tag, depth=self.depth+1))
        self.content_dirs = dirs
        self.content_files = files


class File:
    name = ""
    path = ""
    parent_directory = None
    tag = ""  # Unique identifier
    depth = 0

    type = None

    def __init__(self, path, manager: DataFileManager, name=None, parent=None, depth=0):
        self.path = path
        self.manager = manager
        self.depth = depth
        self.tag = f"file_{path}"
        if name:
            self.name = name
        else:
            self.name = os.path.basename(path)
        self.parent_directory = parent
        filename, extension = os.path.splitext(self.name)
        if extension == ".log":
            self.type = "Gaussian log"
        # asyncio.get_running_loop().call_soon_threadsafe(asyncio.create_task, self.manager.file_queue.put(self))
        # asyncio.run(self._queue_up())
        self.manager.file_queue.put_nowait(self)

    # async def _queue_up(self):
    #     await self.manager.file_queue.put(self)  # wait in line to run what_am_i

    async def what_am_i(self):
        self.manager.notify_observers("file changed", self)



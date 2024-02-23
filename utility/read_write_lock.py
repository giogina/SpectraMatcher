import threading


class PathLockManager:
    def __init__(self):
        self.locks = {}
        self.locks_lock = threading.Lock()

    def _get_lock(self, path):
        with self.locks_lock:
            if path not in self.locks:
                self.locks[path] = ReadersWriterLock()
            return self.locks[path]

    def acquire_read(self, path):
        lock = self._get_lock(path)
        lock.acquire_read()

    def release_read(self, path):
        lock = self._get_lock(path)
        lock.release_read()

    def acquire_write(self, path):
        lock = self._get_lock(path)
        lock.acquire_write()

    def release_write(self, path):
        lock = self._get_lock(path)
        lock.release_write()


class ReadersWriterLock:
    def __init__(self):
        self.read_lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.readers = 0

    def acquire_read(self):
        with self.read_lock:
            self.readers += 1
            if self.readers == 1:
                self.write_lock.acquire()

    def release_read(self):
        with self.read_lock:
            self.readers -= 1
            if self.readers == 0:
                self.write_lock.release()

    def acquire_write(self):
        self.write_lock.acquire()

    def release_write(self):
        self.write_lock.release()

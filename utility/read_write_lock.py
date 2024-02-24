import threading


class PathLockManager:
    locks = {}
    locks_lock = threading.Lock()

    @classmethod
    def _get_lock(cls, path):
        with cls.locks_lock:
            if path not in cls.locks:
                cls.locks[path] = ReadersWriterLock()
            return cls.locks[path]

    @classmethod
    def acquire_read(cls, path):
        lock = cls._get_lock(path)
        lock.acquire_read()

    @classmethod
    def release_read(cls, path):
        lock = cls._get_lock(path)
        lock.release_read()

    @classmethod
    def acquire_write(cls, path):
        lock = cls._get_lock(path)
        lock.acquire_write()

    @classmethod
    def release_write(cls, path):
        lock = cls._get_lock(path)
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

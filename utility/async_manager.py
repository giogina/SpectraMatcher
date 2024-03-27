import asyncio
import threading
import os
from concurrent.futures import ThreadPoolExecutor


class AsyncManager:
    _tasks = None
    _loop = None
    _executor = ThreadPoolExecutor(max_workers=os.cpu_count() * 4)
    _waiting_task_map = {}  # Maps task_id to asyncio Task
    _running_task_map = {}  # Do I need this for the shutdown cancel?
    _stop = False
    _thread = None

    @classmethod
    def start(cls):
        print(f"Asyncmanager started!")
        if cls._loop is None:
            print(f"Initiating async manager!")
            cls._thread = threading.Thread(target=cls._start_loop_in_thread, daemon=True)
            cls._thread.start()

    @classmethod
    def _start_loop_in_thread(cls):
        """Starts the asyncio event loop in a background thread."""
        cls._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls._loop)
        cls._tasks = asyncio.Queue()
        cls._loop.run_until_complete(cls._run_tasks())

    @classmethod
    async def _run_tasks(cls):
        while True:
            task_id, func, args, observers, notification = await cls._tasks.get()
            if cls._stop:
                return
            if cls._waiting_task_map.get(task_id) == (func, args):
                del cls._waiting_task_map[task_id]  # Remove it from the map as it's now running
                result = await cls._loop.run_in_executor(cls._executor, func, *args)
                cls.notify_observers(observers, notification, result)

    @classmethod
    def submit_task(cls, task_id, func, *args, observers=None, notification=""):
        """Synchronously submit a task from the main thread."""
        if not cls._loop:
            raise RuntimeError("Event loop is not running")
        cls._waiting_task_map[task_id] = (func, args)
        asyncio.run_coroutine_threadsafe(cls._submit_task(task_id, func, *args, observers=observers, notification=notification), cls._loop)

    @classmethod
    async def _submit_task(cls, task_id, func, *args, observers=None, notification=""):
        """Actual coroutine to handle task submission."""
        await cls._tasks.put((task_id, func, args, observers, notification))

    @classmethod
    def shutdown(cls):
        if cls._loop is not None:
            asyncio.run_coroutine_threadsafe(cls._async_shutdown(), cls._loop)
            # cls._loop.close()

    @classmethod
    async def _async_shutdown(cls):
        cls._executor.shutdown(wait=True)
        cls._stop = True

    @classmethod
    def notify_observers(cls, observers, notification, result):
        """Notify observers with the provided data."""
        if observers is not None:
            for observer in observers:
                observer.update(notification, result)

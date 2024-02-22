import asyncio
import threading
import os
from concurrent.futures import ThreadPoolExecutor


class AsyncManager:
    _tasks = asyncio.Queue()
    _loop = None
    _executor = ThreadPoolExecutor(max_workers=os.cpu_count() * 2)
    _waiting_task_map = {}  # Maps task_id to asyncio Task
    _running_task_map = {}  # Do I need this for the shutdown cancel?
    _stop = False

    def __init__(self):
        if AsyncManager._loop is None:
            print(f"Initiating async manager!")
            self._thread = threading.Thread(target=self._start_loop_in_thread, daemon=True)
            self._thread.start()

    @staticmethod
    def _start_loop_in_thread():
        """Starts the asyncio event loop in a background thread."""
        AsyncManager._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(AsyncManager._loop)
        AsyncManager._loop.run_until_complete(AsyncManager._run_tasks())

    @classmethod
    async def _run_tasks(cls):
        while True:
            task_id, func, args = await cls._tasks.get()
            if cls._stop:
                return
            if cls._waiting_task_map.get(task_id) == (func, args):
                del cls._waiting_task_map[task_id]  # Remove it from the map as it's now running
                asyncio.create_task(cls.run_in_executor(func, *args))

    @classmethod
    def submit_task(cls, task_id, func, *args):
        """Synchronously submit a task from the main thread."""
        if not cls._loop:
            raise RuntimeError("Event loop is not running")
        cls._waiting_task_map[task_id] = (func, args)
        asyncio.run_coroutine_threadsafe(cls._submit_task(task_id, func, *args), cls._loop)

    @classmethod
    async def _submit_task(cls, task_id, func, *args):
        """Actual coroutine to handle task submission."""
        await cls._tasks.put((task_id, func, args))

    @classmethod
    async def run_in_executor(cls, func, *args):
        await cls._loop.run_in_executor(cls._executor, func, *args)

    @classmethod
    def shutdown(cls):
        asyncio.run_coroutine_threadsafe(cls._async_shutdown(), cls._loop)
        cls._thread.join()
        cls._loop.close()

    @classmethod
    async def _async_shutdown(cls):
        cls._executor.shutdown(wait=True)
        cls._stop = True

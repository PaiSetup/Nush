from threading import Thread, Condition, Event, Lock

class DeferredLogger:
    def __init__(self):
        self._lock = Lock()
        self._lines = []

    def log(self, line):
        with self._lock:
            self._lines.append(line)

    def output_logs(self):
        with self._lock:
            for line in self._lines:
                print(line)
            self._lines.clear()


class ThreadManager:
    def __init__(self, thread_count):
        self._thread_count = thread_count
        self._threads = [None] * thread_count

        self._scheduled_tasks = []
        self._dispatcher = Thread(target=self._dispatcher_routine)
        self._dispatcher_shutdown = Event()
        self._dispatcher_notify = Condition()
        self._dispatcher_tasks_started = 0

    def schedule_task(self, target, *args, **kwargs):
        task = Thread(target=self._wrap_target_function(target), args=args, kwargs=kwargs)
        with self._dispatcher_notify:
            self._scheduled_tasks.append(task)
            self._dispatcher_notify.notify()

    def _dispatcher_routine(self):
        def wait_predicate():
            has_task = len(self._scheduled_tasks) > 0
            has_thread = self._get_available_thread_index() is not None
            return (has_task and has_thread) or (not has_task and self._dispatcher_shutdown.is_set())

        while True:
            with self._dispatcher_notify:
                # wait for notification
                self._dispatcher_notify.wait_for(wait_predicate)

                if len(self._scheduled_tasks) > 0:
                    # Find task and thread to perform it
                    scheduled_task = self._scheduled_tasks.pop(0)
                    index = self._get_available_thread_index()

                    # Ensure thread is really done by joining it
                    if self._threads[index] is not None:
                        self._threads[index].join()

                    # prepare task data
                    task_index = self._dispatcher_tasks_started
                    self._dispatcher_tasks_started += 1
                    task_data = {"thread_index": index, "task_index": task_index}

                    # Start thread
                    self._threads[index] = scheduled_task
                    self._threads[index]._kwargs["task_data"] = task_data
                    self._threads[index].start()

                elif self._dispatcher_shutdown.is_set():
                    return

    def __enter__(self):
        self._dispatcher.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Shut down dispatcher thread
        self._dispatcher_shutdown.set()
        with self._dispatcher_notify:
            self._dispatcher_notify.notify()
        self._dispatcher.join()

        # Join all threads
        for thread in self._threads:
            if thread is not None:
                thread.join()

    def _get_available_thread_index(self):
        for index, thread in enumerate(self._threads):
            if thread is None or not thread.is_alive():
                return index
        return None

    def _wrap_target_function(self, target):
        def wrapped_target(*args, **kwargs):
            target(*args, **kwargs)
            with self._dispatcher_notify:
                self._dispatcher_notify.notify()

        return wrapped_target

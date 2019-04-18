from os import mkdir
from threading import Thread, Condition, Event, Lock

from pytube import YouTube

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


class ThreadManager:
    def __init__(self, thread_count):
        self._thread_count = thread_count
        self._threads = [None] * thread_count

        self._scheduled_tasks = []
        self._dispatcher = Thread(target=self._dispatcher_routine)
        self._dispatcher_shutdown = Event()
        self._dispatcher_notify = Condition()

    def schedule_task(self, target, *args, **kwargs):
        task = Thread(target=self._wrap_target_function(target), args=args, kwargs=kwargs)
        with self._dispatcher_notify:
            self._scheduled_tasks.append(task)
            self._dispatcher_notify.notify()

    def _dispatcher_routine(self):
        while True:
            with self._dispatcher_notify:
                # wait for notification
                self._dispatcher_notify.wait()

                # shutdown dispatcher thread
                if self._dispatcher_shutdown.is_set():
                    return

                # Find scheduled task
                if len(self._scheduled_tasks) == 0:
                    continue # Spurious wake-up: no tasks to dispatch
                scheduled_task = self._scheduled_tasks.pop(0)

                # Find first thread that's not working and job for it
                index = self._get_available_thread_index()
                if index is None:
                     continue # Spurious wake-up: no available thread
                if self._threads[index] is not None:
                    self._threads[index].join()

                # Start thread
                self._threads[index] = scheduled_task
                self._threads[index]._kwargs['thread_index'] = index
                self._threads[index].start()


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


def ensure_output_dir_is_present(output_dir):
    try:
        mkdir(output_dir)
    except OSError:
        pass  # directory already exists


def download_video(url, output_dir, logger, thread_index):
    try:
        video = YouTube(url) \
            .streams \
            .filter(progressive=True, file_extension='mp4') \
            .order_by('resolution') \
            .desc() \
            .first()
    except Exception:
        logger.log("\tthread={}: Error downloading \"{}\"".format(thread_index, url))
    else:
        logger.log("\tthread={}: Downloading \"{}\" - \"{}\"".format(thread_index, url, video.default_filename))
        video.download(output_path=output_dir)


def print_help(thread_count, output_dir):
    print("DWYT - download youtube")
    print("thread_count={}, output_dir={}".format(thread_count, output_dir))
    print("Valid inputs:")
    print("\tUrl (starting with https)")
    print("\tFile name - file with urls in each line")
    print()
    print("Input any number of valid input lines and confirm with <Enter>:")


def query_urls():
    while True:
        print('\t', end='')
        line = input()
        if line == "":
            return

        if line.startswith("https://"):
            # Single url
            yield line
        else:
            # File with urls
            with open(line) as file:
                for line in file.read().splitlines():
                    yield line

def filter_comments(lines):
    return (line for line in lines if not line.startswith('#'))

if __name__ == '__main__':
    thread_count = 3
    output_dir = "yt"

    print_help(thread_count, output_dir)
    ensure_output_dir_is_present(output_dir)
    logger = DeferredLogger()
    with ThreadManager(thread_count) as thread_manager:
        for url in filter_comments(query_urls()):
            thread_manager.schedule_task(download_video, url, output_dir, logger)
    print("Done")
    logger.output_logs()

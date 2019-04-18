from os import mkdir
from threading import Thread, Condition

from pytube import YouTube


class ThreadManager:
    def __init__(self, thread_count):
        self.thread_count = thread_count
        self.threads = [None] * thread_count
        self.condition_variable = Condition()

    def start_thread(self, target, *args, **kwargs):
        with self.condition_variable:
            # Wait for and acquire index of available thread in list
            while not self._is_thread_available():
                self.condition_variable.wait()
            index = self._get_available_thread_index()

            # Ensure thread is really done by joining
            if self.threads[index] is not None:
                self.threads[index].join()

            # Schedule new thread
            kwargs['thread_index'] = index
            self.threads[index] = Thread(target=self._wrap_target_function(target), args=args, kwargs=kwargs)
            self.threads[index].start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for thread in self.threads:
            if thread is not None:
                thread.join()

    def _get_available_thread_index(self):
        for index, thread in enumerate(self.threads):
            if thread is None or not thread.is_alive():
                return index
        return None

    def _is_thread_available(self):
        return self._get_available_thread_index() is not None

    def _wrap_target_function(self, target):
        def wrapped_target(*args, **kwargs):
            target(*args, **kwargs)
            with self.condition_variable:
                self.condition_variable.notify()
        return wrapped_target


def ensure_output_dir_is_present(output_dir):
    try:
        mkdir(output_dir)
    except OSError:
        pass  # directory already exists


def download_video(url, output_dir, thread_index):
    try:
        video = YouTube(url) \
            .streams \
            .filter(progressive=True, file_extension='mp4') \
            .order_by('resolution') \
            .desc() \
            .first()
    except Exception:
        print("\tthread={}: Error downloading \"{}\"".format(thread_index, url))
    else:
        print("\tthread={}: Downloading \"{}\" - \"{}\"".format(thread_index, url, video.default_filename))
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


if __name__ == '__main__':
    thread_count = 1
    output_dir = "yt"

    print_help(thread_count, output_dir)
    ensure_output_dir_is_present(output_dir)
    with ThreadManager(thread_count) as thread_manager:
        for url in query_urls():
            thread_manager.start_thread(download_video, url, output_dir)
    print("Done")

import os
import platform
import re
import subprocess
import sys


class CliException(Exception):
    def __init__(self, message):
        self.message = message


def run_cli_operation(operation, *args, **kwargs):
    while True:
        try:
            return operation(*args, **kwargs)
        except CliException as e:
            if e.message is not None:
                info(e.message)


def sort_and_remove_duplicates(list_arg):
    list_arg = sorted(list_arg)

    result = []
    if len(list_arg) > 0:
        result.append(list_arg[0])

    for i in range(1, len(list_arg)):
        if list_arg[i] != list_arg[i - 1]:
            result.append(list_arg[i])

    return result


def join_human_readable_strings(list_arg):
    if len(list_arg) == 0:
        return ""
    elif len(list_arg) == 1:
        return list_arg[0]
    else:
        result = ", ".join(list_arg[:-1])
        result += f" and {list_arg[-1]}"
        return result


def join_selected_tags_names(tags, available_tags):
    if tags is None:
        return "<UNINITIALIZED>"
    if len(tags) == 0:
        return "<EMPTY>"

    indices = [str(available_tags.index(x)) for x in tags if x in available_tags]

    indices_str = " ".join(indices)
    tags_str = ", ".join(tags)
    return f"{tags_str} ( {indices_str} )"


def read_indices(previous_tags, available_tags, max_index):
    def parse_tag_index(input_tag):
        # Try to read as an integer
        try:
            index = int(input_tag)
            if index > max_index:
                raise CliException(f'Tag index "{index}" is too large')
            return index
        except ValueError:
            pass

        # Try to match as string prefix.
        matching_indices = []
        matching_tags = []
        input_tag = input_tag.lower()
        for index, tag in enumerate(available_tags):
            if tag.lower().startswith(input_tag):
                matching_indices.append(index)
                matching_tags.append(tag)
        if len(matching_indices) == 0:
            raise CliException(f'Invalid tag specified: "{input_tag}"')
        elif len(matching_indices) != 1:
            raise CliException(f'Cannot match "{input_tag}" to a specific tag. It matches {join_human_readable_strings(matching_tags)}.')
        return matching_indices[0]

    def operation():
        # Get an input line and split it.
        line = input("Tags: ")
        tags_str = re.split("[ .,]+", line)
        tags_str = (x.strip() for x in tags_str)
        tags_str = (x for x in tags_str if len(x) > 0)
        tags_str = list(tags_str)

        # Convert to ints.
        use_previous_character = "-"
        use_previous = use_previous_character in tags_str
        if use_previous:
            if previous_tags is None:
                raise CliException('Cannot use a "-" argument - tags are uninitialized')
            result = [available_tags.index(x) for x in previous_tags if x in available_tags]
        else:
            result = []

        # Process all indices.
        for tag_str in tags_str:
            # Special "-" argument is already handled. Ignore it.
            if tag_str == use_previous_character:
                continue

            # Handle removing a tag.
            if tag_str.startswith(use_previous_character):
                if not use_previous:
                    raise CliException('A removed tag can only be specified with a "-" argument')
                tag_str = tag_str[1:]
                index = parse_tag_index(tag_str)
                try:
                    result.remove(index)
                except ValueError:
                    raise CliException(f'Removed tag is not contained within current tags: "{tag_str}"')

            # Handle adding an index.
            else:
                index = parse_tag_index(tag_str)
                result.append(index)

        # Post-process the indices and return.
        result = sort_and_remove_duplicates(result)
        return result

    return run_cli_operation(operation)


def read_yes_no(prompt, empty_lines_threshold=4):
    empty_lines_count = 0

    def operation():
        line = input(f"{prompt} (y/n): ")
        if line == "y":
            return True
        if line == "n":
            return False

        if len(line) == 0:
            empty_lines_count += 1
            if empty_lines_count == empty_lines_threshold:
                return True
        else:
            empty_lines_count = 0

        raise CliException(None)

    return run_cli_operation(operation)


def read_identifier(name):
    def operation():
        line = input(f"Input {name}: ")
        line = line.strip()
        if len(line) == 0:
            raise CliException(None)
        return line

    return run_cli_operation(operation)


class BackgroundProcess:
    def __init__(self, args):
        self._handle = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

    def open_file_in_default_application(file_path):
        os = platform.system()
        if os == "Linux":
            return BackgroundProcess(["xdg-open", file_path])
        else:
            raise NotImplementedError()  # TODO Windows

    def kill(self):
        # TODO kill children recursively. In case of xdg-open this doesn't do anything.
        self._handle.kill()


def info(*args, **kwargs):
    print("INFO:", *args, **kwargs)


def warning(*args, **kwargs):
    print("WARNING:", *args, **kwargs)


def error(*args, **kwargs):
    print("ERROR:", *args, **kwargs)
    sys.exit(1)

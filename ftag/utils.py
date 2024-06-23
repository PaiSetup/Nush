import re
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


def read_indices(previous_indices, max_index):
    def operation():
        # Get an input line and split it.
        line = input("Indices: ")
        indices_str = re.split("[ .,]+", line)
        indices_str = (x.strip() for x in indices_str)
        indices_str = (x for x in indices_str if len(x) > 0)
        indices_str = list(indices_str)
        if len(indices_str) == 0:
            raise CliException("Specify indices")

        # Convert to ints.
        use_previous_character = "-"
        use_previous = use_previous_character in indices_str
        if use_previous:
            indices = previous_indices
        else:
            indices = []

        # Process all indices.
        for index_str in indices_str:
            # Special character is already handled. Ignore it.
            if index_str == use_previous_character:
                continue

            # Handle removing an index.
            if index_str.startswith(use_previous_character):
                if not use_previous:
                    raise CliException('A removed tag can only be specified with a "-" argument')
                index_str = index_str[1:]
                try:
                    index = int(index_str)
                except ValueError:
                    raise CliException(f'Invalid tag index specified: "{index_str}"')
                try:
                    indices.remove(index)
                except ValueError:
                    raise CliException(f'Removed tag is not contained within current tags: "{index_str}"')

            # Handle adding an index.
            else:
                try:
                    index = int(index_str)
                except ValueError:
                    raise CliException(f'Invalid tag index specified: "{index_str}"')
                if index > max_index:
                    raise CliException(f'Tag index "{index}" is too large')
                indices.append(index)

        # Post-process the indices and return.
        indices = sort_and_remove_duplicates(indices)
        return indices

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


def read_tag():
    def operation():
        line = input("Input new tag value: ")
        line = line.strip()
        if len(line) == 0:
            raise CliException(None)
        return line

    return run_cli_operation(operation)


def info(*args, **kwargs):
    print("INFO:", *args, **kwargs)


def warning(*args, **kwargs):
    print("WARNING:", *args, **kwargs)


def error(*args, **kwargs):
    print("ERROR:", *args, **kwargs)
    sys.exit(1)

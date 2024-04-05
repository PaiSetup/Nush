import sys


def read_indices_or_character(maxIndex, character):
    while True:
        # Work on strings
        line = input("Indices: ")
        if len(line) == 1 and line[0] in character:
            return line
        indices_str = line.split()
        indices_str = (x.strip() for x in indices_str)
        indices_str = (x for x in indices_str if len(x) > 0)
        indices_str = list(indices_str)
        if len(indices_str) == 0:
            info("Specify at least one!")
            continue

        # Convert to ints
        indices = []
        try:
            for index_str in indices_str:
                indices.append(int(index_str))
        except ValueError as e:
            info("Invalid number passed!")
            continue

        # Work on ints
        if any((index > maxIndex for index in indices)):
            info(f"Too large index! Max is {maxIndex}")
            continue
        return indices


def read_yes_no(prompt, empty_lines_threshold=4):
    empty_lines_count = 0
    while True:
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


def read_tag():
    while True:
        line = input("Input new tag value: ")
        line = line.strip()
        if len(line) == 0:
            continue
        return line


def info(*args, **kwargs):
    print("INFO:", *args, **kwargs)


def warning(*args, **kwargs):
    print("WARNING:", *args, **kwargs)


def error(*args, **kwargs):
    print("ERROR:", *args, **kwargs)
    sys.exit(1)

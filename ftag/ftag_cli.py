#!/bin/python

import argparse
import sys
from pathlib import Path

from tag_engine import TagEngine, TagEngineException, TagEngineState
from utils import error, info, read_indices, read_tag, read_yes_no, warning

# Parse arguments
parser = argparse.ArgumentParser(description="Tag files and generate symlink structures.")
parser.add_argument("-c", "--create", action="store_true", help="Create new ftag database.")
parser.add_argument("-a", "--add_category", type=str, help="Add a new category to the ftag database.")
parser.add_argument("-f", "--file", type=Path, help="Path to the file to tag interactively")
parser.add_argument("-g", "--generate", action="store_true", help="Generate symlinks")
args = parser.parse_args()


# Definitions of main command functions
def print_current_tags(engine, file_to_tag):
    print(f"Current tags for file {file_to_tag}")
    for category in engine.get_tag_categories():
        available_values = engine.get_tag_values(category)
        current_values = engine.get_tags_for_file(file_to_tag, category)
        if current_values is not None:
            current_values_indices = [str(available_values.index(x)) for x in current_values]
            print(f"  {category}: {', '.join(current_values)} ( {' '.join(current_values_indices)} )")
        else:
            print(f"  {category}: NONE")
    print()


def load_engine():
    engine = TagEngine()
    if engine.get_state() != TagEngineState.Loaded:
        error("Failed to load ftags metadata")
    return engine


def initialize_database():
    engine = TagEngine()
    if engine.get_state() != TagEngineState.NotLoaded:
        error(f"Ftag database is already created: {self.get_metadata_file()}")
    engine.initialize()

    engine = TagEngine()
    if engine.get_state() != TagEngineState.Loaded:
        error("Failed to create new ftag database")
    else:
        info(f"Successfully created new ftag database in {engine.get_metadata_file()}")


def add_category(engine, category_name):
    try:
        engine.add_category(category_name)
    except TagEngineException as e:
        error(e.message)
    engine.save()


def tag_file(engine, file_to_tag):
    print(f"Tagging file {file_to_tag}")
    print()

    # Select tag values for each available tag category
    tags = {}
    for category in engine.get_tag_categories():
        # Display values for this category
        print(f"CATEGORY {category}:")
        available_values = engine.get_tag_values(category)
        new_index = len(available_values)
        for index, value in enumerate(available_values):
            print(f"  {index: >2}: {value}")
        print(f"  {new_index: >2}: NEW")

        # Display current value if any
        current_values = engine.get_tags_for_file(file_to_tag, category)
        if current_values is None:
            current_values_indices = None
        else:
            current_values_indices = [available_values.index(x) for x in current_values]
            current_values_indices_str = [str(x) for x in current_values_indices]
            print(f"Current value: {', '.join(current_values)} ( {' '.join(current_values_indices_str)} )")

        # Read user selection
        while True:
            indices = read_indices(available_values, current_values_indices, len(available_values))

            if new_index in indices:
                # If user selected special NEW index, then try to add a new value to
                # current category. If could not add (i.e. index already present) then
                # ignore it.
                new_value = read_tag()
                tag_added = engine.add_tag(category, new_value)
                if not tag_added:
                    warning(f'Could not add value "{new_value}" to category {category}')
                    continue
                available_values = engine.get_tag_values(category)

            # Use the indices to search through available values.
            values = [available_values[index] for index in indices]

            tags[category] = values
            print()
            break

    # Display confirmation
    # print(f"File: {file_to_tag}")
    # print("Tags:")
    # for category, values in tags.items():
    #     print(f"    {category}: {', '.join(values)}")
    # if not read_yes_no("Proceed?"):
    #     print("Exiting without tagging.")
    #     return
    # print()

    engine.set_tags(file_to_tag, tags)
    engine.save()
    engine.generate()


def generate():
    engine.generate()


# Execute main command
if args.file is not None:
    if not args.file.is_file():
        error(f"invalid file {args.file}")
    engine = load_engine()
    print_current_tags(engine, args.file)
    tag_file(engine, args.file)
elif args.add_category is not None:
    engine = load_engine()
    add_category(engine, args.add_category)
elif args.generate:
    engine = load_engine()
    engine.generate()
elif args.create:
    initialize_database()
else:
    parser.print_help()
    print()
    error("no action")

#!/bin/python

import argparse
import sys
from pathlib import Path

from tag_engine import TagEngine, TagEngineException, TagEngineState
from utils import (
    error,
    info,
    join_selected_tags_names,
    read_indices,
    read_tag,
    read_yes_no,
    warning,
)

# Parse arguments
parser = argparse.ArgumentParser(description="Tag files and generate symlink structures.")
parser.add_argument("-c", "--create", action="store_true", help="Create new ftag database.")
parser.add_argument("-a", "--add_category", type=str, help="Add a new category to the ftag database.")
parser.add_argument("-f", "--file", type=Path, help="Path to the file to tag interactively")
parser.add_argument("-g", "--generate", action="store_true", help="Generate symlinks")
parser.add_argument("-t", "--tag_all", action="store_true", help="Iterate over all untagged files and tag them.")
args = parser.parse_args()


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


def tag_file(engine, file_to_tag, only_uninitialized_categories):
    print(f"Tagging file {file_to_tag}")
    for category in engine.get_tag_categories():
        available_values = engine.get_tag_values(category)
        current_values = engine.get_tags_for_file(file_to_tag, category)
        print(f"  {category}: {join_selected_tags_names(current_values, available_values)}")
    print()

    # Select tag values for each available tag category
    tags = {}
    for category in engine.get_tag_categories():
        current_values = engine.get_tags_for_file(file_to_tag, category)
        if only_uninitialized_categories and current_values is not None:
            tags[category] = current_values
            continue

        # Display values for this category
        print(f"CATEGORY {category}:")
        available_values = engine.get_tag_values(category)
        new_index = len(available_values)
        for index, value in enumerate(available_values):
            print(f"  {index: >2}: {value}")
        print(f"  {new_index: >2}: NEW")

        # Display current value if any
        print(f"Current tags: {join_selected_tags_names(current_values, available_values)}")

        # Read user selection
        while True:
            indices = read_indices(current_values, available_values, len(available_values))

            if new_index in indices:
                # If user selected special NEW index, then try to add a new value to
                # current category. If could not add (i.e. index already present) then
                # ignore it.
                new_value = read_tag()
                try:
                    tag_added = engine.add_tag(category, new_value)
                except TagEngineException as e:
                    warning(e.message)
                    warning(f'Could not add value "{new_value}" to category {category}.')
                    continue
                available_values = engine.get_tag_values(category)

            # Use the indices to search through available values.
            values = [available_values[index] for index in indices]

            tags[category] = values
            print(f"Selected tags: {join_selected_tags_names(values, available_values)}")
            print()
            break

    engine.set_tags(file_to_tag, tags)
    engine.save()
    engine.generate_file(file_to_tag)


def generate():
    engine = load_engine()
    engine.generate_all_files(True)


def tag_all():
    engine = load_engine()
    for file_to_tag in engine.get_untagged_files():
        tag_file(engine, file_to_tag, True)


# Execute main command
if args.file is not None:
    if not args.file.is_file():
        error(f"invalid file {args.file}")
    engine = load_engine()
    tag_file(engine, args.file, False)
elif args.tag_all:
    tag_all()
elif args.add_category is not None:
    engine = load_engine()
    add_category(engine, args.add_category)
elif args.generate:
    generate()
elif args.create:
    initialize_database()
else:
    parser.print_help()
    print()
    error("no action")

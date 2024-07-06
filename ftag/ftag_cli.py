#!/bin/python

import argparse
import sys
from pathlib import Path

from engine import *
from utils import *


# ------------------------------------- Helper functions
def load_engine():
    engine = TagEngine()
    if engine.get_state() != TagEngineState.Loaded:
        error("Failed to load ftags metadata")
    print(f"Ftag database found at {engine.get_metadata_file()}")
    return engine


# ------------------------------------- Core operations
def initialize_database():
    engine = TagEngine()
    if engine.get_state() != TagEngineState.NotLoaded:
        error(f"Ftag database is already created: {engine.get_metadata_file()}")
    engine.initialize()
    engine.save()

    engine = TagEngine()
    if engine.get_state() != TagEngineState.Loaded:
        error("Failed to create new ftag database")
    else:
        info(f"Successfully created new ftag database in {engine.get_metadata_file()}")


def add_category(engine, category):
    try:
        engine.add_category(category)
    except TagEngineException as e:
        error(e.message)
    engine.save()


def add_mime_filter(engine, new_filter):
    engine.add_mime_filter(new_filter)
    engine.save()


def add_path_filter(engine, new_filter):
    engine.add_path_filter(new_filter)
    engine.save()


def create_query(engine):
    # Read rules
    rules = {}
    for category in engine.get_categories():
        # Display available tags for this category
        available_values = engine.get_tags_for_category(category)
        for index, value in enumerate(available_values):
            print(f"  {index: >2}: {value}")

        # Read user selection and add it to the query rules
        indices = read_indices(None, available_values, len(available_values))
        if indices:
            rules[category] = [available_values[index] for index in indices]

    # Read query name
    query_name = read_identifier("query name")

    engine.add_query(query_name, rules)
    engine.save()


def generate(engine):
    engine.generate_all_symlinks()


def tag_all(engine):
    statistics = engine.get_untagged_files_statistics()
    print(f"Tagging {statistics['num_untagged_files']} out of {statistics['num_taggable_files']} taggable files.")

    for file_to_tag in engine.get_untagged_files():
        default_app = BackgroundProcess.open_file_in_default_application(file_to_tag)
        tag_file(engine, file_to_tag, True)
        while not read_yes_no("Do you want tag a next file? Say 'no' to re-tag this one."):
            tag_file(engine, file_to_tag, False)
        default_app.kill()


def tag_file(engine, file_to_tag, only_uninitialized_categories):
    if len(engine.get_categories()) == 0:
        print("Database doesn't contain any categories.")
        return

    print(f"Tagging file {file_to_tag}")
    for category in engine.get_categories():
        available_values = engine.get_tags_for_category(category)
        current_values = engine.get_tags_for_file(file_to_tag, category)
        print(f"  {category}: {join_selected_tags_names(current_values, available_values)}")
    print()

    # Select tag values for each available tag category
    tags = {}
    for category in engine.get_categories():
        current_values = engine.get_tags_for_file(file_to_tag, category)
        if only_uninitialized_categories and current_values is not None:
            tags[category] = current_values
            continue

        # Display values for this category
        print(f"CATEGORY {category}:")
        available_values = engine.get_tags_for_category(category)
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
                new_value = read_identifier("new tag value")
                try:
                    tag_added = engine.add_tag(category, new_value)
                except TagEngineException as e:
                    warning(e.message)
                    warning(f'Could not add value "{new_value}" to category {category}.')
                    continue
                available_values = engine.get_tags_for_category(category)

            # Use the indices to search through available values.
            values = [available_values[index] for index in indices]

            tags[category] = values
            print(f"Selected tags: {join_selected_tags_names(values, available_values)}")
            print()
            break

    engine.set_tags(file_to_tag, tags)
    engine.save()


# ------------------------------------- Main procedure
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tag files and generate symlink structures.")

    filters_help = "Filters are used by --tag_all option. In case of multiple filters of given type, at least one must be satisfied."

    config_args = parser.add_argument_group("Database configuration")
    config_args.add_argument("-i", "--initialize", action="store_true", help="Create new ftag database. Fails if database is already created.")
    config_args.add_argument("-c", "--add_category", type=str, help="Add a new category to the ftag database.")
    config_args.add_argument("-m", "--add_mime_filter", type=str, help=f"Add a new mime filter as a regex checked against mime type. {filters_help}")
    config_args.add_argument("-p", "--add_path_filter", type=str, help=f"Add a new path filter as a regex checked against file path. {filters_help}")
    config_args.add_argument("-q", "--create_query", action="store_true", help=f"Creates a new query.")
    tagging_args = parser.add_argument_group("File operations")
    tagging_args.add_argument("-g", "--generate", action="store_true", help="Generate symlinks")
    tagging_args.add_argument("-t", "--tag_all", action="store_true", help="Iterate over all untagged files and tag them.")
    tagging_args.add_argument("-f", "--file", type=Path, help="Path to the file to tag interactively")
    args = parser.parse_args()

    if args.initialize:
        initialize_database()
    elif args.add_category:
        engine = load_engine()
        add_category(engine, args.add_category)
    elif args.add_mime_filter:
        engine = load_engine()
        add_mime_filter(engine, args.add_mime_filter)
    elif args.add_path_filter:
        engine = load_engine()
        add_path_filter(engine, args.add_path_filter)
    elif args.create_query:
        engine = load_engine()
        create_query(engine)
    elif args.generate:
        engine = load_engine()
        generate(engine)
    elif args.tag_all:
        engine = load_engine()
        tag_all(engine)
    elif args.file:
        if not args.file.is_file():
            error(f"invalid file {args.file}")
        engine = load_engine()
        tag_file(engine, args.file, False)
    else:
        parser.print_help()
        print()
        error("no action")

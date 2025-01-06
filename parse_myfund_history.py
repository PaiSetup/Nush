#!/bin/python

import argparse
import csv
import datetime
from pathlib import Path


def main(file):
    with open(file, "r", errors="ignore") as csvfile:
        next(csvfile)  # Skip header

        previous_value = 0
        previous_date = None
        for row in csv.reader(csvfile, delimiter=";"):
            # Parse current line
            date = datetime.date(*[int(x) for x in row[0].split("-")])
            value = float(row[1].replace(",", "."))

            # Determine whether we should print the current line. First line should always
            # be printed. Subsequent lines are printed whenever the month changes, because
            # it means we encountered first day of the month.
            if previous_date is None or previous_date.month != date.month:
                if date.day == 1:
                    value_to_display = value
                else:
                    value_to_display = previous_value

                line = f"{date.year}-{str(date.month).zfill(2)}-01;{value_to_display:.2f}"
                line = line.replace(".", ",")
                print(line)

            # Save current line as previous
            previous_value = value
            previous_date = date


if __name__ == "__main__":
    # fmt: off
    description = """
        MyFund offers a chart of total value of all investments over time at https://myfund.pl/index.php?raport=WartoscInwestycjiWCzasie.
        It also allows downloading a csv (delimeted by semicolons). There are datapoints after any financial events, but we'd
        like to just have values at the beginning of each month. This script extracts this information and prints it to stdout as
        csv (delimeted by semicolons).
    """
    arg_parser = argparse.ArgumentParser(description=description, allow_abbrev=False)
    arg_parser.add_argument("file", type=Path, help="CSV file downloaded from MyFund")
    args = arg_parser.parse_args()
    # fmt: on

    main(args.file)

#!/bin/python

import argparse
import csv
import datetime
import json
import sys
from enum import Enum, auto
from pathlib import Path

import requests
from dateutil.relativedelta import relativedelta


class MyFundCsvType:
    TotalInvestmentValue = (0, "investment_value")
    OperationHistory = (1, "operation_history")

    def get_index(self):
        return self[0]

    @staticmethod
    def derive_from_csv_header(header):
        match header:
            case "Data;Value of your investments;;\n" | "Data;Warto inwestycji;;\n":
                return MyFundCsvType.TotalInvestmentValue
            case (
                "Date;Operation;Account;Asset;Currency;Shares;Price;Commition;Tax;Value;Account balance after the operation;Number of units after operation;Investment account;Automatically added;Comment;\n"
                | "Data;Operacja;Konto;Walor;Waluta;Liczba jednostek;Cena;Prowizja;Podatek;Warto;Stan konta po operacji;Liczba jednostek po operacji;Konto inwestycyjne;Automatycznie dodana;Komentarz;\n"
            ):
                return MyFundCsvType.OperationHistory
            case _:
                return None


class OutputData:
    def __init__(self):
        self._data = {}

    def _set_value(self, year, month, idx, value):
        key = f"{year}-{str(month).zfill(2)}-01"
        try:
            entry = self._data[key]
        except KeyError:
            entry = [None, None]
        entry[idx] = value
        self._data[key] = entry

    def set_investment_value(self, year, month, value):
        self._set_value(year, month, 0, value)

    def set_contribution_value(self, year, month, value):
        self._set_value(year, month, 1, value)

    def fill_missing_values(self):
        last_contribution = 0
        for date, values in sorted(self._data.items()):
            if values[1] is None:
                values[1] = last_contribution
                self._data[date] = values
            else:
                last_contribution = values[1]

    def to_csv(self):
        result = "date;contribution_value;investment_value\n"
        for date, values in sorted(self._data.items()):
            result += date
            result += ";"

            if values[1] is not None:
                result += f"{values[1]:.2f}".replace(".", ",")
            result += ";"

            if values[0] is not None:
                result += f"{values[0]:.2f}".replace(".", ",")
            result += ";\n"

        return result


def open_myfund_csv(file_path):
    try:
        file = open(file_path, "r", errors="ignore")
    except:
        return None

    header = next(file)
    csv_type = MyFundCsvType.derive_from_csv_header(header)
    if csv_type is None:
        return None

    reader = csv.reader(file, delimiter=";")
    return file, reader, csv_type


def get_currency_rate(src_currency, date, offset_date_by_one=False):
    # https://api.nbp.pl/api/exchangerates/rates/a/usd/2020-01-13
    src_currency = src_currency.lower()
    result = None

    # Prepare date range. There are no data for weekend dates and holidays, so we'll check a range and select the first date.
    first_date = date
    if offset_date_by_one:
        first_date = first_date + relativedelta(days=1)
    last_date = first_date + relativedelta(days=10)

    # Make a request
    url = f"https://api.nbp.pl/api/exchangerates/rates/a/{src_currency}/{first_date}/{last_date}/?format=json"
    response = requests.get(url)
    if response.status_code != 200:
        return None

    # Parse the request
    jsonResponse = json.loads(response.content)
    return jsonResponse["rates"][0]["mid"]


def parse_total_investment_value_file(reader, output_data):
    previous_value = 0
    previous_date = None
    for row in reader:
        # Parse current line
        date = row[0]
        date = date.split("-")
        date = datetime.date(*[int(x) for x in date])
        value = row[1]
        value = value.replace(",", ".")
        value = float(value)

        # Determine whether we save a new entry to the output data object. We do it in two scenarios:
        #  1. This is the first line.
        #  2. Month changed - it means we encountered the first day of the month.
        if previous_date is None or previous_date.month != date.month:
            if date.day == 1:
                value_to_display = value
            else:
                value_to_display = previous_value

            output_data.set_investment_value(date.year, date.month, value_to_display)

        # Save current line as previous
        previous_value = value
        previous_date = date


def parse_operation_history_file(reader, output_data):
    total_contribution = 0
    previous_date = datetime.date(2000, 1, 1)

    for row in reversed(list(reader)):
        # Parse current line
        date = row[0]
        date = date.split(" ")[0]  # there can be an hour specified after a space. We don't care
        date = date.split("-")
        date = datetime.date(*[int(x) for x in date])
        if date.day != 1:
            date = date.replace(day=1) + relativedelta(months=1)
        operation = row[1]
        currency = row[4]
        value = row[9]
        value = value.replace(",", ".")
        value = float(value)

        # Check whether it's deposit or withdrawal
        match operation:
            case "Cash deposit" | "Wpata":
                delta_sign = 1
            case "Cash withdrawal" | "Wypata":
                delta_sign = -1
            case _:
                continue

        # Verify we're iterating from oldest to latest dates
        if previous_date > date:
            raise ValueError("ERROR: we're probably iterating in the wrong direction. Aborting.")
        previous_date = date

        # Exchange currency to PLN
        if currency != "PLN":
            rate = get_currency_rate(currency, date)
            if rate is None:
                print(f"WARNING: cannot query currency rate for {currency}. Ignoring.", file=sys.stderr)
                continue
            value *= rate

        total_contribution += delta_sign * value

        output_data.set_contribution_value(date.year, date.month, total_contribution)


if __name__ == "__main__":
    # fmt: off
    description = """
        MyFund allows downloading CSV files (semicolon delimeted) with various data from the account. This script consumes these
        files and produces per-month summary as csv. Total investments value is generated based on csv file (1). The numbers in
        the file are presented as-is, just normalized to only show value at first day of each month. Total investment contribution
        is calculated based on csv file (2) by filtering cash deposit/withdrawal events and summing them. Cash operations in foreign
        values are translated to PLN using NBP API.

        Input files are specified as positional cmdline arguments in any order.
          (1) https://myfund.pl/index.php?raport=WartoscInwestycjiWCzasie&dataStart=2022-01-01
          (2) https://myfund.pl/index.php?raport=historiaOperacji&dataStart=2022-01-01
    """
    arg_parser = argparse.ArgumentParser(description=description, allow_abbrev=False)
    arg_parser.add_argument("files", type=Path, nargs="+", help="CSV files downloaded from MyFund")
    args = arg_parser.parse_args()
    # fmt: on

    output_data = OutputData()
    parsed_csv_types = []

    for file_path in args.files:
        # Try to open the file and parse it
        result = open_myfund_csv(file_path)
        if result is None:
            print(f"ERROR: Could not open or parse {file_path}", sys.stderr)
            sys.exit(1)
        file, reader, csv_type = result

        # Verify we haven't seen this file type yet
        if csv_type in parsed_csv_types:
            print(f"ERROR: {csv_type} appeared more than once", sys.stderr)
            sys.exit(1)

        # Parse the file
        with file:
            match csv_type:
                case MyFundCsvType.TotalInvestmentValue:
                    parse_total_investment_value_file(reader, output_data)
                case MyFundCsvType.OperationHistory:
                    parse_operation_history_file(reader, output_data)
                case _:
                    print(f"ERROR: illegal MyFundCsvType ({csv_type})", sys.stderr)
                    sys.exit(1)

    output_data.fill_missing_values()
    print(output_data.to_csv(), end="")

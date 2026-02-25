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
    OperationHistory = auto()
    InvestmentAccountSplit = auto()

    @staticmethod
    def derive_from_csv_header(header):
        match header:
            case "Data;Operacja;Konto;Walor;Waluta;Liczba jednostek;Cena;Prowizja;Podatek;Warto;Stan konta po operacji;Liczba jednostek po operacji;Konto inwestycyjne;Automatycznie dodana;Komentarz;\n":
                return MyFundCsvType.OperationHistory
            case _:
                # There's no specific header for this, because it depends on our investment accounts within MyFund. Detect it heuristically.
                if header.startswith("Data;") and ";Konto gotwkowe;" in header and header.endswith(";;\n"):
                    return MyFundCsvType.InvestmentAccountSplit
                return None


class OutputData:
    class Column:
        def __init__(self, name, data_type, priority):
            self.name = name
            self.data_type = data_type
            self.priority = priority

        def get_sortkey(self):
            return (self.priority, self.name)

    def __init__(self):
        self._data = {}
        self._columns = []

    def _get_column(self, column_name, value, column_priority):
        data_type = type(value)

        # Find existing column. If we find it, verify other fields are matching.
        column_idx = -1
        column = None
        for i, c in enumerate(self._columns):
            if column_name != c.name:
                continue
            if data_type != c.data_type:
                raise TypeError(f"Type of column {column_name} changed")
            if column_priority != c.priority:
                raise TypeError(f"Priority of column {column_name} changed")
            column = c
            column_idx = i
            break

        # If we didn't find the column, create a new one
        if column is None:
            self._columns.append(OutputData.Column(column_name, data_type, column_priority))
            column_idx = len(self._columns) - 1

        return column_idx

    def _align_to_columns(self, entry):
        curr_length = len(entry)
        expected_length = len(self._columns)
        if expected_length > curr_length:
            entry += [None] * (expected_length - curr_length)
        return entry

    def set_value(self, year, month, column_name, value, column_priority):
        # Get existing column index or create new
        column_idx = self._get_column(column_name, value, column_priority)

        # Get existing data row or create new
        key = f"{year}-{str(month).zfill(2)}-01"
        try:
            entry = self._data[key]
        except KeyError:
            entry = []
        entry = self._align_to_columns(entry)

        # Write new data
        entry[column_idx] = value
        self._data[key] = entry

    def fill_missing_values(self, zero_fill=False):
        # Make sure all rows have the same number of columns
        for date, entry in self._data.items():
            self._data[date] = self._align_to_columns(entry)

        column_count = len(self._columns)
        zero_values = [c.data_type(0) for c in self._columns]
        last_values = zero_values.copy()
        for date, entry in sorted(self._data.items()):
            for column_idx in range(column_count):
                if entry[column_idx] is None:
                    if zero_fill:
                        entry[column_idx] = zero_values[column_idx]
                    else:
                        entry[column_idx] = last_values[column_idx]
                        self._data[date] = entry
                else:
                    last_values[column_idx] = entry[column_idx]

    def to_csv(self):
        to_str_funcs = {
            int: lambda i: str(int(i)),
            float: lambda f: f"{f:.2f}".replace(".", ","),
        }

        # Sort columns alphabetically by name and prepare a reorder list so we can reorder each row in the same way
        reordered_columns = sorted(self._columns, key=lambda c: c.get_sortkey())
        reorder_list = sorted(range(len(self._columns)), key=lambda i: self._columns[i].get_sortkey())

        # Create header
        result = "date;"
        result += ";".join([c.name for c in reordered_columns])
        result += "\n"

        # Create data lines
        for date, entry in sorted(self._data.items()):
            result += date
            result += ";"

            reordered_entry = [entry[i] for i in reorder_list]

            for column, value in zip(reordered_columns, reordered_entry):
                result += to_str_funcs[column.data_type](value)
                result += ";"

            result += "\n"

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
    return file, reader, header, csv_type


def get_currency_rate(src_currency, date, offset_date_by_one=True):
    src_currency = src_currency.lower()

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


def parse_date(date_str, align_to_next_month):
    date = date_str
    date = date.split(" ")[0]  # there can be an hour specified after a space. We don't care
    date = date.split("-")
    date = datetime.date(*[int(x) for x in date])
    if align_to_next_month:
        if date.day != 1:
            date = date.replace(day=1) + relativedelta(months=1)
    return date


def parse_float(float_str):
    value = float_str
    value = value.replace(",", ".")
    value = value.replace(" ", "")
    value = float(value)
    return value


class PolishBondCounter:
    class Bond:
        def __init__(self, product, count):
            maturity_year = int("20" + product[5:7])
            maturity_month = int(product[3:5])
            self.product = product
            self.maturity_date = datetime.date(maturity_year, maturity_month, 1)
            self.count = count
            self.sell_ops = []

    def __init__(self):
        self._edo_list = []

    def buy(self, product, count):
        if product.startswith("EDO"):
            self._edo_list.append(PolishBondCounter.Bond(product, count))
        else:
            raise ValueError("Unsupported Polish bond")

    def sell(self, product, count_to_sell, date):
        if count_to_sell > 0:
            raise ValueError("Expected negative value")
        count_to_sell = -count_to_sell

        if product.startswith("EDO"):
            for bond in self._edo_list:
                if product != bond.product:
                    continue

                # Calculate how much we can sell. Add a sell op
                already_sold_count = sum((c for _, c in bond.sell_ops))
                left_count = bond.count - already_sold_count
                curr_sell_count = min(left_count, count_to_sell)
                bond.sell_ops.append((date, curr_sell_count))

                # If we have no more to sell, we can exit
                count_to_sell -= curr_sell_count
                if count_to_sell == 0:
                    break
        else:
            raise ValueError("Unsupported Polish bond")

    def get_count(self, date):
        count = 0
        for bond in self._edo_list:
            # Check if this bond is mature and has already ended
            if bond.maturity_date <= date:
                continue

            # Calculate how many bonds of this type we have unsold
            bond_count = bond.count
            for sell_date, sell_count in bond.sell_ops:
                if sell_date <= date:
                    bond_count -= sell_count

            count += bond_count
        return count


def parse_investment_account_split(reader, header, output_data):
    # Parse the header, so we now how accounts we have
    accounts = header.strip().split(";")
    accounts = [x for x in accounts if x]
    accounts = accounts[1:]
    accounts_count = len(accounts)
    column_names = [f"value ({x})" for x in accounts]

    for row in list(reader):
        date = parse_date(row[0], align_to_next_month=True)

        values = row[1 : 1 + accounts_count]
        values = [parse_float(x) for x in values]
        for column_name, value in zip(column_names, values):
            output_data.set_value(date.year, date.month, column_name, value, 2)


def parse_operation_history_file(reader, output_data):
    previous_date = datetime.date(2000, 1, 1)
    polish_bonds = PolishBondCounter()
    contribution_per_account = {}

    for row in reversed(list(reader)):
        # Parse current line
        real_date = parse_date(row[0], align_to_next_month=False)
        next_aligned_date = parse_date(row[0], align_to_next_month=True)
        operation = row[1]
        product = row[3]
        currency = row[4]
        count = row[5]
        count = None if count == "-" else int(count)
        value = parse_float(row[9])
        account = row[12]
        if not account:
            raise ValueError("No investment account set")

        # Handle cash deposit/withdrawal to calculate contribution value
        # TODO do this lazily
        if currency != "PLN":
            rate = get_currency_rate(currency, real_date)
            if rate is None:
                print(f"WARNING: cannot query currency rate for {currency}. Ignoring.", file=sys.stderr)
                continue
            value *= rate

        # Verify we're iterating from oldest to latest dates
        if previous_date > real_date:
            raise ValueError("ERROR: we're probably iterating in the wrong direction. Aborting.")
        previous_date = real_date

        is_cash_op = operation in ["Wpata", "Wypata"]
        is_buy_sell_op = operation in ["Kupno", "Sprzeda"]
        is_buy_op = operation == "Kupno"

        # Check operation type
        if is_cash_op:
            if account not in contribution_per_account:
                contribution_per_account[account] = float(0)
            contribution_per_account[account] += value  # 'value' is correctly signed

            output_data.set_value(next_aligned_date.year, next_aligned_date.month, f"contribution ({account})", contribution_per_account[account], 1)
        elif is_buy_sell_op and product.startswith("EDO"):
            if is_buy_op:
                polish_bonds.buy(product, count)
            else:
                polish_bonds.sell(product, count, real_date)

        # Update polish bonds value. Theoretically this is not correct, because this code gets called after a financial operation
        # and bonds could get mature in a month without any operations. In that case it will be updated only after the next operation.
        output_data.set_value(next_aligned_date.year, next_aligned_date.month, "polish bond count", polish_bonds.get_count(next_aligned_date), 0)


if __name__ == "__main__":
    # fmt: off
    description = """
MyFund allows downloading CSV files (semicolon delimeted) with various data from the account. This script consumes these
files and produces per-month summary as csv. All outputs are normalized to show values as of the first day of each month.
For example, if some shares were bought May 16, they will show up for June, not for May.

Input files are specified as positional cmdline arguments in any order.
    (1) https://myfund.pl/index.php?raport=historiaOperacji&dataStart=2022-01-01
    (2) https://myfund.pl/index.php?raport=SkladPortfelaKonta&dataStart=2022-01-01

Investment contribution is retrieved per investment account based on csv file (1) by filtering cash deposit/withdrawal events
and summing them. Cash operations in foreign values are translated to PLN using NBP API. File (2) is also used to calculate
current number of polish bonds owned.

File (2) is used to retrieve investment values for each investment account.
    """
    arg_parser = argparse.ArgumentParser(description=description, allow_abbrev=False, formatter_class=argparse.RawTextHelpFormatter)
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
        file, reader, header, csv_type = result

        # Verify we haven't seen this file type yet
        if csv_type in parsed_csv_types:
            print(f"ERROR: {csv_type} appeared more than once", sys.stderr)
            sys.exit(1)

        # Parse the file
        with file:
            match csv_type:
                case MyFundCsvType.OperationHistory:
                    parse_operation_history_file(reader, output_data)
                case MyFundCsvType.InvestmentAccountSplit:
                    parse_investment_account_split(reader, header, output_data)
                case _:
                    print(f"ERROR: illegal MyFundCsvType ({csv_type})", sys.stderr)
                    sys.exit(1)

    output_data.fill_missing_values()
    print(output_data.to_csv(), end="")

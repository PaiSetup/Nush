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
    TotalInvestmentValue = auto()
    OperationHistory = auto()
    InvestmentAccountSplit = auto()

    @staticmethod
    def derive_from_csv_header(header):
        match header:
            case "Data;Warto inwestycji;;\n":
                return MyFundCsvType.TotalInvestmentValue
            case "Data;Operacja;Konto;Walor;Waluta;Liczba jednostek;Cena;Prowizja;Podatek;Warto;Stan konta po operacji;Liczba jednostek po operacji;Konto inwestycyjne;Automatycznie dodana;Komentarz;\n":
                return MyFundCsvType.OperationHistory
            case _:
                # There's no specific header for this, because it depends on our investment accounts within MyFund. Detect it heuristically.
                if header.startswith("Data;") and ";Konto gotwkowe;" in header and header.endswith(";;\n"):
                    return MyFundCsvType.InvestmentAccountSplit
                return None


class OutputData:
    def __init__(self):
        self._data = {}
        self._investment_accounts = []

    def _set_value(self, year, month, idx, value):
        key = f"{year}-{str(month).zfill(2)}-01"
        try:
            entry = self._data[key]
        except KeyError:
            entry = [None, None, None, None]
        entry[idx] = value
        self._data[key] = entry

    def set_contribution_value(self, year, month, value):
        self._set_value(year, month, 0, value)

    def set_investment_value(self, year, month, value):
        self._set_value(year, month, 1, value)

    def set_polish_bonds_count(self, year, month, count):
        self._set_value(year, month, 2, count)

    def set_investment_accounts(self, accounts):
        self._investment_accounts = accounts

    def set_per_account_values(self, year, month, values):
        if len(self._investment_accounts) != len(values):
            raise ValueError("Invalid number of per account values")
        self._set_value(year, month, 3, values)

    def fill_missing_values(self, zero_fill=False):
        zero_values = [
            0,
            0,
            0,
            [0] * len(self._investment_accounts),
        ]
        last_values = zero_values.copy()
        for date, values in sorted(self._data.items()):
            for idx in range(len(last_values)):
                if values[idx] is None:
                    if zero_fill:
                        values[idx] = zero_values[idx]
                    else:
                        values[idx] = last_values[idx]
                        self._data[date] = values
                else:
                    last_values[idx] = values[idx]

    def to_csv(self):
        float_to_str = lambda f: f"{f:.2f}".replace(".", ",")
        int_to_str = lambda i: str(int(i))

        # Create header
        result = "date;contribution_value;investment_value;polish_bond_count"
        if self._investment_accounts:
            result += ";"
            result += ";".join((f"value ({x})" for x in self._investment_accounts))
        result += "\n"

        # Create data lines
        for date, values in sorted(self._data.items()):
            result += date

            result += ";"
            result += float_to_str(values[0])

            result += ";"
            result += float_to_str(values[1])

            result += ";"
            result += int_to_str(values[2])

            for value in values[3]:
                result += ";"
                result += float_to_str(value)
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


def parse_total_investment_value_file(reader, output_data):
    for row in reader:
        date = parse_date(row[0], align_to_next_month=True)
        value = parse_float(row[1])
        output_data.set_investment_value(date.year, date.month, value)


def parse_investment_account_split(reader, header, output_data):
    # Parse the header, so we now how accounts we have
    accounts = header.strip().split(";")
    accounts = [x for x in accounts if x]
    accounts = accounts[1:]
    accounts_count = len(accounts)
    output_data.set_investment_accounts(accounts)

    for row in list(reader):
        date = parse_date(row[0], align_to_next_month=True)

        values = row[1 : 1 + accounts_count]
        values = [parse_float(x) for x in values]
        output_data.set_per_account_values(date.year, date.month, values)


def parse_operation_history_file(reader, output_data):
    total_contribution = 0
    previous_date = datetime.date(2000, 1, 1)
    polish_bonds = PolishBondCounter()

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

        # Handle cash deposit/withdrawal to calculate contribution value
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
            total_contribution += value  # Value is correctly signed
            output_data.set_contribution_value(next_aligned_date.year, next_aligned_date.month, total_contribution)
        elif is_buy_sell_op and product.startswith("EDO"):
            if is_buy_op:
                polish_bonds.buy(product, count)
            else:
                polish_bonds.sell(product, count, real_date)

        # Update polish bonds value. Theoretically this is not correct, because this code gets called after a financial operation
        # and bonds could get mature in a month without any operations. In that case it will be updated only after the next operation.
        output_data.set_polish_bonds_count(next_aligned_date.year, next_aligned_date.month, polish_bonds.get_count(next_aligned_date))


if __name__ == "__main__":
    # fmt: off
    description = """
        MyFund allows downloading CSV files (semicolon delimeted) with various data from the account. This script consumes these
        files and produces per-month summary as csv. All outputs are normalized to show values as of the first day of each month.
        For example, if some shares we bough May 16, they will show up for June, not for May.

        Input files are specified as positional cmdline arguments in any order.
          (1) https://myfund.pl/index.php?raport=WartoscInwestycjiWCzasie&dataStart=2022-01-01
          (2) https://myfund.pl/index.php?raport=historiaOperacji&dataStart=2022-01-01
          (3) https://myfund.pl/index.php?raport=SkladPortfelaKonta&dataStart=2022-01-01

        Total investments value is generated based on csv file (1). The numbers in the file are presented as-is, just normalized to
        only show value at first day of each month.

        Total investment contribution is calculated based on csv file (2) by filtering cash deposit/withdrawal events and summing them.
        Cash operations in foreign values are translated to PLN using NBP API. File (2) is also used to calculate current number of
        polish bonds owned.

        File (3) is used to retrieve values for each investment account.
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
        file, reader, header, csv_type = result

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
                case MyFundCsvType.InvestmentAccountSplit:
                    parse_investment_account_split(reader, header, output_data)
                case _:
                    print(f"ERROR: illegal MyFundCsvType ({csv_type})", sys.stderr)
                    sys.exit(1)

    output_data.fill_missing_values()
    print(output_data.to_csv(), end="")

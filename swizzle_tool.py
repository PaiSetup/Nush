#!/bin/python

from argparse import ArgumentParser
from enum import Enum


class SwizzleNotation(Enum):
    Xyzw = "XYZW"
    Rgba = "RGBA"
    NumbersZero = "0123"
    NumbersOne = "1234"


def error(*args, **kwargs):
    print("ERROR: ", *args, **kwargs)
    exit(1)


class Swizzle:
    def __init__(self, pattern_value):
        self._pattern_value = pattern_value

    @staticmethod
    def parse_pattern_notation(pattern_string):
        if len(pattern_string) != 4:
            error("Pattern must be 4 characters.")

        detected_notation = None
        for notation in SwizzleNotation:
            is_valid = [c in notation.value for c in pattern_string.upper()]
            is_valid = all(is_valid)
            if is_valid:
                detected_notation = notation
                break

        if detected_notation is None:
            error("Invalid pattern notation.")

        return detected_notation

    @staticmethod
    def from_string(pattern_string, notation):
        try:
            pattern_value = [notation.value.index(c) for c in pattern_string.upper()]
            return Swizzle(pattern_value)
        except ValueError:
            error("Invalid pattern value.")

    def reverse_pattern(self):
        self._pattern_value = [self._pattern_value.index(v) for v in [0, 1, 2, 3]]

    def format_pattern(self, notation):
        return "".join([notation.value[v] for v in self._pattern_value])

    def apply(self, vector):
        return [vector[v] for v in self._pattern_value]


if __name__ == "__main__":
    # fmt: off
    arg_parser = ArgumentParser(description="Downscale images to match given disk size constraints.", allow_abbrev=False)
    subparsers = arg_parser.add_subparsers(dest='command', required=True)

    arg_parser_reverse = subparsers.add_parser('reverse')
    arg_parser_reverse.add_argument('pattern', type=str)
    arg_parser_reverse.add_argument('-o', '--out', type=SwizzleNotation, required=False, default=None)

    arg_parser_apply = subparsers.add_parser('apply')
    arg_parser_apply.add_argument('component0', type=str)
    arg_parser_apply.add_argument('component1', type=str)
    arg_parser_apply.add_argument('component2', type=str)
    arg_parser_apply.add_argument('component3', type=str)
    arg_parser_apply.add_argument('patterns', type=str, nargs='+')

    arg_parser_convert = subparsers.add_parser('convert')
    arg_parser_convert.add_argument('pattern', type=str)
    arg_parser_convert.add_argument("out", type=SwizzleNotation)

    args = arg_parser.parse_args()
    # fmt: on

    match (args.command):
        case "reverse":
            inp_notation = Swizzle.parse_pattern_notation(args.pattern)
            out_notation = args.out if args.out is not None else inp_notation

            swizzle = Swizzle.from_string(args.pattern, inp_notation)
            swizzle.reverse_pattern()
            print(swizzle.format_pattern(out_notation))
        case "apply":
            vector = [args.component0, args.component1, args.component2, args.component3]

            for pattern in args.patterns:
                inp_notation = Swizzle.parse_pattern_notation(pattern)
                swizzle = Swizzle.from_string(pattern, inp_notation)
                vector = swizzle.apply(vector)

            for component in vector:
                print(component, end=" ")
            print()
        case "convert":
            inp_notation = Swizzle.parse_pattern_notation(args.pattern)
            out_notation = args.out if args.out is not None else inp_notation
            swizzle = Swizzle.from_string(args.pattern, inp_notation)
            print(swizzle.format_pattern(out_notation))

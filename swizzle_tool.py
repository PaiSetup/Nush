#!/bin/python

from argparse import ArgumentParser
from enum import Enum


class SwizzleNotation(Enum):
    Xyzw = "XYZW"
    Rgba = "RGBA"
    Yuva = "YUVA"
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
            error(f'Invalid pattern "{pattern_string}". Must be 4 characters.')

        detected_notation = None
        for notation in SwizzleNotation:
            is_valid = [c in notation.value for c in pattern_string.upper()]
            is_valid = all(is_valid)
            if is_valid:
                detected_notation = notation
                break

        if detected_notation is None:
            error(f'Invalid pattern "{pattern_string}". Unexpected characters.')

        return detected_notation

    @staticmethod
    def from_string(pattern_string, notation):
        try:
            pattern_value = [notation.value.index(c) for c in pattern_string.upper()]
            return Swizzle(pattern_value)
        except ValueError:
            error("Invalid pattern value.")

    @staticmethod
    def find_swizzle(vector_src, vector_dst, allow_duplicates):
        available_indices = [0, 1, 2, 3]
        result = [None, None, None, None]

        for dst_i, dst in enumerate(vector_dst):
            # Find matching element in src vector
            src_i = None
            src = None
            for i in available_indices:
                if vector_src[i] == dst:
                    src_i = i
                    src = vector_src[i]
                    break
            if src is None:
                error("Cannot match src and dst vectors")

            # Remove from allowed indices list
            if not allow_duplicates:
                available_indices.remove(i)

            result[dst_i] = src_i

        return Swizzle(result)

    @staticmethod
    def solve(vector_src, pre_swizzles, post_swizzles, vector_dst, allow_duplicates):
        for s in pre_swizzles:
            vector_src = s.apply(vector_src)
        for s in post_swizzles:
            vector_dst = s.reverse_pattern().apply(vector_dst)

        return Swizzle.find_swizzle(vector_src, vector_dst, allow_duplicates)

    def reverse_pattern(self):
        new_value = [self._pattern_value.index(v) for v in [0, 1, 2, 3]]
        return Swizzle(new_value)

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

    arg_parser_solve = subparsers.add_parser('solve')
    arg_parser_solve.add_argument('component_src0', type=str)
    arg_parser_solve.add_argument('component_src1', type=str)
    arg_parser_solve.add_argument('component_src2', type=str)
    arg_parser_solve.add_argument('component_src3', type=str)
    arg_parser_solve.add_argument('rest', type=str, nargs='+')
    arg_parser_solve.add_argument('-o', '--out', type=SwizzleNotation, default=SwizzleNotation.Rgba)
    arg_parser_solve.add_argument('-d', '--allow-duplicates', action="store_true")

    args = arg_parser.parse_args()
    # fmt: on

    match (args.command):
        case "reverse":
            inp_notation = Swizzle.parse_pattern_notation(args.pattern)
            out_notation = args.out if args.out is not None else inp_notation

            swizzle = Swizzle.from_string(args.pattern, inp_notation)
            swizzle = swizzle.reverse_pattern()
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
        case "solve":
            vector_src = [args.component_src0, args.component_src1, args.component_src2, args.component_src3]

            # The question mark will show boundary between pre-swizzles and post-swizzles
            try:
                position = args.rest.index("?")
            except ValueError:
                position = -1
            if position == -1:
                # No question mark. Only source and destination vectors should be present.
                # Do not let passing extra swizzles, because we wouldn't know which ones
                # are pre-swizzles and which ones are post-swizzles.
                if len(args.rest) < 4:
                    arg_parser_solve.print_help()
                    error("Destination vector not fully specified.")
                if len(args.rest) > 4:
                    arg_parser_solve.print_help()
                    error('Too many arguments. Either specify "?" to show which swizzle is searched or specify only src and dst vectors')
                pre_swizzles = []
                post_swizzles = []
                vector_dst = args.rest
            else:
                # Question mark shows the location of the swizzle we are searching for.
                if position >= len(args.rest) - 4:
                    arg_parser_solve.print_help()
                    error("Destination vector not fully specified.")
                vector_dst = args.rest[-4:]
                pre_swizzles = args.rest[:position]
                post_swizzles = args.rest[position + 1 : -4]

            # Parse the swizzles
            pre_swizzles = [Swizzle.from_string(s, Swizzle.parse_pattern_notation(s)) for s in pre_swizzles]
            post_swizzles = [Swizzle.from_string(s, Swizzle.parse_pattern_notation(s)) for s in post_swizzles]

            swizzle = Swizzle.solve(vector_src, pre_swizzles, post_swizzles, vector_dst, args.allow_duplicates)
            print(swizzle.format_pattern(args.out))

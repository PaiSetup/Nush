#!/usr/bin/env bash
#
# subdir-stats.sh - per-subdirectory file count, disk usage and average file size.
#
# Usage: subdir-stats.sh [DIRECTORY]
#   DIRECTORY  directory whose immediate subdirectories are reported
#              (default: current working directory)
#
# Output: one line per immediate subdirectory, sorted by MiB/file, largest first.
# Sizes are disk usage (allocated blocks) in binary units (GiB / MiB).
# Hidden (dot) subdirectories are skipped.

set -euo pipefail

target=${1:-.}

if [[ ! -d $target ]]; then
    echo "Error: '$target' is not a directory" >&2
    exit 1
fi

# awk program: reads "files<TAB>KiB<TAB>name" and emits
# "sortkey<TAB>formatted line". The sort key (MiB/file) is stripped later.
awk_program='
BEGIN { FS = "\t" }
{
    files = $1
    kib   = $2
    name  = $3

    gib          = kib / 1024 / 1024                      # KiB -> GiB
    mib_per_file = (files > 0) ? kib / 1024 / files : 0   # avoid divide-by-zero

    printf "%.6f\t%8d files  %10.3f GiB  %10.4f MiB/file  %s\n",
           mib_per_file, files, gib, mib_per_file, name
}
'

for dir in "$target"/*/; do
    [[ -d $dir ]] || continue                         # glob matched nothing
    files=$(find "$dir" -type f | wc -l)              # number of files, recursive
    kib=$(du -sk "$dir" | cut -f1)                    # disk usage in KiB
    printf '%d\t%d\t%s\n' "$files" "$kib" "$(basename "$dir")"
done |                                                # one TSV record per subdir
    LC_ALL=C awk "$awk_program" |                     # compute GiB, MiB/file, format line
    LC_ALL=C sort -t$'\t' -k1,1 -nr |                 # sort by MiB/file key, descending
    cut -f2-                                          # drop the sort key column
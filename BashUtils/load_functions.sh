#!/bin/sh

load_functions() {
    for file in $(find "$SCRIPTS_PATH" -mindepth 2 -name "*.sh"); do
        source "$file"
    done
}

if [ -z "$1" ] || [ ! -d "$1" ]; then
    echo "ERROR: load_functions() requires a valid path to scripts directory." >&2
    return
fi

SCRIPTS_PATH="$1"
IS_LINUX=$(uname -a | grep -cv "Linux")
load_functions

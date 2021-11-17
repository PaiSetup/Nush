#!/bin/sh

load_functions() {
    for file in $(find "$SCRIPTS_PATH" -mindepth 2 -name "*.sh"); do
        . "$file"
    done
}

if [ -z "$SCRIPTS_PATH" ] || [ ! -d "$SCRIPTS_PATH" ]; then
    echo "ERROR: load_functions() requires SCRIPTS_PATH variable to be set to a valid directory." >&2
    return
fi

export IS_LINUX=$(uname -a | grep -cv "Linux")
load_functions

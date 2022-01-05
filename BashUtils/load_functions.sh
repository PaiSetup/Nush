#!/bin/sh

export IS_LINUX="$(uname -a | grep -cv "Linux")"

load_functions() {
    # Sanity checks
    if [ -z "$SCRIPTS_PATH" ] || [ ! -d "$SCRIPTS_PATH" ]; then
        echo "ERROR: load_functions() requires SCRIPTS_PATH variable to be set to a valid directory." >&2
        return
    fi

    # Actual loading
    forbidden_dir="$([ "$IS_LINUX" = 0 ] && echo windows || echo linux)"
    for file in $(find "$SCRIPTS_PATH" -mindepth 2 -name "*.sh" -not -path "*/$forbidden_dir/*" -not -path "*/runnable/*"); do
        . "$file"
    done
}
load_functions

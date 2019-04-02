load_functions() {
    pushd $FUNCTIONS_PATH > /dev/null
    while read script_file; do
        . "$script_file"
    done <<< `find . -mindepth 2 | grep "\.sh$"`
    popd > /dev/null
}

load_functions

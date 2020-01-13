load_functions() {
    pushd "$SCRIPTS_PATH/BashUtils" > /dev/null
    counter=0
    while read script_file; do
        . "$script_file"
        counter=$((counter+1))
    done <<< `find . -mindepth 2 | grep "\.sh$" | grep -v "^\./Runnable/"`
    popd > /dev/null
    # echo "Loaded $counter script files"
}

load_functions

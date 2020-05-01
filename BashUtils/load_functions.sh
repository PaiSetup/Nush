load_functions() {
    pushd `dirname $BASH_SOURCE` > /dev/null

    . ./load_paths.sh $@
    while read script_file; do
        . "$script_file"
    done <<< `find . -mindepth 2 | grep "\.sh$" | grep -v "^\./Runnable/"`

    popd > /dev/null
}

load_functions $@

#!/bin/bash

load_functions() {
    # Temporarily go to the scripts directory
    local scripts_path
    scripts_path=$(realpath "${BASH_SOURCE[0]}" | xargs dirname)
    initial_dir=$(pwd)
    cd "$scripts_path" || return

    generate_cached_paths_windows() {
        # Find programs directory
        for value in "/e/Programs" "/d/Programs" "/e/Programy" "/d/Programy"; do
            if [ -d "$value" ];  then
                local programs_dir
                programs_dir="$value"
                break
            fi
        done
        if [ -z "$programs_dir" ]; then
            echo "ERROR: could not find programs directory"
            return 1
        fi
        echo "Will be looking for programs in $programs_dir"

        # Helper function for finding executables and putting them into paths.sh
        find_exe() {
            local variable_name="$1"
            local possible_directory_names="$2"
            local exe_name="$3"
            for possible_directory_name in $possible_directory_names; do
                local dir
                dir="$programs_dir/$possible_directory_name"
                if ! [ -d "$dir" ]; then
                    continue
                fi

                local found_path
                found_path=$(find "$programs_dir/$possible_directory_name" -type f -executable -name "$exe_name" | head -1)
                if [ -n "$found_path" ]; then
                    add_entry "$variable_name" "$found_path"
                    return
                fi
            done
            echo "  Did not find $exe_name" >&2
        }

        # Executables list
        find_exe  NPP_PATH        Notepad++      notepad++.exe
        find_exe  VERACRYPT_PATH  VeraCrypt      VeraCrypt-x64.exe
        find_exe  ICONFIGURE_PATH Iconfigure     Iconfigure.exe
    }

    generate_cached_paths_linux() {
        # Helper function for finding binaries and putting them into paths.sh
        find_binary() {
            local variable_name
            local binary_name
            local found_path

            variable_name="$1"
            binary_name="$2"
            found_path=$(which "$binary_name")
            if [ $? == 0 ]; then
                add_entry "$variable_name" "$found_path"
            else
                echo "  Did not find $binary_name" >&2
            fi
        }

        # Binaries list
        find_binary XRANDR_PATH xrandr
    }

    generate_cached_paths() (
        add_entry() {
            local variable_name="$1"
            local variable_value="$2"
            loaded_paths+=("$variable_name")
            echo "export $variable_name=$variable_value" >> paths.sh
        }

        # Preamble
        local loaded_paths=()
        echo "# Paths loaded by load_functions.sh script, do not change it." > paths.sh
        add_entry SCRIPTS_PATH "$scripts_path"

        # Os-specific search
        local isLinux=$(uname -a | grep -c Linux)
        if [ $isLinux == 1 ]; then
            generate_cached_paths_linux
        else
            generate_cached_paths_windows
        fi

        # Epilogue
        add_entry LOADED_PATHS "$(echo "(${loaded_paths[@]})")"

        # Print the file to the console
        printf "Generated paths.sh file:\n\n"
        cat paths.sh
        printf "\n"
    )

    # Generate paths.sh file if it's not present
    if [ ! -e paths.sh ]; then
        echo "paths.sh file was not found. This must be the first run of the script suite. Searching for paths in system..."
        generate_cached_paths 2>&1
        if [ $? != 0 ]; then
            echo "ERROR: path searching failed."
            rm paths.sh 2>/dev/null
        fi
    fi

    # Run and validate paths.sh file if it is present
    if [ -f paths.sh ]; then
        # Import all cached paths to environment variables
        . ./paths.sh

        # Validate that all paths still exist
        local validation_error=0
        for loaded_path_name in ${LOADED_PATHS[@]}; do
            loaded_path_value="${!loaded_path_name}"
            if [ ! -e "$loaded_path_value" ]; then
                echo "WARNING: \"$loaded_path_name=$loaded_path_value\" path was not found"
                eval "export $loaded_path_name="
                validation_error=1
            fi
        done
        if [ "$validation_error" == 1 ]; then
            cache_file_path=$(realpath "${BASH_SOURCE[0]}" | xargs dirname).paths.sh
            echo "Invalid path(s) came from \"$cache_file_path\" cache file."
            echo "Deleting the file will cause regeneration at next terminal launch."
        fi
    fi

    # Load all functions to namespace
    while read -r script_file; do
        . "$script_file"
    done <<< $(find . -mindepth 2 | grep "\.sh$" | grep -v "^\./Runnable/")

    cd "$initial_dir" || return
}

load_functions "$@"

#!/bin/sh

if [ $IS_LINUX != 0 ] ; then
    return
fi

get_array_count() {
    echo "$#"
}

split_array() {
    for element in $@; do
        echo "$element"
    done
}

print_array_in_lines() {
    indent="$1"
    shift
    split_array $@ | awk "{printf(\"$indent%d. %s\n\", NR-1, \$0)}"
}

get_array_element() {
    index="$1"
    shift
    current_index=0
    for element in $@; do
        if [ "$current_index" = "$index" ]; then
            echo "$element"
            return 0
        fi
        current_index=$((current_index+1))
    done
    return 1
}

set_resolution() (
    # Helper function
    validate_index_selection() (
        selection="$1"
        count="$2"

        if ! echo "$selection" | grep -Eq "^[0-9]+$" ; then
            echo "ERROR: specify a non-negative integer" >&2
            echo 1
            return
        fi
        if [ 0 -gt "$selection" ] || [ "$selection" -ge "$count" ]; then
            echo "ERROR: index must be between 0 and $((count-1)) (inclusive)" >&2
            echo 1
            return
        fi

        echo 0
    )

    # Get displays
    displays=$(xrandr | grep " connected" | cut -d' ' -f1)
    displays_count=$(get_array_count $displays)

    # Validate we have at least one display
    if [ "$displays_count" = 0 ];  then
        echo "ERROR: No displays found" >&2
        return
    fi

    # Select display
    echo "Available displays:"
    print_array_in_lines "  " $displays
    printf "Select display by typing its index (default: 0): "
    read -r selected_display
    if [ -z "$selected_display" ]; then
        selected_display=0
    fi

    # Validate selection
    valid_display_selection=$(validate_index_selection "$selected_display" "$displays_count")
    if [ "$valid_display_selection" != 0 ]; then
        return 1
    fi
    display=$(get_array_element $selected_display $displays)
    echo

    # Get resolutions
    resolutions=$(xrandr | sed -n "/$display/,\$p" | grep -v connected | awk '{print $1}')
    resolutions_count=$(get_array_count $displays)

    # Validate we have at least one resolution
    if [ "$resolutions_count" = 0 ]; then
        echo "ERROR: No resolutions found" >&2
        return
    fi

    # Select resolution
    echo "Available resolutions:"
    print_array_in_lines "  " $resolutions
    printf "Select resolution by typing its index: "
    read -r selected_resolution

    # Validate selection
    valid_resolution_selection=$(validate_index_selection "$selected_resolution" "$resolutions_count")
    if [ "$valid_resolution_selection" != 0 ]; then
        return 1
    fi
    resolution=$(get_array_element "$selected_resolution" $resolutions)
    echo

    # Perform operation
    command="xrandr --output $display --mode $resolution"
    echo "$command"
    eval "$command"
)


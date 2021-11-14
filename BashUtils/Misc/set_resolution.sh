if [ -z "$XRANDR_PATH" ]; then
    return
fi

function set_resolution() (
    # Helper function
    function validate_index_selection() (
        selection="$1"
        count="$2"

        if ! [[ $selection =~ ^[0-9]+$ ]]; then
            echo "ERROR: specify a non-negative integer" >&2
            echo 1
            return
        fi
        if ! [ 0 -le $selection -a $selection -lt $count ]; then
            echo "ERROR: index must be between 0 and $((count-1)) (inclusive)" >&2
            echo 1
            return
        fi

        echo 0
    )

    # Get displays
    displays=()
    displays_count=0
    while read -r line; do
        displays[$displays_count]=$line
        displays_count=$((displays_count+1))
    done < <(xrandr | grep " connected")

    # Validate we have at least one display
    if [ $displays_count == 0 ];  then
        echo "ERROR: No displays found" >&2
        return
    fi

    # Select display
    echo "Available displays:"
    for index in ${!displays[*]}; do
        echo "  $index: ${displays[$index]}"
    done
    echo -n "Select display by typing its index (default: 0): "
    read selected_display
    if [ -z "$selected_display"]; then
        selected_display=0
    fi

    # Validate selection
    valid_display_selection=`validate_index_selection "$selected_display" "$displays_count"`
    if [ "$valid_display_selection" != 0 ]; then
        return 1
    fi
    display=${displays[selected_display]}
    display=`echo $display | cut -d' ' -f1`
    echo

    # Get resolutions
    resolutions=()
    resolutions_count=0
    while read -r line; do
        resolutions[$resolutions_count]=$line
        resolutions_count=$((resolutions_count+1))
    done < <(xrandr | sed -n "/$display/,\$p" | tail -n +2 | sed -n '/connected/q;p')

    # Validate we have at least one resolution
    if [ $resolutions_count == 0 ]; then
        echo "ERROR: No resolutions found" >&2
        return
    fi

    # Select display
    echo "Available resolutions for $display:"
    for index in ${!resolutions[*]}; do
        echo "  $index: ${resolutions[$index]}"
    done
    echo -n "Select resolution by typing its index: "
    read selected_resolution

    # Validate selection
    valid_resolution_selection=`validate_index_selection "$selected_resolution" "$resolutions_count"`
    if [ "$valid_display_selection" != 0 ]; then
        return 1
    fi
    resolution=${resolutions[selected_resolution]}
    resolution=`echo $resolution | cut -d' ' -f1`
    echo

    # Perform operation
    command="xrandr --output $display --mode $resolution"
    echo "$command"
    eval $command
)


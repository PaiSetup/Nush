#!/usr/bin/sh

resolve_pacman_groups() {
    while IFS= read -r line; do
        if ! yay -Qgq "$line" 2>/dev/null; then
                echo "$line"
        fi
    done
}

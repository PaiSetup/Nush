#!/bin/sh

get_unmapped_xdg_mime_types() {
    tmp_file="$(mktemp)"
    find . -not -path "./.java/*"                |
        xargs -I{} realpath "{}"                 |
        xargs -I{} xdg-mime query filetype  "{}" |
        sort                                     | 
        uniq                                     > "$tmp_file"

    while read -r m; do
        if ! grep -q "$m" ~/.config/mimeapps.list; then
            echo "$m"
        fi
    done < "$tmp_file"

    rm "$tmp_file"
}

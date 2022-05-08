#!/bin/sh

todo() {
    file="$HOME/Notes/Todo.md"
    if [ "$1" = "e" ]; then
        which obsidian >/dev/null 2>&1
        if [ "$?" == "0" ]; then
            obsidian "$file"
        else
            $EDITOR "$file"
        fi
    else
	    cat "$file"
    fi
}


#!/bin/sh

todo() {
    if [ "$1" = "e" ]; then
        $EDITOR ~/todo
    else
	cat ~/todo
    fi
}


#!/bin/sh

b() (
    if [ "$(basename "$(pwd)")" != "build" ]; then
        mkdir -p build
        cd build || return
    fi
    cmake .. "$@"
)

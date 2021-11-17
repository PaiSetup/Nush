#!/bin/sh

b() (
    mkdir -p build
    cd build || return
    cmake .. "$@"
)

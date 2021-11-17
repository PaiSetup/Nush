#!/bin/sh

t() (
    cd build || return
    cmake --build . --config Debug && ctest -C Debug --verbose
)

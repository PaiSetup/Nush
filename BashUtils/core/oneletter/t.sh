#!/bin/sh

t() (
    cd build || return
    if [ "$IS_LINUX" = 0 ]; then
        extraArgs="-- -j$(nproc)"
    fi

    cmake --build . --config Debug $extraArgs && ctest -C Debug --verbose
)

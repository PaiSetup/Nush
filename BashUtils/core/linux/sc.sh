#!/bin/sh

sc() (
    shellcheck --exclude=SC2155,SC1090,SC2044 "$@" 
)

scc() (
    find $SCRIPTS_PATH $LINUX_SETUP_ROOT -type f                                              \
        \( -name "*.sh" -o -name "*.bash" \)                                                  \
        -not -path "$LINUX_SETUP_ROOT/build/*" -not -path "$SCRIPTS_PATH/load_functions.bash" \
        |  xargs -l1 shellcheck -e 2086,2181,2038,2009,2068,2046,2155,2044,1090,2059,2015
)

#!/bin/sh

if [ $IS_LINUX != 0 ] ; then
    return
fi

sc() (
    shellcheck --exclude=SC2155,SC1090,SC2044 "$@" 
)

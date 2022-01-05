#!/bin/sh

if [ -z "$NPP_PATH" ]; then
    return
fi

npp() (
    "$NPP_PATH" -multiInst -notabbar -nosession -noPlugin "$@"
)

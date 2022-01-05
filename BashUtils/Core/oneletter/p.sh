#!/bin/sh

if [ "$IS_LINUX" = 0 ]; then
    alias p="ps aux --forest"
else
    alias p="ps -W"
fi

alias pp="p | less"

#!/bin/sh

npp() (
    NPP_PATH="$(powershell -Command "(Get-ItemProperty -Path 'HKLM:\SOFTWARE\Classes\CLSID\{B298D29A-A6ED-11DE-BA8C-A68E55D89593}\Settings' -Name 'Path').Path" 2>/dev/null)"
    if [ -z "$NPP_PATH" ]; then
        echo "ERROR: Could not find installed Notepad++." >&2
        return 1
    fi

    "$NPP_PATH" -multiInst -notabbar -nosession -noPlugin "$@"
)

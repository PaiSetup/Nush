#!/bin/sh

convert_to_windows_path() (
   echo "$1" | sed 's/^\/\([a-z]\)\/\(.*\)/\1:\/\2/' | sed 's/\//\\/g'
)

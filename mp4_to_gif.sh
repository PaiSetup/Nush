#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <input.mp4>"
    exit 1
fi

if [ ! -f "$1" ]; then
    echo "Error: file '$1' not found"
    exit 1
fi

palette=$(mktemp /tmp/palette_XXXXXX.png)
trap "rm -f '$palette'" EXIT

ffmpeg -y -i "$1" -vf "palettegen=max_colors=256:stats_mode=full" "$palette" && \
ffmpeg -i "$1" -i "$palette" -lavfi "paletteuse=dither=sierra2_4a" "${1%.mp4}.gif"

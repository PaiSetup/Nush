#!/bin/sh

if [ -z "$VERACRYPT_PATH" ]; then
    return
fi

volume_path="f:\Nice"
drive_letter="X"
toggle_veracrypt_mount $volume_path $drive_letter

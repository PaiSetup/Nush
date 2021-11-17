#!/bin/sh

diffs() (
    git diff --stat "$@"
)

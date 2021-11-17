#!/bin/sh

diffn() (
    git diff --name-only "$@"
)

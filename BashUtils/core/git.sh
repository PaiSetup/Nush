#!/bin/sh

log() (
    git log --graph --pretty="format:%C(auto,yellow)%H %C(auto,green)%<(20,trunc)%aN %C(auto,cyan)%<(15,trunc)%cr %C(auto,reset)%s %C(auto)%d" "$@"
)

poi() (
    echo "> log -10"
    log -10

    echo
    echo "> git branch"
    git branch

    echo
    echo "> git status"
    git status
)

amend() (
    git status
    git commit -a --amend
)

diffc() (
    git diff --cached "$@"
)

alias status="git status"

#!/bin/sh

amend() (
    git status
    git commit -a --amend
)

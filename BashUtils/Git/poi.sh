#!/bin/sh

poi() (
    echo "> logs"
    logs
    
    echo
    echo "> git branch"
    git branch
    
    echo
    echo "> git status"
    git status
)

#!/bin/sh

run_ssh_cmd() (
    ip=$1
    cmd=$2

    # shellcheck disable=SC2029
    ssh gta@$ip "$cmd"
)


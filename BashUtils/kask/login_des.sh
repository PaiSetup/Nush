#!/bin/sh

login_des() (
    des_tunnel "$@"
    local_port=2222
    ssh_key=~/.ssh/dziuban
    ssh -p "$local_port" s165335@localhost -i "$ssh_key"
)

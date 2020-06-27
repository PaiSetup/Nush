des_socket_name=$HOME/.ssh/socket_des

function des_tunnel() (
    # Get index
    if ! [[ $1 =~ ^[0-9]+$ ]]; then
        echo "ERROR: Specify valid des index, e.g"
        echo "    login_des.sh 5"
        return 1
    fi
    index=`printf "%02d" $1`

    # Prepare params
    ssh_key=~/.ssh/dziuban
    local_port=2222
    remote_ip=des$index.kask
    remote_port=22

    # Close previous tunnel if present
    des_tunnel_close

    # Create the tunnel
    echo "Creating tunnel to Tunnel to $remote_ip via localhost:$local_port..."
    ssh -fNM -S $des_socket_name -L $local_port:$remote_ip:$remote_port kask.eti.pg.gda.pl
    if [ $? != 0 ]; then
        echo "Error creating tunnel"
        return 1
    fi
)

function des_tunnel_close() (
    if [ ! -e $des_socket_name ]; then
        echo "No socket had to be closed"
        return
    fi

    ssh -S $des_socket_name -O exit kask.eti.pg.gda.pl >/dev/null 2>&1
    if [ $? != 0 ]; then
        rm $des_socket_name
        if [ $? != 0 ]; then
            echo "Socket file exists, but could not be closed or removed"
            return
        fi
        echo "Socket file exists but could not close it. Removing."
    fi

    echo "Socket closed successfully"
)

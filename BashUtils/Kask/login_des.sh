function login_des() (
    if ! [[ $1 =~ ^[0-9]+$ ]]; then
        echo "ERROR: Specify valid des index, e.g"
        echo "    login_des.sh 5"
        exit 1
    fi
    index=`printf "%02d" $1`

    ssh_key="~/.ssh/dziuban"
    dummy_port="2222"
    ssh -fN -L $dummy_port:des$index.kask:22 kask.eti.pg.gda.pl
    ssh -p $dummy_port s165335@localhost -i $ssh_key
)

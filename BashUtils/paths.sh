export SCRIPTS_PATH=`realpath "$BASH_SOURCE" | xargs dirname`
export NPP_PATH="E:\Programs\Notepad++\notepad++.exe"
export VERACRYPT_PATH="E:\Programs\VeraCrypt\VeraCrypt-x64.exe"

if [ "$1" == "debug" ]; then
    function print_path() (
        printf '%-15s %s\n' "$1" "${!1}"
    )
    echo "-------------------- paths.sh"
    print_path SCRIPTS_PATH
    print_path NPP_PATH
    print_path VERACRYPT_PATH
    echo "-------------------- paths.sh"
fi

export SCRIPTS_PATH=`realpath "$BASH_SOURCE" | xargs dirname`
export NPP_PATH="E:\Programs\Notepad++\notepad++.exe"
export VERACRYPT_PATH="E:\Programs\VeraCrypt\VeraCrypt-x64.exe"
export ICON_SETTER_PATH="/d/Projects/IconSetter/build/Debug/IconSetter.exe"

if [ "$1" == "debug" ]; then
    function print_path() (
        if [ -e "${!1}" ]; then
            msg=
        else
            msg="NOT FOUND!!!"
        fi
        printf '%-15s %s %s\n' "$1" "${!1}" "$msg"
    )
    echo "-------------------- paths.sh"
    print_path SCRIPTS_PATH
    print_path NPP_PATH
    print_path VERACRYPT_PATH
    print_path ICON_SETTER_PATH
    echo "-------------------- paths.sh"
fi

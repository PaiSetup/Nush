export SCRIPTS_PATH=`realpath "$BASH_SOURCE" | xargs dirname`
export NPP_PATH="/e/Programs/Notepad++/notepad++.exe"
export VERACRYPT_PATH="/e/Programs/VeraCrypt/VeraCrypt-x64.exe"
export ICONFIGURE_PATH="/e/Programs/Iconfigure/Iconfigure.exe"

if [ "$1" == "debug" ]; then
    function print_path() (
        if [ -e "${!1}" ]; then
            msg="FOUND"
        else
            msg="NOT FOUND"
        fi
        printf '%-16s %-40s %s\n' "$1" "${!1}" "$msg"
    )
    echo "-------------------- paths.sh"
    print_path SCRIPTS_PATH
    print_path NPP_PATH
    print_path VERACRYPT_PATH
    print_path ICON_SETTER_PATH
    echo "-------------------- paths.sh"
fi

function npp() (
    if [ -z "$NPP_PATH" ]; then
        echo "ERROR: Variable NPP_PATH not set"
        return 1;
    fi
    if [ ! -f "$NPP_PATH" ]; then
        echo "ERROR: Variable NPP_PATH is set but points to not existing file"
        return 1;
    fi
 
    "$NPP_PATH" -multiInst -notabbar -nosession -noPlugin $@
)
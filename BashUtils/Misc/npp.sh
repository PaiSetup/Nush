if [ -z "$NPP_PATH" ]; then
    return
fi

function npp() (
    "$NPP_PATH" -multiInst -notabbar -nosession -noPlugin $@
)

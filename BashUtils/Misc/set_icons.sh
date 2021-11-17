#!/bin/sh

if [ -z "$ICONFIGURE_PATH" ]; then
    return
fi

set_icons() (
    $ICONFIGURE_PATH -l D:\\Pictures\\Icons -d D: -d D:\\Pictures -d D:\\Video -d E:
    $ICONFIGURE_PATH -r -d E:\\Programs
)
#!/bin/bash

SCRIPT_DIR="/home/tkalmijn"
PID_FILE="/var/run/hue-dmx.pid"

start() {
    cd "$SCRIPT_DIR" || exit
    python3 "$SCRIPT_DIR/hue-dmx.py"
}

stop() {
    if [ -f $PID_FILE ]; then
        echo "Stopping Hue-DMX with PID $(cat $PID_FILE)..."
    else
        echo "No PID file found at $PID_FILE."
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    *)
        echo "Usage: $0 {start|stop}"
        exit 1
esac

exit 0

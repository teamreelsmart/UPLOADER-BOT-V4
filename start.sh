#!/usr/bin/env sh
# Start the health-check web server on the port assigned by the host, while the
# Telegram bot remains the primary process.
set -eu

: "${PORT:=10000}"

gunicorn --bind "0.0.0.0:${PORT}" app:app &
web_pid=$!

cleanup() {
    kill -TERM "$web_pid" 2>/dev/null || true
}

trap 'cleanup; exit 0' INT TERM

python3 bot.py &
bot_pid=$!

if wait "$bot_pid"; then
    bot_status=0
else
    bot_status=$?
fi
cleanup
wait "$web_pid" 2>/dev/null || true
exit "$bot_status"

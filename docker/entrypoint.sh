#!/bin/bash
set -eo pipefail  # stronger error handling than just 'set -e'

# NOTE: ROOT_PATH needs to be defined before supervisord can pass it to
#   our app (if necessary)
export ROOT_PATH="$ROOT_PATH"

# start services and record the PID
supervisord -c /etc/supervisor/supervisord.conf &
supervisord_pid=$!

# trap SIGTERM and forward to supervisord
_term() {
  echo "Caught SIGTERM! Gracefully shutting down..."
  supervisorctl stop all
  kill -TERM $supervisord_pid 2>/dev/null
  wait $supervisord_pid
  exit 0
}
trap _term TERM

echo "Waiting for services to start..."
sleep 3  # initial delay to allow services to start

# monitor process health
while sleep 3
do
    if ! supervisorctl status fastapi | grep -q RUNNING
    then
        echo "fastapi process crashed"
        break
    fi

    if ! supervisorctl status huey | grep -q RUNNING
    then
        echo "huey process crashed"
        break
    fi

    if ! supervisorctl status nginx | grep -q RUNNING
    then
        echo "nginx process crashed"
        break
    fi
done

# cleanup if loop exits unexpectedly
kill -15 $supervisord_pid
wait $supervisord_pid
exit $?

#!/bin/bash
set -e

awsm='python3 /code/awsm/scripts/awsm'

if [ $# -eq 0 ]; then
    echo "Run AWSM docker test"
    umask 0002
    exec $awsm /code/awsm/tests/RME/config.ini

elif [ "$1" = "test" ]; then
    echo "Run AWSM docker test"
    cd /code/awsm
    coverage run --source awsm setup.py test
    coverage report --fail-under=40
    coveralls
    exit 0

elif [[ "$1" == *.ini ]]; then
    echo "Run AWSM with config file"
    umask 0002
    echo "$1"
    exec $awsm "$1"

else
    echo "$@"
    umask 0002
    exec "$@"
fi

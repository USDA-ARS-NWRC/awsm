#!/bin/bash
set -e

awsm='python3 /code/awsm/scripts/awsm'

if [ $# -eq 0 ]; then
    echo "Run AWSM docker test"
    exec $awsm /code/awsm/test_data/RME_run/docker_pysnobal.ini

elif [ ! -x "$1" ]; then
    echo "Run AWSM with config file"
    exec $awsm "$1"

else
    exec "$1"
fi

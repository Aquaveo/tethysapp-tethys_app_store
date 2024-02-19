#!/bin/bash

echo "Running Mamba Download"
if hash micromamba; then
    MAMBA_COMMAND=micromamba
else
    MAMBA_COMMAND=mamba
fi

$MAMBA_COMMAND install -y --freeze-installed -q -c $2 -c tethysplatform -c conda-forge --no-deps $1 --json

echo "Mamba Download Complete"

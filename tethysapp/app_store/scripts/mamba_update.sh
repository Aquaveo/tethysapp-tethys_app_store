#!/bin/bash

echo "Running Mamba Update"
if hash micromamba; then
    MAMBA_COMMAND=micromamba
else
    MAMBA_COMMAND=mamba
fi

$MAMBA_COMMAND install -y  -q -c $2 -c tethysplatform -c conda-forge $1
echo "Mamba Update Complete"
#!/bin/bash

echo "Running Mamba Install"
if hash micromamba; then
    MAMBA_COMMAND=micromamba
else
    MAMBA_COMMAND=mamba
fi

if $MAMBA_COMMAND install -y --freeze-installed -q -c $2 -c tethysplatform -c conda-forge $1; then
    echo "Mamba Install Success"
else
    echo "Mamba failed. Trying conda now."
    conda install -y --freeze-installed -q -c $2 -c tethysplatform -c conda-forge $1 || echo "Conda Install Success"
fi

echo "Install Complete"

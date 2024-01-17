#!/bin/bash

echo "Running Mamba Install"
if micromamba; then
    MAMBA_COMMAND=micromamba
else
    MAMBA_COMMAND=mamba

$MAMBA_COMMAND install -y --freeze-installed -q -c $2 -c tethysplatform -c conda-forge $1

echo "Mamba Install Complete"

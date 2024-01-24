#!/bin/bash

echo "Running Mamba remove"
if hash micromamba; then
    MAMBA_COMMAND=micromamba
else
    MAMBA_COMMAND=mamba
fi

$MAMBA_COMMAND remove -y --force $1
echo "Mamba Remove Complete"
#!/bin/bash

echo "Running Mamba remove"
if micromamba; then
    MAMBA_COMMAND=micromamba
else
    MAMBA_COMMAND=mamba

$MAMBA_COMMAND remove -y --force $1
echo "Mamba Remove Complete"

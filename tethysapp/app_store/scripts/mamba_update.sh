#!/bin/bash

echo "Running Mamba Update"
micromamba install -y  -q -c $2 -c tethysplatform -c conda-forge $1
echo "Mamba Update Complete"
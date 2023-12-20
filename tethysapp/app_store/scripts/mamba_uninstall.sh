#!/bin/bash

echo "Running Mamba remove"
micromamba remove -y --force $1
echo "Mamba Remove Complete"

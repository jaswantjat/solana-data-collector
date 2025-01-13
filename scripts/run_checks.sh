#!/bin/bash

# Add project root to PYTHONPATH
export PYTHONPATH="/Users/masterjaswant/CascadeProjects/solana_data_collector:$PYTHONPATH"

# Run database checks
python3 scripts/check_database.py

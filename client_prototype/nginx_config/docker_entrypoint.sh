#!/bin/bash

# Collect static files
echo "Starting nginx service"
service nginx start

# Apply database migrations
echo "Running Pastel node"

# the following line runs single master node - intended for production usage
PYTHONPATH="/opt/python_layer" python /opt/python_layer/start_single_masternode.py /opt/python_layer/config_sample/0 127.0.0.1

# the following line runs simulator - it can be several nodes.
#PYTHONPATH="/opt/python_layer" python /opt/python_layer/start_simulator.py /opt/python_layer/config_sample
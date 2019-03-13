#!/bin/bash

# Collect static files
echo "Starting nginx service"
service nginx start

# Apply database migrations
echo "Running Pastel node"
PYTHONPATH="/opt/python_layer" python /opt/python_layer/start_simulator.py /opt/python_layer/config_sample
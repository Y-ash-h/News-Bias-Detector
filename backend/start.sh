#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Start the Flask server
echo "Starting Flask backend server on http://localhost:5000"
python main.py

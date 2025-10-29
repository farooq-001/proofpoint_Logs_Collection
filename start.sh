#!/bin/bash

while true; do
    python3 proofpoint_stream.py
    echo "finished"
    
    # Check if the last echo printed "finished"
    # This condition is trivially true but aligns with your request
    if [ $? -eq 0 ]; then
        echo "Restarting because finished was printed"
        # optionally add a delay here if needed
        sleep 1
    else
        echo "Exiting because finished was not printed"
        break
    fi
done

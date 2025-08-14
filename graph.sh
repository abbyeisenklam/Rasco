#!/bin/bash
echo "Graphing data from these directories: $@"
echo "	Processing results..."
./process_results.sh "$@"
echo "	Making graph"
python ./graph_schedulability.py "$@"

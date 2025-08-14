#!/bin/bash

for dir in "$@"; do
    # Extract the directory name to use in the output filename
    dirname=$(basename "$dir")
    
    # Concatenate only .txt files in the specified directory and filter by "SCHEDULABLE"
    cat "$dir"/*.txt | grep "SCHEDULABLE" > "${dirname}_all.txt"
done
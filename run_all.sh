#!/bin/bash
# inputs:
#   taskset path
#   num tasksets per util step
#   min taskset util (equal to util step)
#   max taskset util
#   num threads for parallel execution
#   algo type?: 0 - baseline-test, 1 - Rasco, 2 - baseline-sim
python main.py tasksets_m4 100 0.2 5.0 60 0
python main.py tasksets_m4 100 0.2 5.0 60 1
python main.py tasksets_m4 100 0.2 5.0 60 2
./graph.sh RASCO baseline-sim baseline-test
# Rasco: Resource Allocation and Scheduling Co-design for DAG Applications on Multicore

This is the Python implementation of the Rasco algorithm as presented in A. Eisenklam, R. Gifford, G. A. Bondar, Y. Cai, T. Sial, L. T. X. Phan, A. Halder. Rasco: Resource Allocation and Scheduling Co-design for DAG Applications on Multicore. In EMSOFT, 2025. The repo contains example tasksets and task profiles to produce a schedulability plot similar to Fig. 9.

### Input
- `/profiles` contains a `phases.txt`, `wcet.txt`, and `theta.txt` for each task under each possible resource budget (if `theta.txt` does not exist, it will be generated automatically from the phase files)
- `/tasksets_m4` contains 100 randomly generated DAG tasksets at each utilization step (0.2 - 5.0 in steps of 0.2) for `m=4` cores

### How to run
- `cd c_src`
- `make`
- `cd ..`
- `./run_all.sh` runs the Rasco algorithm on all of the available tasksets and compares to baseline-test (DAG schedulability test from X. Jiang, N. Guan, X. Long, and H. Wan. Decomposition-based real-time scheduling of parallel tasks on multicores platforms. 2020.) and baseline-sim (simulated static schedule for even partitions under G-EDF)
- `./run_rasco.sh` runs Rasco only
- These run scripts set the number of threads for parallel execution equal to 60, which you may want to change based on the number of available cores on your machine.

### Output
- `/RASCO` contains the schedules produces by the Rasco algorithm for each taskset. Each .txt file lists all jobs releases first in the header and then lists the schedule segments, where each segment has the format (time_ns, 'job1.uid', cache, bw, 'job2.uid', cache, bw, 'job3.uid', cache, bw, 'job4.uid', cache, bw)
- If you run `run_all.sh`, the baseline comparisons will be output to `/baseline-sim` and `/baseline-test`. Then check the file `schedulability_plot.pdf` for the results.
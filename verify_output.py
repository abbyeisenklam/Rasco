"""
Verifies that all job releases in the output files appear in their respective static schedules.
Also tracks:
1. Percentage of files where SCHEDULABLE is True
2. Missing files in the input directory (checking for utils 0.2-4.8 in increments of 0.2)
3. Runtime as a function of utilization

Usage:
    python verify_output_directory.py <directory_path> <num_tasksets_per_util>

The program processes all files in the specified directory, extracting job releases,
static schedules, and runtime from each file. It reports missing files, files with missing jobs,
or files marked as unschedulable. Utilization values are fixed from 0.2 to 4.8 in increments of 0.2.
"""

import sys
import os
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np


def parse_input_file(file_path):
    """Parse the input file to extract job releases, static schedule, and runtime."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Check for SCHEDULABLE status
    schedulable_match = re.search(r'SCHEDULABLE:\s*(True|False)', content)
    schedulable = schedulable_match.group(1) == "True" if schedulable_match else None
    
    # Extract runtime information
    runtime_match = re.search(r'RUNTIME:\s*(\d+\.?\d*)', content)
    runtime = float(runtime_match.group(1)) if runtime_match else None
    
    # Extract job releases section
    # Find where the job releases end (just before STARTING SCHEDULE)
    schedule_start_idx = content.find("STARTING SCHEDULE")
    if schedule_start_idx == -1:
        raise ValueError("Could not find 'STARTING SCHEDULE' in input file")
    
    # Extract job releases (everything from start to the schedule section)
    job_releases_text = content[:schedule_start_idx]
    
    # Extract static schedule section
    schedule_text = content[schedule_start_idx:]
    
    # if not schedule_text:
    #     raise ValueError("Could not extract schedule section from input file")
    
    return job_releases_text, schedule_text, schedulable, runtime


def extract_job_releases(job_releases_text):
    """Extract all job releases from the job releases text."""
    # Pattern to match job lines
    job_pattern = r'Job\(uid=([^,]+)'
    
    # Find all job UIDs
    job_uids = re.findall(job_pattern, job_releases_text)
    
    # if not job_uids:
    #     print("WARNING: No job UIDs found in job releases text.")
    #     print("First 200 characters of job releases text:")
    #     print(job_releases_text[:200])
    
    return set(job_uids)


def extract_scheduled_jobs(schedule_text):
    """Extract all jobs that appear in the static schedule."""
    # Skip the explanation line that contains the format description
    format_line_idx = schedule_text.find("format:")
    if format_line_idx > 0:
        # Find the end of this line
        newline_idx = schedule_text.find("\n", format_line_idx)
        if newline_idx > 0:
            # Skip this line in our parsing
            schedule_text = schedule_text[newline_idx+1:]
    
    # Pattern to match schedule lines with job UIDs
    schedule_line_pattern = r'\([^)]*\)'
    
    # Find all schedule lines
    schedule_lines = re.findall(schedule_line_pattern, schedule_text)
    
    scheduled_jobs = set()
    
    for line in schedule_lines:
        # Each schedule line format: (t, 'job_id1', c1, bw1, 'job_id2', c2, bw2, ...)
        # Split the line by commas and remove parentheses
        parts = line.strip('()').split(', ')
        
        # Skip the first item (timestamp)
        parts = parts[1:]
        
        # Extract job UIDs (every 3rd item starting from index 0)
        for i in range(0, len(parts), 3):
            if i < len(parts) and parts[i].startswith("'") and parts[i].endswith("'"):
                job_uid = parts[i].strip("'")
                if job_uid != "None":
                    scheduled_jobs.add(job_uid)
    
    return scheduled_jobs


def analyze_job_coverage(job_releases, scheduled_jobs):
    """Analyze which jobs are covered in the schedule and which are missing."""
    # Jobs that appear in the schedule
    covered_jobs = job_releases.intersection(scheduled_jobs)
    
    # Jobs that are missing from the schedule
    missing_jobs = job_releases.difference(scheduled_jobs)
    
    # Jobs in schedule but not in releases (unexpected)
    unexpected_jobs = scheduled_jobs.difference(job_releases)
    
    return covered_jobs, missing_jobs, unexpected_jobs


def group_jobs_by_prefix(job_set):
    """Group jobs by their prefix (before the underscore)."""
    grouped = defaultdict(list)
    for job in job_set:
        if '_' in job:
            prefix = job.split('_')[0]
            grouped[prefix].append(job)
        else:
            grouped['unknown'].append(job)
    
    # Sort each group
    for prefix in grouped:
        grouped[prefix].sort()
    
    return grouped


def process_file(file_path):
    """Process a single file and check for missing jobs and schedulability."""
    try:
        # Parse the input file
        job_releases_text, schedule_text, schedulable, runtime = parse_input_file(file_path)
        
        # Extract job releases and scheduled jobs
        job_releases = extract_job_releases(job_releases_text)
        scheduled_jobs = extract_scheduled_jobs(schedule_text)
        
        # Check if we successfully extracted jobs
        if not job_releases:
            print(f"ERROR in {file_path}: Failed to extract any job releases.")
            return False, None
            
        if not scheduled_jobs:
            print(f"ERROR in {file_path}: Failed to extract any scheduled jobs.")
            return False, None
        
        # Analyze job coverage
        covered_jobs, missing_jobs, unexpected_jobs = analyze_job_coverage(job_releases, scheduled_jobs)
        
        # Extract util and index from filename
        filename = os.path.basename(file_path)
        match = re.search(r'out_(\d+\.?\d*)_(\d+)\.txt', filename)
        util = float(match.group(1)) if match else None
        index = int(match.group(2)) if match else None
        
        # Return success status and missing jobs information
        return True, {
            'file_path': file_path,
            'filename': filename,
            'util': util,
            'index': index,
            'total_jobs': len(job_releases),
            'scheduled_jobs': len(scheduled_jobs),
            'covered_jobs': len(covered_jobs),
            'coverage_percent': (len(covered_jobs) / len(job_releases) * 100),
            'missing_jobs': missing_jobs,
            'unexpected_jobs': unexpected_jobs,
            'schedulable': schedulable,
            'runtime': runtime
        }
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, None


def main(directory_path, max_util, num_tasksets_per_util):
    try:
        # Check if the directory exists
        if not os.path.isdir(directory_path):
            print(f"Error: {directory_path} is not a directory")
            return 2
        
        # Get all files in the directory
        files = [os.path.join(directory_path, f) for f in os.listdir(directory_path) 
                if os.path.isfile(os.path.join(directory_path, f)) and f.startswith('out_')]
        
        if not files:
            print(f"No output files found in {directory_path}")
            return 0
        
        print(f"Found {len(files)} output files in {directory_path}")
        
        # Process each file and collect results
        any_missing_jobs = False
        files_with_missing_jobs = []
        files_with_errors = []
        processed_count = 0
        
        # Track schedulability statistics
        schedulable_files = []
        unschedulable_files = []
        unknown_schedulable_status = []
        
        # For runtime plotting
        util_runtime_data = defaultdict(list)
        
        # Process each file
        processed_results = []
        for file_path in files:
            print(f"Processing {file_path}...", end='')
            success, result = process_file(file_path)
            
            if not success:
                files_with_errors.append(file_path)
                print(" ERROR")
                continue
            
            processed_count += 1
            processed_results.append(result)
            
            # Track schedulability
            if result['schedulable'] is not None:
                if result['schedulable']:
                    schedulable_files.append(file_path)
                else:
                    unschedulable_files.append(file_path)
            else:
                unknown_schedulable_status.append(file_path)
            
            # Track runtime data
            if result['util'] is not None and result['runtime'] is not None:
                util_runtime_data[result['util']].append(result['runtime'])
            
            if result['missing_jobs']:
                any_missing_jobs = True
                files_with_missing_jobs.append(result)
                print(f" MISSING JOBS: {len(result['missing_jobs'])}")
            else:
                print(" OK")
        
        # Check for missing files based on utils from 0.2 to 4.8 in increments of 0.2
        missing_files = []
        for util in np.arange(0.2, max_util, 0.2):  # 0.2 to 4.8 in steps of 0.2
            for index in range(num_tasksets_per_util):
                expected_filename = f"out_{util:.1f}_{index}.txt"
                expected_filepath = os.path.join(directory_path, expected_filename)
                
                # Check if this file exists in our processed results
                if not any(result['filename'] == expected_filename for result in processed_results if result['filename'] is not None):
                    missing_files.append(expected_filename)
                    #Remove the file from 'outut' directory if it doesn't exist in processed results
                    if directory_path == "RASCO":
                        output_filepath = os.path.join('baseline-sim', expected_filename)
                        if os.path.exists(output_filepath):
                            os.remove(output_filepath)
                        output_filepath = os.path.join('baseline-test', expected_filename)
                        if os.path.exists(output_filepath):
                            os.remove(output_filepath)
                    elif directory_path == "baseline-sim":
                        output_filepath = os.path.join('RASCO', expected_filename)
                        if os.path.exists(output_filepath):
                            os.remove(output_filepath)
                        output_filepath = os.path.join('baseline-test', expected_filename)
                        if os.path.exists(output_filepath):
                            os.remove(output_filepath)
        
        # Print summary
        print("\n===== SUMMARY =====")
        print(f"Processed {processed_count} files out of {len(files)} total")
        print(f"Files with errors: {len(files_with_errors)}")
        
        # Print missing files information
        if missing_files:
            print(f"\nMISSING FILES ({len(missing_files)}):")
            for filename in sorted(missing_files):
                print(f"  {filename}")
        else:
            print("\nAll expected files are present!")
        
        # Print schedulability statistics
        if processed_count > 0:
            schedulable_percent = (len(schedulable_files) / processed_count * 100) if processed_count > 0 else 0
            print(f"\nSCHEDULABILITY STATISTICS:")
            print(f"  Schedulable files: {len(schedulable_files)} ({schedulable_percent:.2f}%)")
            print(f"  Unschedulable files: {len(unschedulable_files)}")
            print(f"  Unknown schedulable status: {len(unknown_schedulable_status)}")
        
        if any_missing_jobs:
            print(f"\nFOUND {len(files_with_missing_jobs)} FILES WITH MISSING JOBS:")
            
            for result in files_with_missing_jobs:
                print(f"\nFile: {result['file_path']}")
                print(f"  Total jobs: {result['total_jobs']}")
                print(f"  Jobs covered: {result['covered_jobs']} ({result['coverage_percent']:.2f}%)")
                
                print(f"  Missing jobs ({len(result['missing_jobs'])}):")
                grouped_missing = group_jobs_by_prefix(result['missing_jobs'])
                for prefix, jobs in sorted(grouped_missing.items()):
                    print(f"    {prefix}: {', '.join(jobs)}")
                
                if result['unexpected_jobs']:
                    print(f"  Unexpected jobs ({len(result['unexpected_jobs'])}):")
                    grouped_unexpected = group_jobs_by_prefix(result['unexpected_jobs'])
                    for prefix, jobs in sorted(grouped_unexpected.items()):
                        print(f"    {prefix}: {', '.join(jobs)}")
        else:
            print("\nALL FILES HAVE COMPLETE SCHEDULES! No missing jobs found.")
        
        if files_with_errors:
            print("\nFiles that couldn't be processed:")
            for file_path in files_with_errors:
                print(f"  {file_path}")
        
        # Plot median runtime as a function of utilization
        if util_runtime_data:
            plt.figure(figsize=(8, 5))
            
            # Sort utils for plotting
            utils = sorted(util_runtime_data.keys())
            
            # Extract median runtimes for each utilization
            median_runtimes = [np.median(util_runtime_data[u]) for u in utils]
            
            # Create line plot with markers for median runtimes
            plt.plot(utils, median_runtimes, 'o-', color='red', linewidth=2, markersize=8)
            
            # Increase font size for axis labels
            plt.xlabel('Utilization', fontsize=22)
            plt.ylabel('Median Runtime (seconds)', fontsize=22)
            #plt.title('Median Runtime vs. Utilization (Log Scale)', fontsize=16)
            plt.xticks(fontsize=12)
            plt.yticks(fontsize=12)
            #plt.yscale('log')
            plt.grid(True)
            
            # Add some padding to x-axis
            plt.xlim(min(utils) - 0.05, max(utils) + 0.05)
            
            # Save the plot
            plot_path = os.path.join(directory_path, f'{directory_path}_median_runtime_vs_util.png')
            plt.savefig(plot_path)
            print(f"\nMedian Runtime vs Utilization plot saved as: {plot_path}")
        
        # Return an exit code
        return 1 if any_missing_jobs or missing_files else 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <directory_path> <max_util> <num_tasksets_per_util>")
        print(f"Note: Utilization values are fixed from 0.2 to max_util in increments of 0.2")
        sys.exit(1)
    
    directory_path = sys.argv[1]
    max_util = float(sys.argv[2])
    num_tasksets_per_util = int(sys.argv[3])
    
    sys.exit(main(directory_path, max_util, num_tasksets_per_util))
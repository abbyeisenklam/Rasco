import re
import sys
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

# Define the regex pattern for parsing
pattern = re.compile(r'TASKSET IDX: \d+, UTIL: ([\d\.]+), SCHEDULABLE: (True|False)')

# Initialize a dictionary to store data from all files
all_util_schedulable_counts = {}

# Loop through each directory name provided as a command-line argument
for dir_name in sys.argv[1:]:
    # Construct the full filename by appending "_all.txt"
    filename = f"{dir_name}_all.txt"
    
    # Initialize a dictionary for each file
    util_schedulable_counts = defaultdict(lambda: [0, 0])
    
    # Add the extra data point at 0.0 utilization with y = 100
    util_schedulable_counts[0] = [1, 1]  # 100% schedulable for this utilization

    # Read the data from the file
    with open(filename, "r") as file:
        data = file.readlines()
    
    # Parse the data for the current file
    for line in data:
        match = pattern.match(line)
        if match:
            util = float(match.group(1))
            schedulable = match.group(2) == 'True'
            util_schedulable_counts[util][1] += 1  # Increment total count for the utilization level
            if schedulable:
                util_schedulable_counts[util][0] += 1  # Increment schedulable count for the utilization level

    # Store the parsed data by the directory name
    all_util_schedulable_counts[dir_name] = util_schedulable_counts

# Predefined line styles and markers for diversity
line_styles = ['-', '--', '-.', ':']
markers = ['o', 's', 'D', '^', 'v', 'p', '*', 'x', '+', 'h']

# Create the figure with improved visual style
plt.figure(figsize=(10, 6))

# Set up the axes with enhanced styling
ax = plt.gca()

# Configure the appearance of the plot
# Set thickness of the spines
for spine in ax.spines.values():
    spine.set_linewidth(1.5)

for idx, (label, util_schedulable_counts) in enumerate(all_util_schedulable_counts.items()):
    # Prepare data for plotting - use all available data without filtering
    utils = sorted(util_schedulable_counts.keys())
    schedulability_percentages = []
    
    for util in utils:
        schedulable_count, total_count = util_schedulable_counts[util]
        schedulability_percentage = (schedulable_count / total_count) * 100 if total_count > 0 else 0
        schedulability_percentages.append(schedulability_percentage)
    
    # Select unique line style and marker for each dataset
    color = None
    linestyle = line_styles[idx % len(line_styles)]
    marker = markers[idx % len(markers)]
    
    # Plot each file's data with a unique label
    plt.plot(utils, schedulability_percentages, marker=marker, linestyle=linestyle, 
             label=label, linewidth=3, color=color, markersize=8)

# Configure axis labels with larger, bold font
plt.xlabel("Taskset Utilization", fontsize=26, fontweight='bold', labelpad=10)
plt.ylabel("% Tasksets Schedulable", fontsize=26, fontweight='bold', labelpad=10)

# Configure legend with larger font
plt.legend(loc='best', fontsize=24, framealpha=0.9)

# Set up grid with both major and minor gridlines
plt.grid(True, which='major', linestyle='-', linewidth=0.8, alpha=0.7)

# Set y-axis limit slightly above 100
plt.ylim(0, 105)

# Calculate the max utilization for tick placement
max_util = max(max(util_schedulable_counts.keys()) for util_schedulable_counts in all_util_schedulable_counts.values())
max_util = np.ceil(max_util * 10) / 10  # Round up to nearest 0.1

# Set up minor ticks every 0.1 step
ax.xaxis.set_minor_locator(plt.MultipleLocator(0.1))
ax.yaxis.set_minor_locator(plt.MultipleLocator(5))

# Set up major x-ticks every 1.0 with bold labels
# Create tick positions (unchanged)
# Create a label for each position, but make the first one empty
tick_positions = np.arange(0, max_util + 0.5, 1.0)
tick_labels = [""] + [f"{x:.1f}" for x in np.arange(1.00, max_util + 0.5, 1.0)]

# Make sure the number of labels matches the number of positions
if len(tick_labels) < len(tick_positions):
    # Add empty strings if we have fewer labels than positions
    tick_labels.extend([""] * (len(tick_positions) - len(tick_labels)))
elif len(tick_labels) > len(tick_positions):
    # Trim extra labels if we have more labels than positions
    tick_labels = tick_labels[:len(tick_positions)]

# Apply the ticks and custom labels
plt.xticks(tick_positions, tick_labels, fontsize=22, fontweight='bold')

# Set up y-ticks with bold labels
plt.yticks(np.arange(0, 110, 10), fontsize=22, fontweight='bold')

# Ensure x-axis starts at 0.0 and extends slightly past the max util
plt.xlim(0, max_util + 0.1)

# Apply tight layout for better spacing
plt.tight_layout()

# Save the plot to both PDF and PNG formats
output_pdf = "schedulability_plot.pdf"
plt.savefig(output_pdf, format='pdf', bbox_inches='tight')

print(f"Plots saved as {output_pdf}")
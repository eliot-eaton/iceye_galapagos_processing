
#!/bin/bash
set -euo pipefail

# Usage: ./slc_to_tif.sh input.slc

slc="$1"
par="${slc}.par"
output_tif="${slc}.tif"

# Check input files
if [ ! -f "$slc" ]; then
    echo "ERROR: SLC file not found: $slc"
    exit 1
fi

if [ ! -f "$par" ]; then
    echo "ERROR: Parameter file not found: $par"
    exit 1
fi

# Read range samples
range_samples=$(awk '$1 == "range_samples:" {print $2; exit}' "$par")

if [ -z "$range_samples" ]; then
    echo "ERROR: Could not read range_samples from $par"
    exit 1
fi

# Convert SLC to TIFF using Gamma
rasSLC "$slc" "$range_samples" - - 20 20 - - "$output_tif" 1

echo "Created: $output_tif"

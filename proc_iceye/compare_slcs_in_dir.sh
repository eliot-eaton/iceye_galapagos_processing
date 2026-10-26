#!/bin/bash

for f in *X47*.slc.par *X49*.slc.par; do
    [ -f "$f" ] || continue
    echo "========== $f =========="
    grep -Ei \
    'range_samples:|azimuth_lines:|near_range_slc:|range_pixel_spacing:|azimuth_pixel_spacing:|start_time:|center_time:|heading:|incidence_angle:|azimuth_deskew:|radar_frequency:|sensor:|earth_radius' \
    "$f"
done
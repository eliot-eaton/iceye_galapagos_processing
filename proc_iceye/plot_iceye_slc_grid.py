#!/usr/bin/env python3

"""
Plot calibrated ICEYE SLC radar brightness in a 2 x 3 grid.

ICEYE SLC samples are stored as separate in-phase and quadrature
datasets:

    s_i
    s_q

Complex SLC power:

    |DN|^2 = I^2 + Q^2

Calibrated radar brightness:

    beta0 = calibration_factor * (I^2 + Q^2)

The data are spatially averaged in LINEAR POWER before conversion
to dB:

    beta0_dB = 10 * log10(mean(beta0))

The HDF5 files are processed in blocks so that the complete
full-resolution SLC does not need to be loaded into memory.

Output is a high-resolution raster PNG.
"""

from pathlib import Path
import argparse
from datetime import datetime

import h5py
import numpy as np

import matplotlib as mpl
import matplotlib.pyplot as plt


# ================================================================
# Command-line arguments
# ================================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Plot calibrated ICEYE SLC beta0 images in a "
            "2-row x 3-column grid."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:

  python plot_iceye_slc_grid.py \\
      --input-dir /nfs/a283/homes/ee16eme/data/fernandina_iceye_july2026/CS-26350 \\
      --output fernandina_iceye_slc_grid.png

Higher-resolution SLC rendering:

  python plot_iceye_slc_grid.py \\
      --input-dir /nfs/a283/homes/ee16eme/data/fernandina_iceye_july2026/CS-26350 \\
      --output fernandina_iceye_slc_grid.png \\
      --max-size 2000 \\
      --dpi 600
        """
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Root directory containing ICEYE SLC HDF5 files.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("iceye_slc_grid.png"),
        help=(
            "Output PNG filename "
            "(default: iceye_slc_grid.png)."
        ),
    )

    parser.add_argument(
        "--max-size",
        type=int,
        default=1800,
        help=(
            "Approximate maximum number of multilooked pixels "
            "along the longest SLC dimension (default: 1800)."
        ),
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=600,
        help=(
            "PNG output resolution in dots per inch "
            "(default: 600)."
        ),
    )

    parser.add_argument(
        "--percentiles",
        type=float,
        nargs=2,
        default=[2.0, 98.0],
        metavar=("LOW", "HIGH"),
        help=(
            "Percentiles for the common beta0 dB display "
            "stretch (default: 2 98)."
        ),
    )

    return parser.parse_args()


# ================================================================
# Metadata helpers
# ================================================================

def decode_h5_value(value):

    if isinstance(value, bytes):
        return value.decode("utf-8")

    return str(value)


def read_metadata(h5_file):

    with h5py.File(h5_file, "r") as f:

        if "s_i" not in f or "s_q" not in f:
            raise KeyError(
                f"{h5_file}: could not find s_i and s_q"
            )

        if "calibration_factor" not in f:
            raise KeyError(
                f"{h5_file}: calibration_factor not found"
            )

        metadata = {}

        metadata["satellite"] = (
            decode_h5_value(
                f["satellite_name"][()]
            )
            if "satellite_name" in f
            else "ICEYE"
        )

        metadata["time"] = (
            decode_h5_value(
                f["acquisition_start_utc"][()]
            )
            if "acquisition_start_utc" in f
            else ""
        )

        metadata["acquisition_id"] = (
            decode_h5_value(
                f["acquisition_id"][()]
            )
            if "acquisition_id" in f
            else ""
        )

        metadata["mode"] = (
            decode_h5_value(
                f["acquisition_mode"][()]
            )
            if "acquisition_mode" in f
            else ""
        )

        metadata["polarization"] = (
            decode_h5_value(
                f["polarization"][()]
            )
            if "polarization" in f
            else ""
        )

        metadata["shape"] = (
            f["s_i"].shape
        )

        metadata["calibration_factor"] = float(
            f["calibration_factor"][()]
        )

    return metadata


# ================================================================
# Multilooking
# ================================================================

def determine_look_factor(shape, max_size):
    """
    Determine a square averaging factor so that the longest
    output dimension is approximately max_size pixels.
    """

    longest_dimension = max(shape)

    factor = int(
        np.ceil(
            longest_dimension / max_size
        )
    )

    return max(1, factor)


def read_multilooked_beta0_db(
    h5_file,
    look_factor,
):
    """
    Read ICEYE I/Q data in strips and average linear SLC power
    over look_factor x look_factor blocks.

    beta0 = calibration_factor * mean(I^2 + Q^2)

    Conversion to dB occurs AFTER averaging.
    """

    with h5py.File(h5_file, "r") as f:

        s_i = f["s_i"]
        s_q = f["s_q"]

        if s_i.shape != s_q.shape:
            raise ValueError(
                f"{h5_file}: s_i and s_q shapes differ"
            )

        calibration_factor = float(
            f["calibration_factor"][()]
        )

        n_azimuth, n_range = s_i.shape

        # --------------------------------------------------------
        # Number of complete averaging blocks.
        # --------------------------------------------------------

        n_out_azimuth = (
            n_azimuth // look_factor
        )

        n_out_range = (
            n_range // look_factor
        )

        if (
            n_out_azimuth < 1
            or n_out_range < 1
        ):
            raise ValueError(
                "Look factor is larger than image dimensions."
            )

        usable_range = (
            n_out_range * look_factor
        )

        print(
            f"  Full SLC       : "
            f"{n_azimuth} x {n_range}"
        )

        print(
            f"  Look factor    : "
            f"{look_factor} x {look_factor}"
        )

        print(
            f"  Output image   : "
            f"{n_out_azimuth} x {n_out_range}"
        )

        print(
            f"  Calibration CF : "
            f"{calibration_factor:.10e}"
        )

        # --------------------------------------------------------
        # Output array.
        # --------------------------------------------------------

        mean_power = np.empty(
            (
                n_out_azimuth,
                n_out_range,
            ),
            dtype=np.float32,
        )

        # --------------------------------------------------------
        # Process one multilooked azimuth row at a time.
        # --------------------------------------------------------

        for output_row in range(
            n_out_azimuth
        ):

            row_start = (
                output_row * look_factor
            )

            row_end = (
                row_start + look_factor
            )

            # Read only this strip from HDF5.
            i = s_i[
                row_start:row_end,
                :usable_range,
            ].astype(
                np.float32
            )

            q = s_q[
                row_start:row_end,
                :usable_range,
            ].astype(
                np.float32
            )

            # Linear complex power.
            power = (
                i * i +
                q * q
            )

            # Rearrange range samples into averaging blocks.
            power = power.reshape(
                look_factor,
                n_out_range,
                look_factor,
            )

            # Average over azimuth and range.
            mean_power[
                output_row,
                :
            ] = power.mean(
                axis=(0, 2)
            )

        # --------------------------------------------------------
        # Apply radiometric calibration.
        # --------------------------------------------------------

        beta0 = (
            mean_power
            * calibration_factor
        )

        # --------------------------------------------------------
        # Convert to dB.
        # --------------------------------------------------------

        beta0_db = np.full(
            beta0.shape,
            np.nan,
            dtype=np.float32,
        )

        valid = (
            np.isfinite(beta0)
            & (beta0 > 0)
        )

        beta0_db[valid] = (
            10.0
            * np.log10(
                beta0[valid]
            )
        )

    return beta0_db


# ================================================================
# Panel title
# ================================================================

def make_title(metadata):

    satellite = metadata["satellite"]

    satellite = satellite.replace(
        "ICEYE-",
        ""
    )

    time_string = metadata["time"]

    try:

        dt = datetime.fromisoformat(
            time_string
        )

        date_label = dt.strftime(
            "%d %b %Y %H:%M"
        )

    except ValueError:

        date_label = time_string

    return (
        f"{satellite} — {date_label}"
    )


# ================================================================
# Main
# ================================================================

def main():

    args = parse_args()

    input_dir = args.input_dir
    output_file = args.output

    # ------------------------------------------------------------
    # Validate input.
    # ------------------------------------------------------------

    if not input_dir.is_dir():
        raise NotADirectoryError(
            f"Input directory does not exist: "
            f"{input_dir}"
        )

    if args.max_size < 10:
        raise ValueError(
            "--max-size must be at least 10"
        )

    if args.dpi < 1:
        raise ValueError(
            "--dpi must be positive"
        )

    low_percentile, high_percentile = (
        args.percentiles
    )

    if not (
        0 <= low_percentile
        < high_percentile
        <= 100
    ):
        raise ValueError(
            "--percentiles must satisfy "
            "0 <= LOW < HIGH <= 100"
        )

    # Force PNG output.
    if output_file.suffix.lower() != ".png":
        output_file = (
            output_file.with_suffix(".png")
        )

    # ------------------------------------------------------------
    # Find SLC files.
    # ------------------------------------------------------------

    h5_files = sorted(
        input_dir.rglob("*SLC*.h5")
    )

    if not h5_files:
        raise FileNotFoundError(
            f"No *SLC*.h5 files found beneath "
            f"{input_dir}"
        )

    print()
    print("ICEYE SLC files")
    print("================")

    for h5_file in h5_files:
        print(h5_file)

    print()
    print(
        f"Found {len(h5_files)} SLC files."
    )

    if len(h5_files) != 6:
        print(
            "WARNING: expected 6 scenes for "
            "a 2 x 3 figure."
        )

    # ------------------------------------------------------------
    # Metadata.
    # ------------------------------------------------------------

    scenes = []

    for h5_file in h5_files:

        metadata = read_metadata(
            h5_file
        )

        scenes.append({
            "file": h5_file,
            "metadata": metadata,
        })

    # Chronological order.
    scenes.sort(
        key=lambda scene:
        scene["metadata"]["time"]
    )

    # ------------------------------------------------------------
    # Process SLCs.
    # ------------------------------------------------------------

    for scene in scenes:

        h5_file = scene["file"]
        metadata = scene["metadata"]

        print()
        print("=" * 70)
        print(h5_file.name)
        print("=" * 70)

        look_factor = determine_look_factor(
            metadata["shape"],
            args.max_size,
        )

        scene["look_factor"] = (
            look_factor
        )

        scene["image"] = (
            read_multilooked_beta0_db(
                h5_file,
                look_factor,
            )
        )

    # ------------------------------------------------------------
    # Common dB stretch.
    # ------------------------------------------------------------

    valid_values = []

    for scene in scenes:

        image = scene["image"]

        # We only need a representative sample to estimate
        # the common display percentiles.
        sample = image[
            ::5,
            ::5,
        ]

        values = sample[
            np.isfinite(sample)
        ]

        if values.size > 0:
            valid_values.append(
                values
            )

    if not valid_values:
        raise ValueError(
            "No valid calibrated pixels found."
        )

    all_valid = np.concatenate(
        valid_values
    )

    vmin, vmax = np.percentile(
        all_valid,
        [
            low_percentile,
            high_percentile,
        ],
    )

    del all_valid

    print()
    print("=" * 70)

    print(
        f"Common beta0 display range: "
        f"{vmin:.2f} to {vmax:.2f} dB"
    )

    print("=" * 70)

    # ============================================================
    # Matplotlib settings
    # ============================================================

    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [
            "Helvetica",
            "Arial",
            "Liberation Sans",
            "DejaVu Sans",
        ],
        "font.size": 11,
        "axes.labelsize": 11,
        "axes.titlesize": 11,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.fontsize": 11,
        "figure.titlesize": 11,
    })

    # ============================================================
    # 2 rows x 3 columns
    # ============================================================

    fig, axes = plt.subplots(
        nrows=2,
        ncols=3,
        figsize=(6.5, 4.0),
    )

    axes = axes.ravel()

    image_handle = None

    # ------------------------------------------------------------
    # Plot each scene.
    # ------------------------------------------------------------

    for index, ax in enumerate(axes):

        if index >= len(scenes):
            ax.axis("off")
            continue

        scene = scenes[index]

        image_handle = ax.imshow(
            scene["image"],
            cmap="gray",
            vmin=vmin,
            vmax=vmax,
            origin="upper",

            # No smoothing/interpolation.
            interpolation="none",

            aspect="auto",
        )

        ax.set_title(
            make_title(
                scene["metadata"]
            ),
            pad=3,
        )

        # No pixel-coordinate labels.
        ax.set_xticks([])
        ax.set_yticks([])

        # --------------------------------------------------------
        # Panel labels.
        # --------------------------------------------------------

        panel_letter = chr(
            ord("a") + index
        )

        ax.text(
            0.025,
            0.965,
            f"({panel_letter})",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=11,
            fontweight="bold",
            color="white",
        )

    # ------------------------------------------------------------
    # Common colour bar.
    # ------------------------------------------------------------

    if image_handle is not None:

        cbar = fig.colorbar(
            image_handle,
            ax=axes.tolist(),
            orientation="horizontal",
            fraction=0.055,
            pad=0.06,
            aspect=45,
        )

        cbar.set_label(
            r"Radar brightness, $\beta^0$ (dB)"
        )

    # ------------------------------------------------------------
    # Layout.
    # ------------------------------------------------------------

    fig.subplots_adjust(
        left=0.02,
        right=0.99,
        top=0.93,
        bottom=0.15,
        wspace=0.05,
        hspace=0.15,
    )

    # ------------------------------------------------------------
    # Save high-resolution raster PNG.
    # ------------------------------------------------------------

    fig.savefig(
        output_file,
        format="png",
        dpi=args.dpi,
        bbox_inches="tight",
        pad_inches=0.02,
    )

    plt.close(fig)

    print()
    print(
        f"Saved PNG: {output_file}"
    )

    print(
        f"Figure size: 6.5 x 4.0 inches"
    )

    print(
        f"Requested DPI: {args.dpi}"
    )


if __name__ == "__main__":
    main()

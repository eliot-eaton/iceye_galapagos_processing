#!/usr/bin/env python3

import argparse
import h5py


def explore_h5_structure(h5_file):
    """
    Explore and print the structure of an HDF5 file.

    Args:
        h5_file (str): Path to input HDF5 file.
    """
    print(f"🔍 Exploring structure of {h5_file}...\n")

    with h5py.File(h5_file, "r") as f:
        print("=" * 60)
        print("HDF5 FILE STRUCTURE")
        print("=" * 60)

        def print_structure(name, obj):
            """Recursive function to print HDF5 structure."""
            if isinstance(obj, h5py.Dataset):
                print(f"\n📊 Dataset: {name}")
                print(f"   Shape: {obj.shape}")
                print(f"   Dtype: {obj.dtype}")

                if obj.shape == ():
                    print(f"   Value: {obj[()]}")
                else:
                    print(f"   Size: {obj.size} elements")

                if len(obj.attrs) > 0:
                    print("   Attributes:")
                    for attr_name, attr_val in obj.attrs.items():
                        print(f"      {attr_name}: {attr_val}")

            elif isinstance(obj, h5py.Group):
                print(f"\n📁 Group: {name}")

                if len(obj.attrs) > 0:
                    print("   Attributes:")
                    for attr_name, attr_val in obj.attrs.items():
                        print(f"      {attr_name}: {attr_val}")

        f.visititems(print_structure)

        print("\n" + "=" * 60)
        print(f"Total keys in root: {list(f.keys())}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Explore and print the structure of an HDF5 file."
    )

    parser.add_argument(
        "h5_file",
        help="Path to the input HDF5 file."
    )

    args = parser.parse_args()
    explore_h5_structure(args.h5_file)


if __name__ == "__main__":
    main()

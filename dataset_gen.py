import argparse
import os
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


# Specific tollgate identifiers.
# We store them in the "region" column because the assignment imposes
# the fixed schema: ts, user_id, region, event_type, value.
TOLLGATES = [
    "tollgate_a1_lausanne",
    "tollgate_a1_geneva",
    "tollgate_a9_sion",
    "tollgate_a12_fribourg",
    "tollgate_a2_lugano",
    "tollgate_a13_chur",
]

# Vehicle categories.
# We store them in the "event_type" column to stay compatible
# with the required project schema.
VEHICLE_TYPES = [
    "motorcycle",
    "car",
    "van",
    "bus",
    "truck",
]

# Size presets used to generate reproducible datasets.
# These row counts follow the alternative allowed in the assignment:
# using number of rows instead of exact stored size.
SIZE_TO_ROWS = {
    "S": 5_000_000,
    "M": 25_000_000,
    "L": 100_000_000,
}


def make_batch(start_ts, rows, user_id_max, seed):
    """
    Generate one in-memory batch of synthetic tollgate records.

    Output schema:
      - ts: timestamp of the vehicle passage
      - user_id: synthetic identifier for a vehicle/account/tag
      - region: tollgate identifier
      - event_type: vehicle category
      - value: toll amount
    """
    rng = np.random.default_rng(seed)

    # Spread events across a 90-day window starting from start_ts.
    ts_offsets = rng.integers(0, 90 * 24 * 3600, size=rows, dtype=np.int64)
    timestamps = [start_ts + timedelta(seconds=int(x)) for x in ts_offsets]

    # Synthetic user/account/transponder ids.
    user_ids = rng.integers(1, user_id_max + 1, size=rows, dtype=np.int32)

    # Non-uniform probabilities make the dataset more realistic.
    # Some tollgates are busier than others.
    tollgates = rng.choice(
        TOLLGATES,
        size=rows,
        p=[0.22, 0.20, 0.14, 0.14, 0.16, 0.14]
    )

    # Cars are the most frequent vehicle type in this synthetic scenario.
    vehicle_types = rng.choice(
        VEHICLE_TYPES,
        size=rows,
        p=[0.08, 0.60, 0.15, 0.05, 0.12]
    )

    # Base toll values by vehicle category.
    # We later add a bit of random noise to avoid perfectly constant values.
    toll_base_price = {
        "motorcycle": 3.5,
        "car": 7.0,
        "van": 10.5,
        "bus": 16.0,
        "truck": 22.0,
    }

    # Generate the "value" column as a toll amount with slight variability.
    values = np.empty(rows, dtype=np.float32)
    for i, vehicle in enumerate(vehicle_types):
        noise = rng.normal(0, 0.8)
        values[i] = max(0.0, toll_base_price[vehicle] + noise)

    # Build a PyArrow table with the exact schema expected by the assignment.
    table = pa.table({
        "ts": pa.array(timestamps, type=pa.timestamp("ms")),
        "user_id": pa.array(user_ids, type=pa.int32()),
        "region": pa.array(tollgates, type=pa.string()),
        "event_type": pa.array(vehicle_types, type=pa.string()),
        "value": pa.array(values, type=pa.float32()),
    })

    return table


def write_small_files(output_dir, total_rows, rows_per_file, compression, seed):
    """
    Write the dataset as many small Parquet files.

    This is intentional for Variant 3:
    we want a "small-files layout" first, so that we can later
    compact it into fewer larger files and compare performance.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Fixed reference date for reproducibility.
    start_ts = datetime(2025, 1, 1, tzinfo=timezone.utc)

    # Number of output files needed to store all rows.
    num_files = (total_rows + rows_per_file - 1) // rows_per_file

    written_rows = 0

    start_time = time.time() # Starting the timer

    for file_idx in range(num_files):
        # Last file may contain fewer rows than the others.
        rows_this_file = min(rows_per_file, total_rows - written_rows)

        # Use a different seed per file to avoid identical batches.
        table = make_batch(
            start_ts=start_ts,
            rows=rows_this_file,
            user_id_max=2_000_000,
            seed=seed + file_idx
        )

        # Sequential file naming makes later listing and compaction easier.
        file_path = os.path.join(output_dir, f"part-{file_idx:06d}.parquet")

        # Write one Parquet object.
        # Dictionary encoding is enabled because repeated strings
        # such as tollgate names and vehicle types compress well.
        pq.write_table(
            table,
            file_path,
            compression=compression,
            use_dictionary=True
        )

        written_rows += rows_this_file

        # Progress message every 100 files and at the very end.
        if (file_idx + 1) % 100 == 0 or file_idx == num_files - 1:
            print(f"Written {file_idx + 1}/{num_files} files")

    elapsed = time.time() - start_time # Ending the timer
    return num_files, elapsed


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic tollgate traffic dataset in Parquet small-files layout"
    )

    # Logical dataset name, used in the output path.
    parser.add_argument(
        "--dataset-id",
        required=True,
        help="Dataset identifier, e.g. tollgate_s"
    )

    # Root directory where curated/<dataset_id>/small will be created.
    parser.add_argument(
        "--base-dir",
        default="data",
        help="Base output directory"
    )

    # Required size preset: S, M, or L.
    parser.add_argument(
        "--size",
        choices=["S", "M", "L"],
        required=True,
        help="Dataset size preset"
    )

    # Small rows_per_file => many small Parquet files.
    # This is the key parameter for simulating the small-files problem.
    parser.add_argument(
        "--rows-per-file",
        type=int,
        default=10_000,
        help="Rows per Parquet file for small-files layout"
    )

    # Compression can be kept configurable for experiments.
    parser.add_argument(
        "--compression",
        default="snappy",
        choices=["snappy", "zstd", "gzip", "none"],
        help="Parquet compression codec"
    )

    # Seed ensures reproducible data generation.
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed"
    )

    args = parser.parse_args()

    # Translate size preset into total row count.
    total_rows = SIZE_TO_ROWS[args.size]

    # PyArrow expects None when no compression should be used.
    compression = None if args.compression == "none" else args.compression

    # Curated output path for the small-files version of the dataset.
    output_dir = os.path.join(
        args.base_dir,
        "curated",
        args.dataset_id,
        "small"
    )

    num_files, elapsed = write_small_files(
        output_dir=output_dir,
        total_rows=total_rows,
        rows_per_file=args.rows_per_file,
        compression=compression,
        seed=args.seed
    )

    # Final summary for reproducibility and logging.
    print("\n=== Dataset generation complete ===")
    print(f"Theme           : tollgate traffic")
    print(f"Dataset id      : {args.dataset_id}")
    print(f"Size preset     : {args.size}")
    print(f"Total rows      : {total_rows}")
    print(f"Rows per file   : {args.rows_per_file}")
    print(f"Files created   : {num_files}")
    print(f"Compression     : {args.compression}")
    print(f"Elapsed time    : {elapsed:.2f} seconds")
    print(f"Output path     : {output_dir}")


if __name__ == "__main__":
    main()
# Authors : Tanguy Godat & Tim Gouvernon --Variant 3

import argparse
import os
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

TOLLGATES = [
    "tollgate_a1_lausanne",
    "tollgate_a1_geneva",
    "tollgate_a9_sion",
    "tollgate_a12_fribourg",
    "tollgate_a2_lugano",
    "tollgate_a13_chur",
]

VEHICLE_TYPES = ["motorcycle", "car", "van", "bus", "truck"]

SIZE_TO_ROWS = {
    "Test": 100_000,
    "S": 5_000_000,
    "M": 25_000_000,
    "L": 100_000_000,
}


def make_batch(start_ts, rows, user_id_max, seed):
    rng = np.random.default_rng(seed) #seed allow reproducibility
    ts_offsets = rng.integers(0, 90 * 24 * 3600, size=rows, dtype=np.int64)
    timestamps = [start_ts + timedelta(seconds=int(x)) for x in ts_offsets]
    user_ids = rng.integers(1, user_id_max + 1, size=rows, dtype=np.int32)
    tollgates = rng.choice(TOLLGATES, size=rows, p=[0.22, 0.20, 0.14, 0.14, 0.16, 0.14])
    vehicle_types = rng.choice(VEHICLE_TYPES, size=rows, p=[0.08, 0.60, 0.15, 0.05, 0.12])

    toll_base_price = {
        "motorcycle": 3.5,
        "car": 7.0,
        "van": 10.5,
        "bus": 16.0,
        "truck": 22.0,
    }

    values = np.empty(rows, dtype=np.float32)
    for i, vehicle in enumerate(vehicle_types):
        noise = rng.normal(0, 0.8)
        values[i] = max(0.0, toll_base_price[vehicle] + noise)

    table = pa.table({
        "ts": pa.array(timestamps, type=pa.timestamp("ms")),
        "user_id": pa.array(user_ids, type=pa.int32()),
        "region": pa.array(tollgates, type=pa.string()),
        "event_type": pa.array(vehicle_types, type=pa.string()),
        "value": pa.array(values, type=pa.float32()),
    })
    return table


def write_small_files(output_dir, total_rows, rows_per_file, seed):
    os.makedirs(output_dir, exist_ok=True)
    start_ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
    num_files = (total_rows + rows_per_file - 1) // rows_per_file # rounds up the value, math.ceil
    written_rows = 0
    start_time = time.time()

    for file_idx in range(num_files):
        rows_this_file = min(rows_per_file, total_rows - written_rows)
        table = make_batch(
            start_ts=start_ts,
            rows=rows_this_file,
            user_id_max=2_000_000,
            seed=seed + file_idx, #offset in order to not have x times the same batch
        )
        file_path = os.path.join(output_dir, f"part-{file_idx:06d}.parquet")
        pq.write_table(table, file_path, compression="none", use_dictionary=True)
        written_rows += rows_this_file

        if (file_idx + 1) % 100 == 0 or file_idx == num_files - 1: #print once every 100 files done
            print(f"Written {file_idx + 1}/{num_files} files")

    elapsed = time.time() - start_time
    return num_files, elapsed


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic tollgate traffic dataset in Parquet small-files layout"
    )
    parser.add_argument("--dataset-id", required=True, help="Dataset identifier, e.g. tollgate_s")
    parser.add_argument("--base-dir", default="data", help="Base output directory")
    parser.add_argument("--size", choices=["S", "M", "L"], required=True, help="Dataset size preset")
    parser.add_argument(
        "--rows-per-file",
        type=int,
        default=10_000,
        help="Rows per Parquet file for small-files layout",
    )

    parser.add_argument("--seed", type=int, default=67, help="Random seed")
    args = parser.parse_args()

    total_rows = SIZE_TO_ROWS[args.size]
    output_dir = os.path.join(args.base_dir, "curated", args.dataset_id, "small")

    num_files, elapsed = write_small_files(
        output_dir=output_dir,
        total_rows=total_rows,
        rows_per_file=args.rows_per_file,
        seed=args.seed
    )

    print("\n=== Dataset generation complete ===")
    print(f"Theme : tollgate traffic")
    print(f"Dataset id : {args.dataset_id}")
    print(f"Size preset : {args.size}")
    print(f"Total rows : {total_rows}")
    print(f"Rows per file : {args.rows_per_file}")
    print(f"Files created : {num_files}")
    print(f"Compression : {"none"}")
    print(f"Elapsed time : {elapsed:.2f} seconds")
    print(f"Output path : {output_dir}")


if __name__ == "__main__":
    main()
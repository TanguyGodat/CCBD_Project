#have to modify dataset_gen and compoact to be able to call their main
import argparse
import os
import time
import pyarrow as pa
from dataset_gen import write_small_files
from compact import compact_dataset
# from upload import main
# from download import main

# intended structure for now
# bench.main(dataset-id, size, compact) -> generate data -> upload 
# -> list? -> query (filter region and time, group event_type, compute count and average value)
# -> download ? (whole dataset?)


def main(small_output_dir_, compact_output_dir_, total_rows_, compression_, rows_per_file_, to_compact_, compact_factor_, seed_):
    
    # gen 

    small_num_files, small_elapsed = write_small_files(
        output_dir=small_output_dir_,
        total_rows=total_rows_,
        rows_per_file=rows_per_file_,
        compression=compression_,
        seed=seed_
    )

    if to_compact_:
        compact_total_rows, compact_file_count, compact_elapsed, compact_rows_per_output_file = compact_dataset(
            input_dir=small_output_dir_,
            output_dir=compact_output_dir_,
            output_file_count=int(rows_per_file_/compact_factor_),  # For simplicity, use rows_per_file as the target file count for compaction.
            compression=compression_
        )

    # upload

    # list

    # query

    # download



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark a generated synthetic tollgate traffic dataset in Parquet"
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

    # Option to run compaction after generation
    parser.add_argument(
        "--to-compact",
        type=bool,
        default=False,
        help="Choose to run compaction after generation"
    )

    parser.add_argument(
        "--compact-factor",
        type=int,
        default=25,
        help="Factor by which to reduce the number of files during compaction (e.g., 10 means 10x fewer files)"
    )

    # Compression can be kept configurable for experiments.
    parser.add_argument(
        "--compression",
        default="none",
        choices=["snappy", "zstd", "gzip", "none"],
        help="Parquet compression codec"
    )

    # Seed ensures reproducible data generation.
    parser.add_argument(
        "--seed",
        type=int,
        default=67,
        help="Random seed"
    )

    args = parser.parse_args()

    # Translate size preset into total row count.
    # to modify in dataset_gen, write_small_files take args.size instead of total_rows
    SIZE_TO_ROWS = { #temporary fix
    "S": 5_000_000,
    "M": 25_000_000,
    "L": 100_000_000,
    }
    total_rows = SIZE_TO_ROWS[args.size]

    # PyArrow expects None when no compression should be used.
    compression = None if args.compression == "none" else args.compression

    # Curated output path for the small-files version of the dataset.
    small_output_dir = os.path.join(
        args.base_dir,
        "curated",
        args.dataset_id,
        "small"
    )
    compact_output_dir = small_output_dir  # Default to small output dir if not compacting
    compact_factor = 1
    if args.to_compact:
        compact_output_dir = os.path.join(
                args.base_dir,
                "curated",
                args.dataset_id,
                "compact"
        )
        compact_factor = args.compact_factor

    main(small_output_dir, compact_output_dir, total_rows, compression, args.rows_per_file, args.to_compact, compact_factor, args.seed)


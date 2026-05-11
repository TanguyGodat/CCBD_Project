import argparse
import os
import time

import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq


def count_parquet_files(directory):
    """
    Count how many Parquet files exist under a directory.
    """
    count = 0
    for name in os.listdir(directory):
        if name.endswith(".parquet"):
            count += 1
    return count


def compact_dataset(input_dir, output_dir, output_file_count):
    """
    Read a small-files Parquet dataset and rewrite it as a chosen number
    of larger Parquet files.
    """
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    if os.path.exists(output_dir):
        raise FileExistsError(
            f"Output directory already exists: {output_dir}. "
            f"Remove it first or choose another output path."
        )

    if output_file_count <= 0:
        raise ValueError("output_file_count must be > 0")

    os.makedirs(output_dir, exist_ok=True)

    dataset = ds.dataset(input_dir, format="parquet")
    total_rows = dataset.count_rows()

    # Compute the target number of rows per compacted output file.
    rows_per_output_file = (total_rows + output_file_count - 1) // output_file_count

    # Read in reasonably sized batches, then merge several batches together
    # before writing one larger compact file.
    scanner = dataset.scanner(batch_size=100_000)

    buffered_batches = []
    buffered_rows = 0
    written_rows = 0
    file_idx = 0

    start_time = time.time()

    for record_batch in scanner.to_batches():
        buffered_batches.append(record_batch)
        buffered_rows += record_batch.num_rows

        # When enough rows are buffered, write one compact file.
        if buffered_rows >= rows_per_output_file:
            table = pa.Table.from_batches(buffered_batches)

            file_path = os.path.join(output_dir, f"part-{file_idx:05d}.parquet")
            pq.write_table(
                table,
                file_path,
                compression="none",
                use_dictionary=True
            )

            written_rows += table.num_rows
            file_idx += 1

            print(
                f"Written compact file {file_idx}/{output_file_count}, "
                f"rows written: {written_rows}/{total_rows}"
            )

            buffered_batches = []
            buffered_rows = 0

    # Write remaining rows, if any.
    if buffered_batches:
        table = pa.Table.from_batches(buffered_batches)

        file_path = os.path.join(output_dir, f"part-{file_idx:05d}.parquet")
        pq.write_table(
            table,
            file_path,
            compression="none",
            use_dictionary=True
        )

        written_rows += table.num_rows
        file_idx += 1

        print(
            f"Written final compact file {file_idx}, "
            f"rows written: {written_rows}/{total_rows}"
        )

    elapsed = time.time() - start_time
    return total_rows, file_idx, elapsed, rows_per_output_file


def main():
    parser = argparse.ArgumentParser(
        description="Compact a small-files Parquet dataset into a chosen number of larger files"
    )
    parser.add_argument(
        "--dataset-id",
        required=True,
        help="Dataset identifier, e.g. tollgate_s"
    )
    parser.add_argument(
        "--base-dir",
        default="data",
        help="Base directory containing curated/<dataset_id>/small"
    )
    parser.add_argument(
        "--output-file-count",
        type=int,
        required=True,
        help="Desired number of files in the compact output layout"
    )

    args = parser.parse_args()

    input_dir = os.path.join(
        args.base_dir,
        "curated",
        args.dataset_id,
        "small"
    )

    output_dir = os.path.join(
        args.base_dir,
        "curated",
        args.dataset_id,
        "compact"
    )

    small_file_count = count_parquet_files(input_dir)

    total_rows, compact_file_count, elapsed, rows_per_output_file = compact_dataset(
        input_dir=input_dir,
        output_dir=output_dir,
        output_file_count=args.output_file_count
    )

    print("\n=== Compaction complete ===")
    print(f"Dataset id            : {args.dataset_id}")
    print(f"Input path            : {input_dir}")
    print(f"Output path           : {output_dir}")
    print(f"Input file count      : {small_file_count}")
    print(f"Requested output files: {args.output_file_count}")
    print(f"Actual output files   : {compact_file_count}")
    print(f"Total rows            : {total_rows}")
    print(f"Rows per output file  : {rows_per_output_file}")
    print(f"Compression           : {"none"}")
    print(f"Elapsed time (s)      : {elapsed:.2f}")


if __name__ == "__main__":
    main()
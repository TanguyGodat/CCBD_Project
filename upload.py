import argparse
import os
import time

import boto3


def collect_files(root_dir):
    files = []
    for root, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".parquet") or filename.endswith(".json"):
                files.append(os.path.join(root, filename))
    return sorted(files)


def upload_directory(s3_client, bucket, local_dir, s3_prefix):
    if not os.path.exists(local_dir):
        raise FileNotFoundError(f"Local directory does not exist: {local_dir}")

    files = collect_files(local_dir)
    if not files:
        raise ValueError(f"No files found in: {local_dir}")

    total_bytes = 0
    start = time.time()

    for i, file_path in enumerate(files, start=1):
        rel_path = os.path.relpath(file_path, local_dir).replace("\\", "/")
        key = f"{s3_prefix}/{rel_path}"
        size = os.path.getsize(file_path)
        s3_client.upload_file(file_path, bucket, key)
        total_bytes += size
        print(f"[{i}/{len(files)}] uploaded {key}")

    elapsed = time.time() - start
    return total_bytes, len(files), elapsed


def main():
    parser = argparse.ArgumentParser(description="Upload a curated dataset layout to MinIO/S3")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--layout", required=True, choices=["small", "compact"])
    parser.add_argument("--base-dir", default="data")
    parser.add_argument("--endpoint-url", required=True)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--access-key", default=None)
    parser.add_argument("--secret-key", default=None)
    args = parser.parse_args()

    local_dir = os.path.join(args.base_dir, "curated", args.dataset_id, args.layout)
    s3_prefix = f"curated/{args.dataset_id}/{args.layout}"

    client_kwargs = {
        "endpoint_url": args.endpoint_url,
        "region_name": args.region,
    }
    if args.access_key and args.secret_key:
        client_kwargs["aws_access_key_id"] = args.access_key
        client_kwargs["aws_secret_access_key"] = args.secret_key

    s3 = boto3.client("s3", **client_kwargs)

    total_bytes, file_count, elapsed = upload_directory(
        s3_client=s3,
        bucket=args.bucket,
        local_dir=local_dir,
        s3_prefix=s3_prefix,
    )

    mb = total_bytes / (1024 * 1024)
    throughput = mb / elapsed if elapsed > 0 else 0.0

    print("\n=== Upload complete ===")
    print(f"Local dir   : {local_dir}")
    print(f"S3 prefix   : {s3_prefix}")
    print(f"Files       : {file_count}")
    print(f"Bytes       : {total_bytes}")
    print(f"Elapsed (s) : {elapsed:.2f}")
    print(f"Throughput  : {throughput:.2f} MB/s")


if __name__ == "__main__":
    main()

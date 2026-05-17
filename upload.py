# Authors : Tanguy Godat & Tim Gouvernon --Variant 3

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
        key = f"{s3_prefix}/{rel_path}" if s3_prefix else rel_path
        size = os.path.getsize(file_path)
        s3_client.upload_file(file_path, bucket, key)
        total_bytes += size
        print(f"[{i}/{len(files)}] uploaded {key}")

    elapsed = time.time() - start
    return total_bytes, len(files), elapsed


def main():
    parser = argparse.ArgumentParser(description="Upload any local dataset directory to MinIO/S3")
    parser.add_argument("--bucket", required=True, help="Target bucket")
    parser.add_argument("--local-dir", required=True, help="Local directory to upload")
    parser.add_argument("--prefix", required=True, help="Target S3 prefix")
    parser.add_argument("--endpoint-url", required=True, help="MinIO/S3 endpoint URL")
    parser.add_argument("--region", default="us-east-1", help="S3 region")
    parser.add_argument("--access-key", default=None, help="S3 access key")
    parser.add_argument("--secret-key", default=None, help="S3 secret key")
    args = parser.parse_args()

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
        local_dir=args.local_dir,
        s3_prefix=args.prefix,
    )

    mb = total_bytes / (1024 * 1024)
    throughput = mb / elapsed if elapsed > 0 else 0.0

    print("\n=== Upload complete ===")
    print(f"Local dir : {args.local_dir}")
    print(f"S3 prefix : {args.prefix}")
    print(f"Files : {file_count}")
    print(f"Bytes : {total_bytes}")
    print(f"Elapsed (s) : {elapsed:.2f}")
    print(f"Throughput : {throughput:.2f} MB/s")


if __name__ == "__main__":
    main()
# Authors : Tanguy Godat & Tim Gouvernon --Variant 3

import argparse
import os
import time

import boto3


def list_objects(s3_client, bucket, prefix):
    keys = []
    token = None

    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token

        resp = s3_client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            key = obj["Key"]
            if not key.endswith("/"):
                keys.append(key)

        if resp.get("IsTruncated"):
            token = resp.get("NextContinuationToken")
        else:
            break

    return sorted(keys)


def download_prefix(s3_client, bucket, prefix, local_dir):
    keys = list_objects(s3_client, bucket, prefix)
    if not keys:
        raise ValueError(f"No objects found under prefix: {prefix}")

    os.makedirs(local_dir, exist_ok=True)

    total_bytes = 0
    start = time.time()

    for i, key in enumerate(keys, start=1):
        rel_path = os.path.relpath(key, prefix).replace("\\", "/")
        out_path = os.path.join(local_dir, rel_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        s3_client.download_file(bucket, key, out_path)
        size = os.path.getsize(out_path)
        total_bytes += size
        print(f"[{i}/{len(keys)}] downloaded {key}")

    elapsed = time.time() - start
    return total_bytes, len(keys), elapsed


def main():
    parser = argparse.ArgumentParser(description="Download any MinIO/S3 prefix to a local directory")
    parser.add_argument("--bucket", required=True, help="Source bucket")
    parser.add_argument("--prefix", required=True, help="S3 prefix to download")
    parser.add_argument("--local-dir", required=True, help="Local output directory")
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

    total_bytes, file_count, elapsed = download_prefix(
        s3_client=s3,
        bucket=args.bucket,
        prefix=args.prefix,
        local_dir=args.local_dir,
    )

    mb = total_bytes / (1024 * 1024)
    throughput = mb / elapsed if elapsed > 0 else 0.0

    print("\n=== Download complete ===")
    print(f"S3 prefix : {args.prefix}")
    print(f"Local dir : {args.local_dir}")
    print(f"Files : {file_count}")
    print(f"Bytes : {total_bytes}")
    print(f"Elapsed (s) : {elapsed:.2f}")
    print(f"Throughput : {throughput:.2f} MB/s")


if __name__ == "__main__":
    main()
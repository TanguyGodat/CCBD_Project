# Variant 3 — Small Files vs Compaction

Authors: Tanguy Godat & Tim Gouvernon

This project studies the impact of **small files** versus **compacted files** on object-storage performance. The workflow generates synthetic Parquet datasets, compacts them into fewer larger files, uploads them to a MinIO/S3-compatible object store, runs a fixed query directly on S3, downloads the data back locally, and records all measurements in a CSV file.

The benchmark compares two layouts:
- **small**: many small Parquet files
- **compact**: the same logical dataset rewritten into fewer larger Parquet files

Three dataset sizes are supported:
- **S** = 5,000,000 rows
- **M** = 25,000,000 rows
- **L** = 100,000,000 rows

## Dependencies

The project requires Python 3 and the following packages:
- `boto3`
- `numpy`
- `pyarrow`
- `pandas`
- `matplotlib`
- `jupyter`
- `ipykernel`

A minimal `requirements.txt` is:

```txt
boto3
numpy
pyarrow
pandas
matplotlib
jupyter
ipykernel
```

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Project files

- `dataset_gen.py`: generates the synthetic tollgate traffic dataset in a small-files Parquet layout.
- `compact.py`: compacts a small-files dataset into fewer larger Parquet files.
- `upload.py`: uploads a local dataset directory to MinIO/S3.
- `download.py`: downloads a MinIO/S3 prefix to a local directory.
- `bench.py`: orchestrates the full benchmark workflow and writes results to a CSV file.
- `analysis.ipynb`: analyzes `results/results.csv` and produces summary tables and plots.

## Endpoint configuration

The scripts use a MinIO/S3-compatible endpoint and accept the endpoint configuration through command-line arguments. Upload, download, and benchmark scripts all require an endpoint URL and bucket name, and they optionally accept an access key, secret key, and region.

Typical parameters are:
- `--endpoint-url`: MinIO/S3 endpoint, for example `http://localhost:9000`
- `--bucket`: target bucket name
- `--region` or `--region-name`: S3 region, default `us-east-1`
- `--access-key`: S3 access key
- `--secret-key`: S3 secret key

Example environment values:

```bash
export S3_ENDPOINT="http://localhost:9000"
export S3_BUCKET="ccbd"
export S3_REGION="us-east-1"
export S3_ACCESS_KEY="minioadmin"
export S3_SECRET_KEY="minioadmin123"
```

## How to run

### 1. Generate the small-files dataset

This script creates a dataset under `data/curated/<dataset_id>/small`. The size preset must be one of `S`, `M`, or `L`, and the default number of rows per small file is 10,000.

Example:

```bash
python dataset_gen.py \
  --dataset-id tollgate_s \
  --base-dir data \
  --size S \
  --rows-per-file 10000 \
  --seed 67
```

### 2. Compact the dataset

This script reads the small-files dataset and rewrites it into a compacted layout under `data/curated/<dataset_id>/compact`. The compaction level is controlled by `--output-compact-ratio`, which defaults to 25.

Example:

```bash
python compact.py \
  --dataset-id tollgate_s \
  --base-dir data \
  --output-compact-ratio 25
```

### 3. Upload a dataset to MinIO/S3

This script uploads all `.parquet` and `.json` files from a local directory to a given bucket and prefix.

Example:

```bash
python upload.py \
  --bucket "$S3_BUCKET" \
  --local-dir data/curated/tollgate_s/small \
  --prefix bench/tollgate_s/small \
  --endpoint-url "$S3_ENDPOINT" \
  --region "$S3_REGION" \
  --access-key "$S3_ACCESS_KEY" \
  --secret-key "$S3_SECRET_KEY"
```

### 4. Download a dataset from MinIO/S3

This script downloads all objects stored under a prefix into a local directory.

Example:

```bash
python download.py \
  --bucket "$S3_BUCKET" \
  --prefix bench/tollgate_s/small \
  --local-dir bench_downloads/tollgate_s/small \
  --endpoint-url "$S3_ENDPOINT" \
  --region "$S3_REGION" \
  --access-key "$S3_ACCESS_KEY" \
  --secret-key "$S3_SECRET_KEY"
```

## Full benchmark workflow

The main script is `bench.py`. It can:
1. generate a small-files dataset locally,
2. compact it locally,
3. upload each tested layout to MinIO/S3,
4. measure listing time,
5. run a fixed query directly on S3,
6. download the uploaded objects back locally,
7. append the results to `results/results.csv`.

The benchmark query filters on:
- `region = tollgate_a1_geneva`
- `2025-01-15T00:00:00+00:00 <= ts < 2025-02-15T00:00:00+00:00`

### Example: reproduce the benchmark for size S

```bash
python bench.py \
  --dataset-id tollgate_s \
  --size S \
  --bucket "$S3_BUCKET" \
  --endpoint-url "$S3_ENDPOINT" \
  --region-name "$S3_REGION" \
  --access-key "$S3_ACCESS_KEY" \
  --secret-key "$S3_SECRET_KEY" \
  --rows-per-file 10000 \
  --compact-output-ratio 25 \
  --seed 67 \
  --small-output-dir data/curated/tollgate_s/small \
  --compact-from data/curated/tollgate_s/small \
  --compact-to data/curated/tollgate_s/compact \
  --download-base-dir bench_downloads \
  --results-csv results/results.csv \
  --query-region tollgate_a1_geneva \
  --query-start 2025-01-15T00:00:00+00:00 \
  --query-end 2025-02-15T00:00:00+00:00 \
  --layout small::data/curated/tollgate_s/small::bench/tollgate_s/small \
  --layout compact::data/curated/tollgate_s/compact::bench/tollgate_s/compact
```

### Example: reproduce the benchmark for sizes M and L

For `M`:

```bash
python bench.py \
  --dataset-id tollgate_m \
  --size M \
  --bucket "$S3_BUCKET" \
  --endpoint-url "$S3_ENDPOINT" \
  --region-name "$S3_REGION" \
  --access-key "$S3_ACCESS_KEY" \
  --secret-key "$S3_SECRET_KEY" \
  --rows-per-file 10000 \
  --compact-output-ratio 25 \
  --seed 67 \
  --small-output-dir data/curated/tollgate_m/small \
  --compact-from data/curated/tollgate_m/small \
  --compact-to data/curated/tollgate_m/compact \
  --download-base-dir bench_downloads \
  --results-csv results/results.csv \
  --query-region tollgate_a1_geneva \
  --query-start 2025-01-15T00:00:00+00:00 \
  --query-end 2025-02-15T00:00:00+00:00 \
  --layout small::data/curated/tollgate_m/small::bench/tollgate_m/small \
  --layout compact::data/curated/tollgate_m/compact::bench/tollgate_m/compact
```

For `L`:

```bash
python bench.py \
  --dataset-id tollgate_l \
  --size L \
  --bucket "$S3_BUCKET" \
  --endpoint-url "$S3_ENDPOINT" \
  --region-name "$S3_REGION" \
  --access-key "$S3_ACCESS_KEY" \
  --secret-key "$S3_SECRET_KEY" \
  --rows-per-file 10000 \
  --compact-output-ratio 25 \
  --seed 67 \
  --small-output-dir data/curated/tollgate_l/small \
  --compact-from data/curated/tollgate_l/small \
  --compact-to data/curated/tollgate_l/compact \
  --download-base-dir bench_downloads \
  --results-csv results/results.csv \
  --query-region tollgate_a1_geneva \
  --query-start 2025-01-15T00:00:00+00:00 \
  --query-end 2025-02-15T00:00:00+00:00 \
  --layout small::data/curated/tollgate_l/small::bench/tollgate_l/small \
  --layout compact::data/curated/tollgate_l/compact::bench/tollgate_l/compact
```

## Output files

The benchmark appends one CSV row per tested layout to `results/results.csv`. Each row contains metadata and measurements such as local file count, upload throughput, listing time, query time, and download throughput.

Typical output directories are:
- `data/curated/<dataset_id>/small`
- `data/curated/<dataset_id>/compact`
- `bench_downloads/<dataset_id>/<layout>`
- `results/results.csv`

## How to reproduce the reported results

To reproduce the results presented in the notebook:
1. install the dependencies;
2. configure access to a running MinIO/S3-compatible endpoint;
3. run `bench.py` once for each dataset size `S`, `M`, and `L` using the commands above;
4. confirm that the results are appended to `results/results.csv`;
5. open `analysis.ipynb` and run all cells from top to bottom.

The notebook reads `results/results.csv`, sorts runs by dataset size, builds summary tables, computes speedups, and plots the four key metrics: upload throughput, download throughput, listing time, and query execution time.

## Notes

- The synthetic dataset models tollgate traffic events with columns `ts`, `user_id`, `region`, `event_type`, and `value`.
- The Parquet files are written with `compression="none"`.
- The benchmark directly queries Parquet data on S3 using PyArrow dataset filtering and aggregation.
- The compact layout is produced from the small layout using a configurable compaction ratio.

# Variant 3 — Small Files vs Compaction

Authors: Tanguy Godat & Tim Gouvernon

This project evaluates the impact of **small Parquet files** versus **compacted Parquet files** on object-storage performance. The workflow generates synthetic datasets, optionally compacts them into fewer larger files, uploads them to a MinIO/S3-compatible object store, runs a fixed analytical query directly on S3, downloads the data back locally, and stores the benchmark measurements in CSV files. The current execution flow is designed to run cleanly inside a Docker container and to launch benchmark configurations through `@` argument files such as `S3_requirement.txt`, `S_small.txt`, and `S_compact.txt`.

The benchmark compares two layouts:
- **small**: many small Parquet files
- **compact**: the same logical dataset rewritten into fewer larger files

Three dataset sizes are supported:
- **S** = 5,000,000 rows
- **M** = 25,000,000 rows
- **L** = 100,000,000 rows

## Repository contents

- `dataset_gen.py`: generates the synthetic tollgate traffic dataset in a small-files layout.
- `compact.py`: compacts a small-files dataset into fewer larger files.
- `upload.py`: uploads a local dataset directory to MinIO/S3.
- `download.py`: downloads a MinIO/S3 prefix to a local directory.
- `bench.py`: orchestrates the benchmark workflow and writes results to CSV.
- `analysis.ipynb`: analyzes generated benchmark outputs and builds the final tables and plots.
- `S3_requirement.txt`: shared S3 connection parameters.
- `S_small.txt`, `M_small.txt`, `L_small.txt`: benchmark parameter files for the small-files layout.
- `S_compact.txt`, `M_compact.txt`, `L_compact.txt`: benchmark parameter files for the compact layout.
- `entrypoint.sh`: starts MinIO and prepares the container environment.
- `Dockerfile`: builds the benchmark container.

## Dependencies

The project requires Python 3 and the packages listed in `requirements.txt`, including `boto3`, `numpy`, `pyarrow`, `pandas`, `matplotlib`, `jupyter`, and `ipykernel`.

For a local installation outside Docker:

```bash
pip install -r requirements.txt
```

## Container workflow

The recommended workflow is to run the benchmark inside Docker. The container installs Python, MinIO, and the MinIO client, clones the repository, creates a virtual environment, installs the Python dependencies, and starts a local MinIO service through `entrypoint.sh`.

### 1. Build the image

```bash
docker build -t ccbd-project .
```

### 2. Start the container

```bash
docker run --rm -it \
  -p 9000:9000 \
  -p 9001:9001 \
  -v "$(pwd)/results:/opt/CCBD_Project/results" \
  ccbd-project
```

This starts the MinIO S3 API on `http://localhost:9000` and the MinIO console on `http://localhost:9001`. The results directory is mounted so that CSV outputs written inside the container are immediately available on the host

## S3 configuration file

The benchmark uses a shared S3 argument file named `S3_requirement.txt`. Its current content is:

```txt
--endpoint-url http://localhost:9000
--bucket ccbd
--region-name us-east-1
--access-key minioadmin
--secret-key minioadmin123
```

This file is passed directly to `bench.py` with the `@` syntax supported by the parser. The script already enables argument-file parsing through `fromfile_prefix_chars='@'`, which is why commands such as `python bench.py @S3_requirement.txt @S_small.txt ...` work.

## TXT parameter files

Each dataset size and layout now has its own `.txt` file containing the benchmark arguments. This simplifies execution and avoids repeating long command lines.

Typical usage is:

```bash
python bench.py @S3_requirement.txt @S_small.txt --results-csv results/results_s_small.csv
```

This merges the shared S3 connection settings from `S3_requirement.txt` with the benchmark parameters defined in `S_small.txt`, then writes the output to `results/results_small_small.csv`.

## Running the benchmark

Run one command per dataset size and layout.

### Small-files layout

```bash
python bench.py @S3_requirement.txt @S_small.txt --results-csv results/results_s_small.csv
python bench.py @S3_requirement.txt @M_small.txt --results-csv results/results_m_small.csv
python bench.py @S3_requirement.txt @L_small.txt --results-csv results/results_l_small.csv
```

### Compact layout

```bash
python bench.py @S3_requirement.txt @S_compact.txt --results-csv results/results_s_compact.csv
python bench.py @S3_requirement.txt @M_compact.txt --results-csv results/results_m_compact.csv
python bench.py @S3_requirement.txt @L_compact.txt --results-csv results/results_l_compact.csv
```

These commands keep the S3 connection settings centralized in one file and keep each benchmark configuration in its own dedicated parameter file.

## Benchmark behavior

The benchmark can:
1. generate a small-files dataset locally,
2. compact it locally when needed,
3. upload the selected layout to MinIO/S3,
4. measure listing time,
5. run a fixed query directly on S3,
6. download the uploaded objects back locally,
7. append the results to the requested CSV file.

The benchmark query filters on:
- `region = tollgate_a1_geneva`
- `2025-01-15T00:00:00+00:00 <= ts < 2025-02-15T00:00:00+00:00`
- group by `event_type`, with count and average of `value`.

## Output files

The benchmark writes one CSV row per tested layout to the file passed through `--results-csv`. Typical outputs include:

- `results/results_s_small.csv`
- `results/results_m_small.csv`
- `results/results_l_small.csv`
- `results/results_s_compact.csv`
- `results/results_m_compact.csv`
- `results/results_l_compact.csv`

The workflow also uses the `.txt` files as reusable command definitions rather than as result files.

If the results directory is not mounted as a volume, files can still be copied out of the container with:

```bash
docker cp <container_id>:/opt/CCBD_Project/results/results_medium.csv .
```

## Reproducing the analysis

To reproduce the reported figures and summary tables:
1. build and start the Docker container,
2. verify that MinIO is reachable,
3. run the six benchmark commands shown above,
4. confirm that the CSV outputs are written into `results/`,
5. open `analysis.ipynb` and run all cells.

The notebook reads the benchmark outputs, sorts runs by dataset size, computes speedups and percentage reductions, and generates the plots used in the report.

## Notes

- The synthetic dataset models tollgate traffic events with columns `ts`, `user_id`, `region`, `event_type`, and `value`.
- The Parquet files are written with `compression="none"`.
- The benchmark directly queries Parquet data on S3 using PyArrow dataset filtering and aggregation.
- The compact layout is produced from the small layout using a configurable compaction ratio.

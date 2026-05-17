Authors : Tanguy Godat & Tim Gouvernon --Variant 3

# CCBD_Project
CCBD Projet variant 3

[Gdoc Planner](https://docs.google.com/document/d/1O7DRiCNgyTZn5gqpeT01s45ZBMVxIXkuG_LP3JHQOes/edit?usp=sharing)

# Variant 3 — Small files problem & compaction
Goal. Demonstrate and quantify the small files problem in object storage data lakes: too many tiny
objects can drastically increase overhead (listing, metadata, open/close costs) and slow down scans. Then
implement a compaction step to mitigate it.
What you must implement.
  - Produce two curated Parquet datasets with the same contents:
    – Small-files layout: many small Parquet objects (e.g., thousands).
    – Compact layout: fewer, larger Parquet objects (e.g., tens to hundreds).
  - Implement a compaction script that takes the small-files layout as input and rewrites it into a compact layout (still Parquet).
  - Implement the fixed analytics query on both layouts using pyarrow.dataset.
Experiments (run for S/M/L).
  - Listing time vs number of objects (small vs compact).
  - Query runtime (small vs compact).
  - End-to-end pipeline time: generation → upload → query (optional but encouraged).
Expected discussion. Explain why too many files hurt, and provide a practical rule-of-thumb for file
sizing (in your context). Discuss trade-offs: compaction cost, update frequency, and when compaction is
worth it.

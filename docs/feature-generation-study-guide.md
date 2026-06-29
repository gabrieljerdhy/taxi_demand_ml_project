# Feature Generation Study Guide

This note is a quick memory aid for how this project turns raw NYC taxi rides into model-ready features and targets.

## Big Picture

The feature pipeline has 3 main stages:

1. Load and validate raw ride records.
2. Convert rides into an hourly time series per pickup location.
3. Slice each location's time series into supervised learning examples.

In code, that flow is:

```python
from src.pipelines.features.validate import load_raw_data
from src.pipelines.features.transform_raw_to_ts import transform_raw_data_into_ts_data
from src.pipelines.features.transform_ts_to_features import (
    transform_ts_data_into_features_and_target,
)

rides = load_raw_data(year=2025)
ts_data = transform_raw_data_into_ts_data(rides)
features, target = transform_ts_data_into_features_and_target(
    ts_data,
    input_seq_len=24 * 28,
    step_size=24,
)
```

## Stage 1: Raw Data Loading and Validation

Main file: `src/pipelines/features/validate.py`

### What happens

- `load_raw_data(year, months=None)` reads local parquet files from `data/raw/`.
- If a monthly parquet file is missing, it tries to download it through `src/pipelines/features/extract.py`.
- It keeps only these raw columns:
  - `pickup_datetime`
  - `pickup_location_id`
- `validate_raw_data(rides, year, month)` removes rows whose pickup timestamp falls outside the requested month.

### Column contract after validation

The validated rides dataframe should contain:

- `pickup_datetime`
- `pickup_location_id`

### Mental model

At this point, each row is still one ride.

### Example dataframe preview

```text
       pickup_datetime  pickup_location_id
0  2025-01-01 00:05:00                  43
1  2025-01-01 00:17:00                  43
2  2025-01-01 00:42:00                 116
3  2025-01-01 01:03:00                  43
4  2025-01-01 01:18:00                 116
```

How to read it:

- each row is one taxi ride
- timestamps are still at the original ride level
- multiple rows can share the same hour and location

## Stage 2: Raw Rides to Hourly Time Series

Main file: `src/pipelines/features/transform_raw_to_ts.py`

### What happens

`transform_raw_data_into_ts_data(rides)` does two important things:

1. It floors each pickup timestamp to the hour:

```python
rides["pickup_hour"] = rides["pickup_datetime"].dt.floor("h")
```

2. It counts rides per:
   - `pickup_hour`
   - `pickup_location_id`

This produces hourly demand counts:

- `pickup_hour`
- `pickup_location_id`
- `rides`

### Why `add_missing_slots()` matters

Real ride data has gaps. Some location-hour combinations do not appear because no rides happened there.

`add_missing_slots(ts_data)` fills those missing combinations with `rides = 0` so the model sees a complete hourly sequence.

It does this by:

- building a full hourly range from the minimum to maximum hour in the data
- looping over location IDs
- reindexing each location's hourly series onto the full hourly range
- filling missing hours with zero rides

It even handles locations with no rows in the aggregated data by inserting a dummy zero row first, then reindexing.

### Column contract after time-series conversion

The time-series dataframe should contain:

- `pickup_hour`
- `pickup_location_id`
- `rides`

### Mental model

At this point, each row is one location at one hour, with the ride count for that hour.

### Example dataframe preview

```text
          pickup_hour  pickup_location_id  rides
0 2025-01-01 00:00:00                  43      2
1 2025-01-01 01:00:00                  43      1
2 2025-01-01 02:00:00                  43      0
3 2025-01-01 00:00:00                 116      1
4 2025-01-01 01:00:00                 116      1
```

How to read it:

- rides have been aggregated to hourly counts
- missing location-hour combinations are present with `rides = 0`
- this is the dataframe used to build lag features

## Stage 3: Time Series to Features and Target

Main file: `src/pipelines/features/transform_ts_to_features.py`

### What happens

`transform_ts_data_into_features_and_target(ts_data, input_seq_len, step_size)` converts each location's hourly series into sliding-window training examples.

For each `pickup_location_id`, it:

1. sorts rows by `pickup_hour`
2. takes `input_seq_len` hours of ride history as features
3. uses the immediately following hour as the target
4. shifts the window forward by `step_size`

### Core idea

If:

- `input_seq_len = 24 * 28`, the model uses the previous 28 days of hourly ride counts
- `step_size = 24`, a new training example starts every 24 hours

So the project is not using only the latest hour. It is using a whole block of past hourly ride counts.

## How the Sliding Window Works

The helper `get_cutoff_indices_features_and_target()` builds tuples like:

```python
(subseq_first_idx, subseq_mid_idx, subseq_last_idx)
```

Interpret them like this:

- `subseq_first_idx:subseq_mid_idx` = feature window
- `subseq_mid_idx:subseq_last_idx` = one-row target window

Inside the main loop:

```python
x[i, :] = ts_data_one_location.iloc[idx[0]:idx[1]]["rides"].values
y[i] = ts_data_one_location.iloc[idx[1]:idx[2]]["rides"].values[0]
pickup_hours.append(ts_data_one_location.iloc[idx[1]]["pickup_hour"])
```

So:

- features are the ride counts from the previous `input_seq_len` hours
- target is the ride count for the next hour after that history block
- `pickup_hour` stored in the features dataframe is the prediction hour, not a history hour

## Feature Columns

The ride-history columns are created like this:

```python
[f"rides_previous_{i+1}_hour" for i in reversed(range(input_seq_len))]
```

That means the feature columns are named:

- `rides_previous_N_hour`
- `rides_previous_(N-1)_hour`
- ...
- `rides_previous_1_hour`

Where:

- `rides_previous_N_hour` is the oldest hour in the input window
- `rides_previous_1_hour` is the most recent hour before the prediction hour

The final features dataframe also includes:

- `pickup_hour`
- `pickup_location_id`

## Target

The returned target is a pandas `Series` named:

- `target_rides_next_hour`

This is the ride count for the hour identified by the feature row's `pickup_hour`.

### Example dataframe preview

Features dataframe:

```text
   rides_previous_3_hour  rides_previous_2_hour  rides_previous_1_hour  \
0                   10.0                   12.0                   15.0
1                   12.0                   15.0                   11.0

          pickup_hour  pickup_location_id
0 2025-01-01 03:00:00                  43
1 2025-01-01 04:00:00                  43
```

Target series:

```text
0    11.0
1     9.0
Name: target_rides_next_hour, dtype: float32
```

How to read it:

- one row now represents one training example
- lag columns are the past ride counts used as inputs
- `pickup_hour` is the hour being predicted
- the target is the ride count for that prediction hour

## Worked Example

Imagine one location has these hourly ride counts:

```text
Hour 1  -> 10
Hour 2  -> 12
Hour 3  -> 15
Hour 4  -> 11
```

If:

- `input_seq_len = 3`
- `step_size = 1`

Then the first training example is:

- features:
  - `rides_previous_3_hour = 10`
  - `rides_previous_2_hour = 12`
  - `rides_previous_1_hour = 15`
- target:
  - `target_rides_next_hour = 11`
- `pickup_hour`:
  - Hour 4

## Shapes to Remember

After stage 3:

- `features` is a dataframe with:
  - many lag columns
  - `pickup_hour`
  - `pickup_location_id`
- `target` is a series with one value per feature row

Each feature row answers:

> Given the previous hourly ride counts for this location, how many rides will happen at this `pickup_hour`?

## Fast Recall Summary

Use this when you want the shortest possible reminder:

- Raw parquet -> keep pickup timestamp and pickup zone only.
- Validate rows so each file contains only rides from its intended month.
- Floor pickup timestamps to the hour.
- Group by hour and location to count rides.
- Fill missing hour-location combinations with `0`.
- For each location, build sliding windows over hourly `rides`.
- History window becomes features.
- Next hour becomes target.
- Add `pickup_hour` and `pickup_location_id` to each feature row.

## Files to Revisit When Studying

- `src/pipelines/features/extract.py`
- `src/pipelines/features/validate.py`
- `src/pipelines/features/transform_raw_to_ts.py`
- `src/pipelines/features/transform_ts_to_features.py`

Notebook versions of the same story:

- `notebooks/01_load_and_validate_raw_data.ipynb`
- `notebooks/02_transform_raw_data_into_ts_data.ipynb`
- `notebooks/03_transform_ts_data_intro_features_and_targets.ipynb`
- `notebooks/04_transform_raw_data_into_features_and_targets.ipynb`

## One-Line Memory Hook

The project predicts ride demand for a location-hour by turning past hourly ride counts into lag features and using the next hour's ride count as the target.

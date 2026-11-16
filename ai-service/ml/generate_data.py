"""Generate a reproducible synthetic parking-duration dataset."""

from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_PATH = Path(__file__).resolve().parent / "parking_history.csv"
RANDOM_SEED = 42
ROW_COUNT = 2_000


def generate_data(row_count: int = ROW_COUNT, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Create parking visits with vehicle- and arrival-dependent durations."""
    rng = np.random.default_rng(seed)
    vehicle_types = rng.choice(
        ["bike", "car", "suv"],
        size=row_count,
        p=[0.32, 0.52, 0.16],
    )
    weekday = rng.integers(0, 7, size=row_count)

    arrival_hour = rng.integers(0, 24, size=row_count)
    office_arrivals = rng.random(row_count) < 0.62
    arrival_hour[office_arrivals] = rng.integers(8, 18, size=office_arrivals.sum())

    shape_and_scale = {
        "bike": (2.2, 18.0),
        "car": (3.4, 38.0),
        "suv": (3.6, 43.0),
    }
    duration_min = np.empty(row_count, dtype=float)
    for vehicle_type, (shape, scale) in shape_and_scale.items():
        vehicle_mask = vehicle_types == vehicle_type
        duration_min[vehicle_mask] = rng.gamma(
            shape=shape,
            scale=scale,
            size=vehicle_mask.sum(),
        )

    is_weekday_office_arrival = (
        (weekday < 5) & (arrival_hour >= 8) & (arrival_hour < 18)
    )
    duration_min += is_weekday_office_arrival * rng.uniform(25, 55, size=row_count)
    duration_min = np.clip(np.rint(duration_min), 5, 720).astype(int)

    return pd.DataFrame(
        {
            "vehicle_type": vehicle_types,
            "arrival_hour": arrival_hour,
            "weekday": weekday,
            "duration_min": duration_min,
        }
    )


def main() -> None:
    data = generate_data()
    data.to_csv(OUTPUT_PATH, index=False)
    print(f"Generated {len(data):,} parking visits: {OUTPUT_PATH}")
    print(f"Average stay: {data['duration_min'].mean():.1f} minutes")
    print("Average duration by vehicle type:")
    print(data.groupby("vehicle_type")["duration_min"].mean().round(1).to_string())


if __name__ == "__main__":
    main()

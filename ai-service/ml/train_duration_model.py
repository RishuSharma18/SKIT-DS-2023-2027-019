"""Train and evaluate the first parking-duration recommendation model."""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split


ML_DIR = Path(__file__).resolve().parent
DATA_PATH = ML_DIR / "parking_history.csv"
MODEL_PATH = ML_DIR / "models" / "duration.joblib"
METRICS_PATH = ML_DIR / "models" / "duration_metrics.json"
TARGET = "duration_min"
FEATURE_COLUMNS = [
    "arrival_hour",
    "weekday",
    "vehicle_type_bike",
    "vehicle_type_car",
    "vehicle_type_suv",
]


def main() -> None:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Training data not found at {DATA_PATH}. "
            "Run generate_data.py first."
        )

    data = pd.read_csv(DATA_PATH)
    required_columns = {"vehicle_type", "arrival_hour", "weekday", TARGET}
    missing_columns = required_columns.difference(data.columns)
    if missing_columns:
        raise ValueError(f"Dataset is missing columns: {', '.join(sorted(missing_columns))}")

    features = pd.get_dummies(
        data[["vehicle_type", "arrival_hour", "weekday"]],
        columns=["vehicle_type"],
        dtype=int,
    ).reindex(columns=FEATURE_COLUMNS, fill_value=0)
    target = data[TARGET]
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=42,
    )

    model = RandomForestRegressor(
        n_estimators=300,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)
    model_mae = mean_absolute_error(y_test, model.predict(x_test))

    mean_prediction = float(y_train.mean())
    baseline_mae = mean_absolute_error(
        y_test,
        [mean_prediction] * len(y_test),
    )

    print(f"Random forest test MAE: {model_mae:.2f} minutes")
    print(f"Mean-only baseline MAE: {baseline_mae:.2f} minutes")
    print(f"MAE improvement: {baseline_mae - model_mae:.2f} minutes")

    if model_mae >= baseline_mae:
        raise RuntimeError(
            "The trained model did not beat the mean-only baseline. "
            "Review the generated data and features before using this model."
        )

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METRICS_PATH.write_text(
        json.dumps(
            {
                "trainingRows": len(data),
                "testRows": len(y_test),
                "testMaeMin": round(float(model_mae), 2),
                "baselineMaeMin": round(float(baseline_mae), 2),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Saved model: {MODEL_PATH}")
    print(f"Saved evaluation metrics: {METRICS_PATH}")


if __name__ == "__main__":
    main()

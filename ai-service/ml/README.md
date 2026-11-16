# Parking duration model (prototype)

This prototype estimates how long a vehicle may occupy a parking space. The
synthetic dataset is for validating the training workflow only; it is not
representative of measured facility traffic.

From `ai-service/`, create and activate a virtual environment, then install
the machine-learning dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install pandas scikit-learn joblib
```

Generate 2,000 deterministic sample visits and train/evaluate the random
forest against a mean-only test-set baseline:

```powershell
python ml\generate_data.py
python ml\train_duration_model.py
```

The CSV is written to `ml/parking_history.csv`; the trained estimator is
written to `ml/models/duration.joblib`. The model accepts the one-hot encoded
vehicle type plus arrival hour and weekday features. The lower-MAE check is
enforced by the training script. This is a prototype metric on synthetic data,
not evidence of real-world predictive accuracy.

The next allocation experiment can use predicted durations to prefer
exit-adjacent spaces for short stays, while reserving farther spaces for
vehicles predicted to stay longer.

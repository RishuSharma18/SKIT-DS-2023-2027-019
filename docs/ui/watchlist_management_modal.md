# Watchlist Management Modal & Input Validation

Modal design specifications for registering and editing stolen or wanted vehicle plates.

## Field Constraints
- License Plate: Auto-uppercased, spaces stripped, validated against regex `^[A-Z0-9]{5,10}$`.
- Reason: Required text selection (`STOLEN`, `WANTED`, `VIOLATION`, `OTHER`).
- Notes: Freeform text area for FIR numbers or investigation notes.

# Project Plan

Source: Form-1, Form-2, proposal PDF and PPT. Sprint names and owners follow Form-2.

## Team and ownership
| Member | Role | Main folders |
|---|---|---|
| Vaibhav Soni (lead) | Backend, DB, integration, deployment | `backend/` |
| Rishu Sharma | CCTV feed, YOLOv8 detection, classification, tracking | `ai-service/app/pipeline.py` |
| Nandani Rathore | Plate OCR, watchlist matching, alerts | `ai-service/app/plate_reader.py`, backend watchlist/alerts |
| Bhumi Porwal | Dashboard, slot allocation ML, violation detection | `frontend/`, `backend/src/services/allocation.js`, slot/violation logic |

## Phases
| # | Phase | Deliverable (definition of done) |
|---|---|---|
| 0 | Setup | Repo scaffold pushed, everyone runs the quick start, sample video collected |
| 1 | Vehicle detection | YOLOv8 + tracker draws boxes/IDs on sample video; COCO class → motorcycle/car (SUVs are not separate) |
| 2 | Plate recognition | Plate crops → EasyOCR → normalised plate; accuracy measured on 50+ crops |
| 3 | Backend | All endpoints + models working; `curl` events update DB and dashboard |
| 4 | Slots + dashboard | Slot polygons, occupancy, slot recommendation, live dashboard |
| 5 | Violations + ML | Wrong parking, overstay, crash heuristic; slot ML trained on logged history |
| 6 | Integration and testing | End-to-end on 3+ videos; bug-fix list closed |
| 7 | Deployment and report | Demo deployment, final report, research paper draft (Form-1 external evaluation) |

## Current status (2026-11-16)
- Crash detection has a first-pass prototype in `ai-service/app/crash.py`. It emits a backend crash event, stores both track IDs on the high-severity alert, and displays the IDs in the dashboard.
- Synthetic-data tests cover collision detection, negative cases, duplicate suppression, and the backend event contract (`cd ai-service && python tests_crash.py`; `cd backend && npm test`).
- This heuristic has not yet been validated against real crash footage and may produce false positives; treat alerts as possible collisions, not confirmed crashes.

## Feature to implementation map
| Feature (PPT) | How it is built | Where |
|---|---|---|
| Smart slot allocation | Vehicle category from YOLO class and bbox size; first free slot that fits | `allocation.js`, `slots.py` |
| Check-in / check-out | A confirmed stationary track inside a configured bay creates a session; leaving the bay closes it | `pipeline.py`, `events.js` |
| Stolen vehicle detection | EasyOCR → normalise → vote → watchlist lookup → alert | `plate_reader.py`, `events.js` |
| Crash detection | Heuristic first (box overlap + sudden speed drop), ML later | new `ai-service/app/crash.py` |
| Wrong parking | Backend alert contract exists; automatic detection needs a configured lot boundary and is not emitted from bay polygons alone | `events.js` |
| ML parking optimisation | Log sessions; train a simple model (e.g. scikit-learn) on slot/vehicle/duration | `ai-service/ml/` (Bhumi, Phase 5) |

## Honest technical notes (good for viva and report)
- COCO has no separate "SUV" class. The detector treats SUVs as cars rather than mislabeling buses, trucks, or perspective-sized cars. Use a model trained with a dedicated SUV class if that distinction is required.
- The sample slot map covers five spaces in one prerecorded camera view. It is not a map or live occupancy reading for a real facility; configure a live camera and draw that facility's spaces first.
- Plate OCR needs a camera that sees plates clearly. Plan to fine-tune or add a plate-detector (YOLO trained on a plate dataset) if EasyOCR on whole-vehicle crops is weak.
- TensorFlow is listed in the PPT. It is only needed if you build the slot/crash ML model in TF; scikit-learn or PyTorch (already pulled by ultralytics) are lighter. Decide in Phase 5.
- DB: The active backend in `backend/app` uses SQLAlchemy with PostgreSQL (or SQLite for local fallback); the retained `backend/src` legacy service uses MongoDB. Align the proposal and mentor-facing documents with the active service.
- Crash detection from plain CCTV is the hardest feature; keep it as a heuristic with a clear "prototype" label.
- No public dataset is perfect; record your own parking-lot clips (phone from a height) plus public clips for testing.

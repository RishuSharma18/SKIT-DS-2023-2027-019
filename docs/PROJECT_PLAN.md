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
| 1 | Vehicle detection | YOLOv8 + tracker draws boxes/IDs on sample video; class → bike/car/suv |
| 2 | Plate recognition | Plate crops → EasyOCR → normalised plate; accuracy measured on 50+ crops |
| 3 | Backend | All endpoints + models working; `curl` events update DB and dashboard |
| 4 | Slots + dashboard | Slot polygons, occupancy, slot recommendation, live dashboard |
| 5 | Violations + ML | Wrong parking, overstay, crash heuristic; slot ML trained on logged history |
| 6 | Integration and testing | End-to-end on 3+ videos; bug-fix list closed |
| 7 | Deployment and report | Demo deployment, final report, research paper draft (Form-1 external evaluation) |

## Feature to implementation map
| Feature (PPT) | How it is built | Where |
|---|---|---|
| Smart slot allocation | Vehicle category from YOLO class and bbox size; first free slot that fits | `allocation.js`, `slots.py` |
| Check-in / check-out | Track confirmed N frames = entry; missing N frames = exit; duration computed | `pipeline.py`, `events.js` |
| Stolen vehicle detection | EasyOCR → normalise → vote → watchlist lookup → alert | `plate_reader.py`, `events.js` |
| Crash detection | Heuristic first (box overlap + sudden speed drop), ML later | new `ai-service/app/crash.py` |
| Wrong parking | Stationary N seconds and not inside any valid slot polygon | `pipeline.py` |
| ML parking optimisation | Log sessions; train a simple model (e.g. scikit-learn) on slot/vehicle/duration | `ai-service/ml/` (Bhumi, Phase 5) |

## Honest technical notes (good for viva and report)
- COCO has no "SUV" class. SUV is inferred from truck/bus class or large car bbox. Threshold is `SUV_AREA_RATIO`; tune it per camera.
- Plate OCR needs a camera that sees plates clearly. Plan to fine-tune or add a plate-detector (YOLO trained on a plate dataset) if EasyOCR on whole-vehicle crops is weak.
- TensorFlow is listed in the PPT. It is only needed if you build the slot/crash ML model in TF; scikit-learn or PyTorch (already pulled by ultralytics) are lighter. Decide in Phase 5.
- DB: Form-1 says MySQL, proposal/Form-2 say MongoDB. The scaffold uses MongoDB; tell your mentor so the documents match.
- Crash detection from plain CCTV is the hardest feature; keep it as a heuristic with a clear "prototype" label.
- No public dataset is perfect; record your own parking-lot clips (phone from a height) plus public clips for testing.

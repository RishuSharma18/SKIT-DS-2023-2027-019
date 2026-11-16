"""Plate normalization/voting checks without loading the EasyOCR model."""
from app.ocr.plate_reader import PlateVoteBuffer, normalize


assert normalize("RJ14 AB 1234") == "RJ14AB1234"
assert normalize("RJ14AB12O4") == "RJ14AB1204"
assert normalize("hello") is None

votes = PlateVoteBuffer(max_frames=5, min_votes=3)
assert votes.add(7, "RJ14AB1234", 0.8) is None
assert votes.add(7, "RJ14AB1234", 0.9) is None
assert votes.add(7, "RJ14AB1234", 1.0) == ("RJ14AB1234", 0.9)
votes.forget(7)
assert votes.add(7, "RJ14AB1234", 1.0) is None
print("plate normalization and temporal voting OK")

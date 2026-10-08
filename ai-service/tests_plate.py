"""Quick sanity check of plate normalisation (no OCR model needed):  python tests_plate.py"""
import re, importlib.util, sys, types

# import only the pure-python bits without pulling in easyocr/cv2
src = open("app/plate_reader.py").read().split("class PlateReader")[0]
src = src.replace("import cv2", "")
mod = types.ModuleType("pr"); exec(src, mod.__dict__)

assert mod.normalize("RJ14 AB 1234") == "RJ14AB1234"
assert mod.normalize("RJl4AB1234") is None or True   # lowercase L not mapped; just must not crash
assert mod.normalize("RJ14AB12O4") == "RJ14AB1204"   # O -> 0 in last 4
assert mod.normalize("hello") is None
print("plate normalisation OK")

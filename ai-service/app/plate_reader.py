"""Compatibility imports for the modular OCR package."""
from .ocr.plate_reader import PLATE_RE, PlateReader, PlateVoteBuffer, normalize

__all__ = ["PLATE_RE", "PlateReader", "PlateVoteBuffer", "normalize"]

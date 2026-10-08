"""Headless/dev runner:  python run_pipeline.py [--show]"""
import sys
import cv2
from app.pipeline import Pipeline

show = "--show" in sys.argv
for frame in Pipeline().run():
    if show:
        cv2.imshow("Smart CCTV", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
cv2.destroyAllWindows()

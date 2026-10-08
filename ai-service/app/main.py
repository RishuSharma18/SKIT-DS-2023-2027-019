"""FastAPI wrapper: /health and /stream (MJPEG preview for the dashboard)."""
import cv2
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from .pipeline import Pipeline

app = FastAPI(title="Smart CCTV AI Service")


@app.get("/health")
def health():
    return {"ok": True}


def _mjpeg():
    for frame in Pipeline().run():
        ok, buf = cv2.imencode(".jpg", frame)
        if ok:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")


@app.get("/stream")
def stream():
    return StreamingResponse(_mjpeg(), media_type="multipart/x-mixed-replace; boundary=frame")

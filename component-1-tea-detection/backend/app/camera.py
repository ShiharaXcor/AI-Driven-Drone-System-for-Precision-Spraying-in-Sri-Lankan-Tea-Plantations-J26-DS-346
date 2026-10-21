import logging
import threading
import cv2
from . import config
from .db import Session, Alert
from .services import STATE, relay, gps

log = logging.getLogger("camera")


class CameraLoop:
    def __init__(self):
        self.thread = None
        self.stop_evt = threading.Event()
        self.running = False
        self.frames = 0
        self.last_error = None
        self.last_result = None

    def status(self):
        return {"running": self.running, "frames": self.frames,
                "last_error": self.last_error, "last_result": self.last_result}

    def start(self, index=None, interval=None):
        if self.running:
            return
        self.index = config.CAMERA_INDEX if index is None else index
        self.interval = config.CAMERA_INTERVAL_S if interval is None else interval
        self.stop_evt.clear()
        self.frames, self.last_error = 0, None
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_evt.set()
        if self.thread:
            self.thread.join(timeout=5)
        self.running = False

    def _fail_safe(self, message):
        """Camera lost: spray OFF (unless the operator forced it ON), and raise a warning once."""
        if self.last_error != message:
            p = gps.read()
            with Session() as s:
                s.add(Alert(priority="warning", message=message, lat=p["lat"], lon=p["lon"]))
                s.commit()
        self.last_error = message
        if STATE["manual"] != "ON":
            relay.set(False)

    def _run(self):
        from .pipeline import run_pipeline
        cap = cv2.VideoCapture(self.index)
        try:
            if not cap.isOpened():
                self._fail_safe(f"Cannot open camera {self.index}")
                return
            while not self.stop_evt.is_set():
                ok, frame = cap.read()
                if not ok:
                    self._fail_safe("Camera read failed")
                else:
                    try:
                        r = run_pipeline(frame)
                        self.last_result = {k: r[k] for k in ("event_id", "decision", "reason", "spray_status")}
                        self.frames += 1
                        self.last_error = None
                    except Exception as e:
                        log.exception("Pipeline error")
                        self._fail_safe(f"Pipeline error: {e}")
                self.stop_evt.wait(self.interval)
        finally:
            cap.release()
            if STATE["manual"] != "ON":
                relay.set(False)             # loop ended: spray OFF
            self.running = False


camera = CameraLoop()
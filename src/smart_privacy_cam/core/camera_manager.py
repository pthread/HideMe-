from __future__ import annotations

from dataclasses import dataclass
import cv2


@dataclass
class CameraInfo:
    index: int
    name: str


def detect_cameras(max_devices: int = 10) -> list[CameraInfo]:
    cameras: list[CameraInfo] = []
    for index in range(max_devices):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                cameras.append(CameraInfo(index=index, name=f"Camera {index}"))
        cap.release()
    return cameras


def open_camera(index: int, width: int, height: int, fps: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    return cap

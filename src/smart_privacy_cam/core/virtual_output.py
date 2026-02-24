from __future__ import annotations

import cv2
import numpy as np
import pyvirtualcam
import platform


class VirtualOutput:
    def __init__(self, width: int, height: int, fps: int) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.cam: pyvirtualcam.Camera | None = None
        self.device: str = ""
        self.backend: str = ""

    def start(self) -> None:
        if self.cam is not None:
            return

        backends = [None]
        if platform.system().lower().startswith("win"):
            backends = ["obs", "unitycapture", None]

        last_error: Exception | None = None
        for backend in backends:
            try:
                if backend is None:
                    self.cam = pyvirtualcam.Camera(width=self.width, height=self.height, fps=self.fps)
                else:
                    self.cam = pyvirtualcam.Camera(
                        width=self.width,
                        height=self.height,
                        fps=self.fps,
                        backend=backend,
                    )
                self.device = self.cam.device
                self.backend = backend or "auto"
                return
            except Exception as exc:
                last_error = exc

        raise RuntimeError(
            "Не удалось создать виртуальную камеру. Установите/включите OBS Virtual Camera "
            "(OBS > Tools > Virtual Camera) или UnityCapture и перезапустите приложение."
        ) from last_error

    def send(self, frame_bgr: np.ndarray) -> None:
        if self.cam is None:
            return
        if frame_bgr.shape[1] != self.width or frame_bgr.shape[0] != self.height:
            frame_bgr = cv2.resize(frame_bgr, (self.width, self.height), interpolation=cv2.INTER_LINEAR)

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frame_rgb = np.ascontiguousarray(frame_rgb)
        self.cam.send(frame_rgb)
        self.cam.sleep_until_next_frame()

    def stop(self) -> None:
        if self.cam is not None:
            self.cam.close()
            self.cam = None

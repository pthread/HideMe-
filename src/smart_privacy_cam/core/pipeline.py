from __future__ import annotations

from dataclasses import replace
import queue
import threading
from typing import Callable

import cv2
import numpy as np

from smart_privacy_cam.config import AppSettings
from smart_privacy_cam.core.background_processor import BackgroundProcessor
from smart_privacy_cam.core.camera_manager import open_camera
from smart_privacy_cam.core.face_processor import FaceProcessor
from smart_privacy_cam.core.virtual_output import VirtualOutput


PreviewCallback = Callable[[np.ndarray], None]
ErrorCallback = Callable[[str], None]


class VideoPipeline:
    def __init__(
        self,
        settings: AppSettings,
        on_preview: PreviewCallback | None = None,
        on_error: ErrorCallback | None = None,
    ) -> None:
        self._settings = settings
        self._on_preview = on_preview
        self._on_error = on_error

        self._frame_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=2)
        self._processed_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=2)

        self._stop_event = threading.Event()
        self._capture_thread: threading.Thread | None = None
        self._process_thread: threading.Thread | None = None
        self._output_thread: threading.Thread | None = None

        self._settings_lock = threading.Lock()

        self._face = FaceProcessor()
        self._background = BackgroundProcessor()
        self._output = VirtualOutput(settings.output_width, settings.output_height, settings.output_fps)

    def start(self) -> None:
        if self._capture_thread and self._capture_thread.is_alive():
            return

        self._stop_event.clear()
        self._output.start()

        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._output_thread = threading.Thread(target=self._output_loop, daemon=True)

        self._capture_thread.start()
        self._process_thread.start()
        self._output_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        for t in (self._capture_thread, self._process_thread, self._output_thread):
            if t and t.is_alive():
                t.join(timeout=1.0)
        self._output.stop()

    def update_settings(self, settings: AppSettings) -> None:
        with self._settings_lock:
            self._settings = replace(settings)

    def _snapshot_settings(self) -> AppSettings:
        with self._settings_lock:
            return replace(self._settings)

    def _capture_loop(self) -> None:
        current_camera = -1
        cap: cv2.VideoCapture | None = None

        try:
            while not self._stop_event.is_set():
                settings = self._snapshot_settings()
                if settings.camera_index != current_camera or cap is None:
                    if cap is not None:
                        cap.release()
                    cap = open_camera(
                        settings.camera_index,
                        settings.output_width,
                        settings.output_height,
                        settings.output_fps,
                    )
                    current_camera = settings.camera_index

                if cap is None or not cap.isOpened():
                    continue

                ok, frame = cap.read()
                if not ok:
                    continue

                self._put_latest(self._frame_queue, frame)
        finally:
            if cap is not None:
                cap.release()

    def _process_loop(self) -> None:
        while not self._stop_event.is_set():
            frame = self._get_with_timeout(self._frame_queue)
            if frame is None:
                continue

            settings = self._snapshot_settings()
            processed = self._face.apply(frame, settings)
            processed = self._background.apply(
                processed,
                enable_blur=settings.enable_background_blur,
                enable_replace=settings.enable_background_replace,
                blur_strength=settings.background_blur_strength,
            )
            self._put_latest(self._processed_queue, processed)

    def _output_loop(self) -> None:
        while not self._stop_event.is_set():
            frame = self._get_with_timeout(self._processed_queue)
            if frame is None:
                continue

            try:
                self._output.send(frame)
            except Exception as exc:
                self._stop_event.set()
                if self._on_error is not None:
                    self._on_error(f"Ошибка виртуальной камеры: {exc}")
                return

            if self._on_preview is not None:
                self._on_preview(frame)

    @staticmethod
    def _put_latest(q: queue.Queue[np.ndarray], frame: np.ndarray) -> None:
        if q.full():
            try:
                q.get_nowait()
            except queue.Empty:
                pass
        q.put_nowait(frame)

    @staticmethod
    def _get_with_timeout(q: queue.Queue[np.ndarray], timeout: float = 0.1) -> np.ndarray | None:
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return None

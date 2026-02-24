from __future__ import annotations

import cv2
import numpy as np
import mediapipe as mp

from smart_privacy_cam.config import AppSettings, PrivacyMode, ThirdPartyMode


class FaceProcessor:
    def __init__(self) -> None:
        face_mesh_api = self._get_face_mesh_api()
        self._mesh = face_mesh_api.FaceMesh(
            static_image_mode=False,
            max_num_faces=5,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    @staticmethod
    def _get_face_mesh_api():
        if hasattr(mp, "solutions") and hasattr(mp.solutions, "face_mesh"):
            return mp.solutions.face_mesh

        try:
            from mediapipe.python.solutions import face_mesh  # type: ignore

            return face_mesh
        except Exception as exc:
            raise RuntimeError(
                "MediaPipe Face Mesh недоступен в текущей среде. "
                "Используйте Python 3.10-3.12 и установленный пакет mediapipe."
            ) from exc

    def apply(self, frame_bgr: np.ndarray, settings: AppSettings) -> np.ndarray:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self._mesh.process(rgb)
        if not results.multi_face_landmarks:
            return frame_bgr

        output = frame_bgr.copy()
        face_boxes: list[tuple[int, int, int, int, float]] = []
        h, w = frame_bgr.shape[:2]

        for face_landmarks in results.multi_face_landmarks:
            xs = [p.x for p in face_landmarks.landmark]
            ys = [p.y for p in face_landmarks.landmark]
            zs = [p.z for p in face_landmarks.landmark]

            x1 = max(int(min(xs) * w), 0)
            y1 = max(int(min(ys) * h), 0)
            x2 = min(int(max(xs) * w), w - 1)
            y2 = min(int(max(ys) * h), h - 1)

            avg_depth = float(np.mean(zs))
            face_boxes.append((x1, y1, x2, y2, avg_depth))

        owner_idx = min(settings.owner_face_index, len(face_boxes) - 1)

        for idx, (x1, y1, x2, y2, depth) in enumerate(face_boxes):
            should_hide = self._should_hide(idx, owner_idx, settings.third_party_mode)
            if not should_hide:
                continue

            z_scale = np.clip(1.0 + abs(depth) * 4.0, 1.0, 1.8)
            output = self._apply_privacy_mask(output, x1, y1, x2, y2, z_scale, settings.privacy_mode)

        return output

    def _should_hide(self, idx: int, owner_idx: int, mode: ThirdPartyMode) -> bool:
        if mode == ThirdPartyMode.HIDE_ALL:
            return True
        if mode == ThirdPartyMode.HIDE_OWNER:
            return idx == owner_idx
        if mode == ThirdPartyMode.HIDE_OTHERS:
            return idx != owner_idx
        return False

    def _apply_privacy_mask(
        self,
        image: np.ndarray,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        z_scale: float,
        mode: PrivacyMode,
    ) -> np.ndarray:
        h, w = image.shape[:2]
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        bw = int((x2 - x1) * z_scale)
        bh = int((y2 - y1) * z_scale)

        nx1 = max(cx - bw // 2, 0)
        ny1 = max(cy - bh // 2, 0)
        nx2 = min(cx + bw // 2, w - 1)
        ny2 = min(cy + bh // 2, h - 1)

        if nx2 <= nx1 or ny2 <= ny1:
            return image

        roi = image[ny1:ny2, nx1:nx2]

        if mode == PrivacyMode.SQUARE_2D:
            image[ny1:ny2, nx1:nx2] = (0, 0, 0)
            return image

        blur = cv2.GaussianBlur(roi, (51, 51), 0)
        image[ny1:ny2, nx1:nx2] = blur
        return image

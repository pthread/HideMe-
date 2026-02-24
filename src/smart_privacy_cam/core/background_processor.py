from __future__ import annotations

import cv2
import numpy as np
import mediapipe as mp


class BackgroundProcessor:
    def __init__(self) -> None:
        selfie_segmentation_api = self._get_selfie_segmentation_api()
        self._segmenter = selfie_segmentation_api.SelfieSegmentation(model_selection=1)

    @staticmethod
    def _get_selfie_segmentation_api():
        if hasattr(mp, "solutions") and hasattr(mp.solutions, "selfie_segmentation"):
            return mp.solutions.selfie_segmentation

        try:
            from mediapipe.python.solutions import selfie_segmentation  # type: ignore

            return selfie_segmentation
        except Exception as exc:
            raise RuntimeError(
                "MediaPipe Selfie Segmentation недоступен в текущей среде. "
                "Используйте Python 3.10-3.12 и установленный пакет mediapipe."
            ) from exc

    def apply(
        self,
        frame_bgr: np.ndarray,
        enable_blur: bool,
        enable_replace: bool,
        blur_strength: int,
    ) -> np.ndarray:
        if not enable_blur and not enable_replace:
            return frame_bgr

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self._segmenter.process(rgb)
        if result.segmentation_mask is None:
            return frame_bgr

        mask = result.segmentation_mask > 0.5
        output = frame_bgr.copy()

        if enable_blur:
            k = blur_strength if blur_strength % 2 == 1 else blur_strength + 1
            blurred = cv2.GaussianBlur(frame_bgr, (k, k), 0)
            output[~mask] = blurred[~mask]

        if enable_replace:
            replacement = np.zeros_like(frame_bgr)
            replacement[:, :] = (30, 30, 30)
            output[~mask] = replacement[~mask]

        return output

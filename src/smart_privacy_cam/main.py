from pathlib import Path
import sys

from smart_privacy_cam.ui.app import SmartPrivacyApp


def run() -> None:
    if sys.version_info < (3, 10) or sys.version_info >= (3, 13):
        raise RuntimeError("Smart Privacy Cam требует Python 3.10-3.12 (совместимость MediaPipe).")

    presets_path = Path("data/presets.json")
    app = SmartPrivacyApp(presets_path=presets_path)
    app.mainloop()

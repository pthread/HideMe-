from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import json


class PrivacyMode(str, Enum):
    SQUARE_2D = "square_2d"
    BLUR_3D = "blur_3d"


class ThirdPartyMode(str, Enum):
    HIDE_OTHERS = "hide_others"
    HIDE_OWNER = "hide_owner"
    HIDE_ALL = "hide_all"


@dataclass
class AppSettings:
    camera_index: int = 0
    owner_face_index: int = 0
    privacy_mode: PrivacyMode = PrivacyMode.BLUR_3D
    third_party_mode: ThirdPartyMode = ThirdPartyMode.HIDE_OTHERS
    enable_background_blur: bool = False
    enable_background_replace: bool = False
    background_blur_strength: int = 25
    output_width: int = 1280
    output_height: int = 720
    output_fps: int = 30

    def __post_init__(self) -> None:
        if isinstance(self.privacy_mode, str):
            self.privacy_mode = PrivacyMode(self.privacy_mode)
        if isinstance(self.third_party_mode, str):
            self.third_party_mode = ThirdPartyMode(self.third_party_mode)


@dataclass
class Preset:
    name: str
    settings: AppSettings


DEFAULT_PRESETS = [
    Preset(
        name="Максимальная анонимность",
        settings=AppSettings(
            privacy_mode=PrivacyMode.BLUR_3D,
            third_party_mode=ThirdPartyMode.HIDE_ALL,
            enable_background_blur=True,
        ),
    ),
    Preset(
        name="Легкий цензор",
        settings=AppSettings(
            privacy_mode=PrivacyMode.SQUARE_2D,
            third_party_mode=ThirdPartyMode.HIDE_OTHERS,
            enable_background_blur=False,
        ),
    ),
]


def load_presets(path: Path) -> list[Preset]:
    if not path.exists():
        save_presets(path, DEFAULT_PRESETS)
        return DEFAULT_PRESETS

    raw = json.loads(path.read_text(encoding="utf-8"))
    presets: list[Preset] = []
    for item in raw:
        settings = AppSettings(**item["settings"])
        presets.append(Preset(name=item["name"], settings=settings))
    return presets


def save_presets(path: Path, presets: list[Preset]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"name": p.name, "settings": asdict(p.settings)} for p in presets]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import threading
from tkinter import messagebox

import customtkinter as ctk
import cv2
from PIL import Image

from smart_privacy_cam.config import (
    AppSettings,
    Preset,
    PrivacyMode,
    ThirdPartyMode,
    load_presets,
)
from smart_privacy_cam.core.camera_manager import detect_cameras
from smart_privacy_cam.core.pipeline import VideoPipeline


class SmartPrivacyApp(ctk.CTk):
    def __init__(self, presets_path: Path) -> None:
        super().__init__()
        self.title("Smart Privacy Cam")
        self.geometry("1280x760")

        ctk.set_appearance_mode("dark")

        self._presets_path = presets_path
        self._presets: list[Preset] = load_presets(self._presets_path)
        self._settings = replace(self._presets[0].settings) if self._presets else AppSettings()
        self._pipeline: VideoPipeline | None = None
        self._preview_lock = threading.Lock()
        self._last_preview_image: ctk.CTkImage | None = None

        self._cameras = detect_cameras()

        self._build_ui()
        self._populate_controls()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self)
        self.sidebar.grid(row=0, column=0, sticky="ns", padx=10, pady=10)

        self.preview_frame = ctk.CTkFrame(self)
        self.preview_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        self.preview_frame.grid_rowconfigure(0, weight=1)
        self.preview_frame.grid_columnconfigure(0, weight=1)

        self.preview_label = ctk.CTkLabel(self.preview_frame, text="Preview")
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        row = 0
        self.preset_option = ctk.CTkOptionMenu(self.sidebar, values=["-"])
        self.preset_option.grid(row=row, column=0, padx=10, pady=(10, 6), sticky="ew")

        row += 1
        self.camera_option = ctk.CTkOptionMenu(self.sidebar, values=["0"])
        self.camera_option.grid(row=row, column=0, padx=10, pady=6, sticky="ew")

        row += 1
        self.privacy_option = ctk.CTkOptionMenu(
            self.sidebar,
            values=[PrivacyMode.SQUARE_2D.value, PrivacyMode.BLUR_3D.value],
            command=self._on_privacy_mode_change,
        )
        self.privacy_option.grid(row=row, column=0, padx=10, pady=6, sticky="ew")

        row += 1
        self.third_party_option = ctk.CTkOptionMenu(
            self.sidebar,
            values=[
                ThirdPartyMode.HIDE_OTHERS.value,
                ThirdPartyMode.HIDE_OWNER.value,
                ThirdPartyMode.HIDE_ALL.value,
            ],
            command=self._on_third_party_mode_change,
        )
        self.third_party_option.grid(row=row, column=0, padx=10, pady=6, sticky="ew")

        row += 1
        self.bg_blur_switch = ctk.CTkSwitch(
            self.sidebar,
            text="Background Blur",
            command=self._on_bg_blur_toggle,
        )
        self.bg_blur_switch.grid(row=row, column=0, padx=10, pady=6, sticky="w")

        row += 1
        self.bg_replace_switch = ctk.CTkSwitch(
            self.sidebar,
            text="Background Replace",
            command=self._on_bg_replace_toggle,
        )
        self.bg_replace_switch.grid(row=row, column=0, padx=10, pady=6, sticky="w")

        row += 1
        self.owner_face_slider = ctk.CTkSlider(
            self.sidebar,
            from_=0,
            to=4,
            number_of_steps=4,
            command=self._on_owner_face_change,
        )
        self.owner_face_slider.grid(row=row, column=0, padx=10, pady=6, sticky="ew")

        row += 1
        self.start_btn = ctk.CTkButton(self.sidebar, text="Start", command=self.start_pipeline)
        self.start_btn.grid(row=row, column=0, padx=10, pady=(12, 6), sticky="ew")

        row += 1
        self.stop_btn = ctk.CTkButton(self.sidebar, text="Stop", command=self.stop_pipeline)
        self.stop_btn.grid(row=row, column=0, padx=10, pady=(0, 12), sticky="ew")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _populate_controls(self) -> None:
        preset_names = [preset.name for preset in self._presets] or ["Default"]
        self.preset_option.configure(values=preset_names, command=self._apply_preset_by_name)
        self.preset_option.set(preset_names[0])

        camera_values = [str(c.index) for c in self._cameras] or ["0"]
        self.camera_option.configure(values=camera_values, command=self._on_camera_change)
        self.camera_option.set(str(self._settings.camera_index))

        self.privacy_option.set(self._settings.privacy_mode.value)
        self.third_party_option.set(self._settings.third_party_mode.value)

        if self._settings.enable_background_blur:
            self.bg_blur_switch.select()
        else:
            self.bg_blur_switch.deselect()

        if self._settings.enable_background_replace:
            self.bg_replace_switch.select()
        else:
            self.bg_replace_switch.deselect()

        self.owner_face_slider.set(self._settings.owner_face_index)

    def start_pipeline(self) -> None:
        try:
            if self._pipeline is None:
                self._pipeline = VideoPipeline(
                    settings=replace(self._settings),
                    on_preview=self._on_preview_frame,
                    on_error=self._on_pipeline_error,
                )
            self._pipeline.start()
        except Exception as exc:
            self._pipeline = None
            messagebox.showerror("Smart Privacy Cam", str(exc))

    def stop_pipeline(self) -> None:
        if self._pipeline is not None:
            self._pipeline.stop()
            self._pipeline = None

    def _on_preview_frame(self, frame_bgr) -> None:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(960, 540))

        def set_image() -> None:
            with self._preview_lock:
                self._last_preview_image = ctk_image
                self.preview_label.configure(image=ctk_image, text="")

        self.after(0, set_image)

    def _apply_preset_by_name(self, name: str) -> None:
        preset = next((p for p in self._presets if p.name == name), None)
        if preset is None:
            return
        self._settings = replace(preset.settings)
        self._populate_controls()
        self._update_pipeline_settings()

    def _on_camera_change(self, value: str) -> None:
        self._settings.camera_index = int(value)
        self._update_pipeline_settings()

    def _on_privacy_mode_change(self, value: str) -> None:
        self._settings.privacy_mode = PrivacyMode(value)
        self._update_pipeline_settings()

    def _on_third_party_mode_change(self, value: str) -> None:
        self._settings.third_party_mode = ThirdPartyMode(value)
        self._update_pipeline_settings()

    def _on_bg_blur_toggle(self) -> None:
        self._settings.enable_background_blur = self.bg_blur_switch.get() == 1
        self._update_pipeline_settings()

    def _on_bg_replace_toggle(self) -> None:
        self._settings.enable_background_replace = self.bg_replace_switch.get() == 1
        self._update_pipeline_settings()

    def _on_owner_face_change(self, value: float) -> None:
        self._settings.owner_face_index = int(round(value))
        self._update_pipeline_settings()

    def _update_pipeline_settings(self) -> None:
        if self._pipeline is not None:
            self._pipeline.update_settings(replace(self._settings))

    def _on_close(self) -> None:
        self.stop_pipeline()
        self.destroy()

    def _on_pipeline_error(self, message: str) -> None:
        self.after(0, lambda: messagebox.showerror("Smart Privacy Cam", message))
        self.after(0, self.stop_pipeline)

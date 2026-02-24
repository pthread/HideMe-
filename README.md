# HideMe!

a lightweight virtual camera utility designed for real-time privacy and identity obfuscation during video calls. built to ensure your space and identity remain yours, even when the camera is on.

---

## key features

* **dynamic face anonymization:** toggle between 2d bounding boxes or sophisticated 3d blur using mediapipe face mesh with z-scaling.
* **third-party shielding:** intelligent logic to hide background bystanders, the primary user, or all detected subjects.
* **environment control:** real-time background blurring or total replacement via selfie segmentation.
* **virtual stream output:** seamless integration with external apps via `pyvirtualcam`.
* **integrated ui:** full control panel with live preview and customizable presets.

---

## tech stack

| component | technology |
| :--- | :--- |
| **language** | python 3.10 - 3.12 |
| **computer vision** | opencv, mediapipe (face mesh & selfie segmentation) |
| **streaming** | pyvirtualcam |
| **interface** | customtkinter |

---

## quick start (windows)

### 1. environment setup
```powershell
# create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

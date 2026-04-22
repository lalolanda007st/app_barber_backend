"""
FaceLandmarkerService — MediaPipe Tasks API (mediapipe >= 0.10)

Usa la nueva API de Tasks en lugar de la deprecada mp.solutions.face_mesh.
El modelo .task se descarga automáticamente en primera ejecución.

Requiere Python 3.11 o 3.12.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

_MODEL_DIR  = Path(__file__).resolve().parent.parent.parent / "app" / "models"
_MODEL_PATH = _MODEL_DIR / "face_landmarker.task"
_MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)


def _ensure_model() -> Path:
    """Descarga el modelo si no existe localmente."""
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if not _MODEL_PATH.exists():
        print(f"[FaceLandmarker] Descargando modelo desde {_MODEL_URL} …")
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
        print(f"[FaceLandmarker] Modelo guardado en {_MODEL_PATH}")
    return _MODEL_PATH


class FaceLandmarkerService:
    """Detecta 478 landmarks faciales usando la API de Tasks de MediaPipe."""

    def __init__(self) -> None:
        model_path   = _ensure_model()
        base_options = mp_python.BaseOptions(model_asset_path=str(model_path))
        options      = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)

    def detect_face_landmarks(self, image_path: Path) -> dict | None:
        """
        Retorna dict con image_width, image_height, points: list[(x, y)]
        o None si no se detecta rostro.
        """
        bgr = cv2.imread(str(image_path))
        if bgr is None:
            return None

        h, w = bgr.shape[:2]
        rgb  = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result   = self._landmarker.detect(mp_image)

        if not result.face_landmarks:
            return None

        points = [
            (int(lm.x * w), int(lm.y * h))
            for lm in result.face_landmarks[0]
        ]

        return {"image_width": w, "image_height": h, "points": points}

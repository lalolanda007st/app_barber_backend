"""
HairSegmenterService — MediaPipe Tasks API (mediapipe >= 0.10)

Genera una máscara binaria del cabello (uint8, 0-255) a partir de una imagen.
El modelo .tflite se descarga automáticamente en primera ejecución.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

_MODEL_DIR  = Path(__file__).resolve().parent.parent / "models"
_MODEL_PATH = _MODEL_DIR / "hair_segmenter.tflite"
_MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "image_segmenter/hair_segmenter/float32/latest/hair_segmenter.tflite"
)


def _ensure_model() -> Path:
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if not _MODEL_PATH.exists():
        print(f"[HairSegmenter] Descargando modelo desde {_MODEL_URL} ...")
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
        print(f"[HairSegmenter] Modelo guardado en {_MODEL_PATH}")
    return _MODEL_PATH


class HairSegmenterService:
    """
    Segmenta el cabello en una imagen.
    Retorna máscara uint8 (H x W): 255 = cabello, 0 = resto.
    """

    def __init__(self) -> None:
        model_path   = _ensure_model()
        base_options = mp_python.BaseOptions(model_asset_path=str(model_path))
        options      = mp_vision.ImageSegmenterOptions(
            base_options=base_options,
            output_category_mask=True,
            output_confidence_masks=True,
        )
        self._segmenter = mp_vision.ImageSegmenter.create_from_options(options)

    def get_hair_mask(
        self,
        image_path: Path,
        confidence_threshold: float = 0.5,
        blur_radius: int = 7,
    ) -> np.ndarray | None:
        """
        Retorna máscara uint8 suavizada o None si falla la lectura.
        blur_radius debe ser impar.
        """
        bgr = cv2.imread(str(image_path))
        if bgr is None:
            return None

        rgb      = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result   = self._segmenter.segment(mp_image)

        if not result.confidence_masks:
            return None

        hair_conf: np.ndarray = result.confidence_masks[0].numpy_view()
        mask = (hair_conf >= confidence_threshold).astype(np.uint8) * 255

        if blur_radius > 1:
            br   = blur_radius if blur_radius % 2 == 1 else blur_radius + 1
            mask = cv2.GaussianBlur(mask, (br, br), 0)

        return mask

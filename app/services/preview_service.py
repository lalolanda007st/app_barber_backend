"""
PreviewService — overlay híbrido con segmentación real de cabello

Flujo:
1. Detectar landmarks faciales (FaceLandmarkerService) → bounding box del área de cabello
2. Segmentar cabello con HairSegmenterService → máscara real píxel a píxel
3. Componer el overlay de estilo sobre la máscara real:
   - Color base del tono del corte
   - Textura/patrón diferente por categoría (fade, pompadour, undercut, etc.)
   - Alpha blending suave con la imagen original
4. Si no hay máscara de cabello, fallback al overlay geométrico anterior
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from app.services.face_landmarker_service import FaceLandmarkerService
from app.services.hair_segmenter_service import HairSegmenterService
from app.utils.file_utils import save_file

# ---------------------------------------------------------------------------
# Paletas de color por categoría de corte
# Cada entrada: (color_base_BGR, color_highlight_BGR, alpha_base, alpha_highlight)
# ---------------------------------------------------------------------------
_STYLE_PALETTES: dict[str, dict] = {
    "fade": {
        "base":      (30,  20,  12),   # marrón muy oscuro
        "highlight": (70,  45,  25),   # marrón medio
        "edge":      (212, 168, 83),   # dorado
        "alpha":     0.72,
        "pattern":   "gradient_v",     # degradado vertical (fade)
    },
    "pompadour": {
        "base":      (35,  22,  14),
        "highlight": (80,  55,  30),
        "edge":      (212, 168, 83),
        "alpha":     0.68,
        "pattern":   "sweep",          # barrido lateral
    },
    "undercut": {
        "base":      (20,  15,  10),
        "highlight": (55,  38,  22),
        "edge":      (180, 140, 60),
        "alpha":     0.75,
        "pattern":   "gradient_v",
    },
    "corto": {
        "base":      (45,  30,  18),
        "highlight": (90,  65,  40),
        "edge":      (200, 160, 75),
        "alpha":     0.60,
        "pattern":   "uniform",
    },
    "texturizado": {
        "base":      (50,  32,  18),
        "highlight": (100, 72,  42),
        "edge":      (212, 168, 83),
        "alpha":     0.65,
        "pattern":   "texture",        # ruido de textura
    },
    "largo": {
        "base":      (40,  25,  14),
        "highlight": (85,  60,  35),
        "edge":      (190, 150, 65),
        "alpha":     0.62,
        "pattern":   "sweep",
    },
    "_default": {
        "base":      (45,  28,  15),
        "highlight": (90,  60,  32),
        "edge":      (212, 168, 83),
        "alpha":     0.65,
        "pattern":   "uniform",
    },
}


class PreviewService:
    def __init__(self) -> None:
        self.face_landmarker   = FaceLandmarkerService()
        self.hair_segmenter    = HairSegmenterService()

    # ------------------------------------------------------------------
    # Punto de entrada público
    # ------------------------------------------------------------------

    def process(
        self,
        file,
        hairstyle_id: str | None,
        hairstyle_name: str | None,
        hairstyle_category: str | None,
    ) -> dict:
        image_path = save_file(file)
        return self.process_preview(
            image_path=image_path,
            hairstyle_id=hairstyle_id,
            hairstyle_name=hairstyle_name,
            hairstyle_category=hairstyle_category,
        )

    def process_preview(
        self,
        image_path: Path,
        hairstyle_id: str | None,
        hairstyle_name: str | None,
        hairstyle_category: str | None,
    ) -> dict:
        # --- 1. Leer imagen base -------------------------------------------
        bgr_orig = cv2.imread(str(image_path))
        if bgr_orig is None:
            raise ValueError(f"No se pudo leer la imagen: {image_path}")

        h, w = bgr_orig.shape[:2]
        category = (hairstyle_category or "").lower()

        # --- 2. Detectar landmarks → bounding box de cabello ---------------
        landmarks_data = self.face_landmarker.detect_face_landmarks(image_path)
        face_found = landmarks_data is not None

        if face_found:
            hair_area = self._estimate_hair_area_from_landmarks(
                points=landmarks_data["points"],
                img_width=w,
                img_height=h,
            )
        else:
            hair_area = self._fallback_hair_area(w, h)

        # --- 3. Segmentación real de cabello --------------------------------
        hair_mask = self.hair_segmenter.get_hair_mask(
            image_path,
            confidence_threshold=0.45,
            blur_radius=9,
        )

        # --- 4. Construir overlay en BGR ------------------------------------
        if hair_mask is not None and hair_mask.max() > 0:
            overlay_bgr = self._build_segmentation_overlay(
                bgr_orig, hair_mask, hair_area, category
            )
            used_segmentation = True
        else:
            # Fallback: overlay geométrico sobre bounding box
            overlay_bgr = self._build_geometric_overlay(
                bgr_orig, hair_area, category
            )
            used_segmentation = False

        # --- 5. Convertir a PIL para añadir etiqueta UI --------------------
        result_rgb = cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)
        pil_img    = Image.fromarray(result_rgb)
        draw       = ImageDraw.Draw(pil_img)

        self._draw_label(
            draw=draw,
            hairstyle_name=hairstyle_name,
            hairstyle_category=hairstyle_category,
            face_found=face_found,
            used_segmentation=used_segmentation,
        )

        # --- 6. Guardar resultado -------------------------------------------
        output_name = f"{uuid4().hex}.jpg"
        output_path = Path("outputs") / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pil_img.save(output_path, format="JPEG", quality=92)

        return {
            "success": True,
            "message": "Preview generada correctamente",
            "hairstyle_id": hairstyle_id,
            "hairstyle_name": hairstyle_name,
            "hairstyle_category": hairstyle_category,
            "original_filename": image_path.name,
            "saved_input_path": str(image_path),
            "preview_image_url": f"/outputs/{output_name}",
            "used_segmentation": used_segmentation,
            "face_detected": face_found,
        }

    # ------------------------------------------------------------------
    # Overlay principal: segmentación real píxel a píxel
    # ------------------------------------------------------------------

    def _build_segmentation_overlay(
        self,
        bgr: np.ndarray,
        mask: np.ndarray,          # uint8 0–255, suavizado
        hair_area: tuple,
        category: str,
    ) -> np.ndarray:
        h, w = bgr.shape[:2]
        palette = _STYLE_PALETTES.get(category, _STYLE_PALETTES["_default"])
        pattern = palette["pattern"]

        # Normalizar máscara a float 0–1
        mask_f = mask.astype(np.float32) / 255.0  # (H, W)

        # --- Capa de color base ---
        color_layer = np.zeros_like(bgr, dtype=np.float32)
        color_layer[:] = palette["base"]  # BGR escalar

        # --- Patrón de gradiente/textura sobre la capa de color ---
        if pattern == "gradient_v":
            color_layer = self._apply_gradient_v(
                color_layer, hair_area, palette["base"], palette["highlight"]
            )
        elif pattern == "sweep":
            color_layer = self._apply_sweep(
                color_layer, hair_area, palette["base"], palette["highlight"]
            )
        elif pattern == "texture":
            color_layer = self._apply_texture(
                color_layer, hair_area, palette["base"], palette["highlight"]
            )
        else:  # uniform
            color_layer[:] = palette["highlight"]

        # --- Bordes brillantes (edge glow) sobre contorno de la máscara ---
        edge_layer = self._build_edge_layer(mask, palette["edge"], (h, w))

        # --- Alpha blending: mezclar original + color_layer usando mask_f ---
        alpha = palette["alpha"]
        bgr_f = bgr.astype(np.float32)

        # expand mask para broadcast sobre 3 canales
        m3 = mask_f[:, :, np.newaxis]

        blended = bgr_f * (1.0 - m3 * alpha) + color_layer * (m3 * alpha)

        # Añadir brillo de bordes
        blended = np.clip(blended + edge_layer, 0, 255)

        return blended.astype(np.uint8)

    # ------------------------------------------------------------------
    # Fallback: overlay geométrico (sin segmentación)
    # ------------------------------------------------------------------

    def _build_geometric_overlay(
        self,
        bgr: np.ndarray,
        hair_area: tuple,
        category: str,
    ) -> np.ndarray:
        """Overlay sobre bounding box cuando no hay máscara de cabello."""
        h, w = bgr.shape[:2]
        left, top, right, bottom = hair_area
        palette = _STYLE_PALETTES.get(category, _STYLE_PALETTES["_default"])

        # Crear máscara elíptica suave en el bounding box
        mask = np.zeros((h, w), dtype=np.float32)
        cy, cx = (top + bottom) // 2, (left + right) // 2
        ry, rx = (bottom - top) // 2, (right - left) // 2
        if rx > 0 and ry > 0:
            Y, X = np.ogrid[:h, :w]
            ellipse = ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2
            mask = np.clip(1.0 - ellipse, 0, 1).astype(np.float32)

        color_layer = self._apply_gradient_v(
            np.zeros_like(bgr, dtype=np.float32),
            hair_area,
            palette["base"],
            palette["highlight"],
        )

        m3   = mask[:, :, np.newaxis]
        bgr_f = bgr.astype(np.float32)
        alpha = palette["alpha"]
        blended = bgr_f * (1.0 - m3 * alpha) + color_layer * (m3 * alpha)
        return np.clip(blended, 0, 255).astype(np.uint8)

    # ------------------------------------------------------------------
    # Helpers de patrón
    # ------------------------------------------------------------------

    def _apply_gradient_v(
        self,
        layer: np.ndarray,
        hair_area: tuple,
        color_bottom: tuple,
        color_top: tuple,
    ) -> np.ndarray:
        """Degradado vertical: color_top arriba → color_bottom abajo."""
        h, w = layer.shape[:2]
        left, top, right, bottom = hair_area
        result = layer.copy()

        for y in range(max(0, top), min(h, bottom + 1)):
            if bottom == top:
                t = 0.0
            else:
                t = (y - top) / (bottom - top)  # 0 = arriba, 1 = abajo
            t = np.clip(t, 0, 1)
            color = tuple(
                int(color_top[i] * (1 - t) + color_bottom[i] * t)
                for i in range(3)
            )
            result[y, left:right] = color
        return result

    def _apply_sweep(
        self,
        layer: np.ndarray,
        hair_area: tuple,
        color_base: tuple,
        color_highlight: tuple,
    ) -> np.ndarray:
        """Barrido lateral: simula el efecto peinado del pompadour/largo."""
        h, w = layer.shape[:2]
        left, top, right, bottom = hair_area
        cx = (left + right) / 2.0
        result = layer.copy()

        for y in range(max(0, top), min(h, bottom + 1)):
            for x in range(max(0, left), min(w, right + 1)):
                # t basado en desplazamiento desde el centro → borde derecho
                t = np.clip((x - cx) / max(right - cx, 1), -1, 1)
                t = (t + 1) / 2  # 0 = izquierda, 1 = derecha
                color = tuple(
                    int(color_base[i] * (1 - t) + color_highlight[i] * t)
                    for i in range(3)
                )
                result[y, x] = color
        return result

    def _apply_texture(
        self,
        layer: np.ndarray,
        hair_area: tuple,
        color_base: tuple,
        color_highlight: tuple,
    ) -> np.ndarray:
        """Ruido suave para simular textura del cabello texturizado."""
        h, w = layer.shape[:2]
        left, top, right, bottom = hair_area
        result = layer.copy()

        # Ruido Perlin-like: sumar capas de ruido gaussiano a distintas escalas
        rng   = np.random.default_rng(seed=42)
        noise = np.zeros((h, w), dtype=np.float32)
        for scale in [16, 8, 4]:
            small = rng.random(
                (h // scale + 1, w // scale + 1), dtype=np.float32
            )
            upsampled = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
            noise += upsampled / scale

        noise = noise / noise.max()  # normalizar a [0,1]

        b_base = np.array(color_base,      dtype=np.float32)
        b_hi   = np.array(color_highlight, dtype=np.float32)

        for y in range(max(0, top), min(h, bottom + 1)):
            for x in range(max(0, left), min(w, right + 1)):
                t = noise[y, x]
                color = b_base * (1 - t) + b_hi * t
                result[y, x] = color.astype(np.uint8)
        return result

    def _build_edge_layer(
        self,
        mask: np.ndarray,
        edge_color_bgr: tuple,
        shape: tuple,
    ) -> np.ndarray:
        """Genera un brillo sutil en el contorno del cabello (efecto edge glow)."""
        h, w = shape
        # Detectar bordes de la máscara con Canny
        edges = cv2.Canny(mask, 50, 150)
        # Dilatar y suavizar para un halo suave
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        edges  = cv2.dilate(edges, kernel, iterations=1)
        edges  = cv2.GaussianBlur(edges, (7, 7), 0)

        edge_f = edges.astype(np.float32) / 255.0 * 0.35  # intensidad del halo
        layer  = np.zeros((h, w, 3), dtype=np.float32)
        layer[:, :, 0] = edge_f * edge_color_bgr[0]
        layer[:, :, 1] = edge_f * edge_color_bgr[1]
        layer[:, :, 2] = edge_f * edge_color_bgr[2]
        return layer

    # ------------------------------------------------------------------
    # Estimación de área de cabello desde landmarks
    # ------------------------------------------------------------------

    def _estimate_hair_area_from_landmarks(
        self,
        points: list[tuple[int, int]],
        img_width: int,
        img_height: int,
    ) -> tuple[int, int, int, int]:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        face_left   = min(xs)
        face_right  = max(xs)
        face_top    = min(ys)
        face_bottom = max(ys)
        face_width  = face_right - face_left
        face_height = face_bottom - face_top
        center_x    = (face_left + face_right) // 2

        hair_width = int(face_width * 1.55)
        left  = center_x - hair_width // 2
        right = center_x + hair_width // 2
        top   = int(face_top - face_height * 0.95)
        bottom = int(face_top + face_height * 0.08)

        shift = int(face_width * 0.03)
        left  -= shift
        right -= shift

        left   = max(0, left)
        right  = min(img_width - 1, right)
        top    = max(0, top)
        bottom = min(img_height - 1, bottom)

        if bottom <= top:
            bottom = min(img_height - 1, top + max(60, face_height // 2))

        return left, top, right, bottom

    def _fallback_hair_area(
        self, width: int, height: int
    ) -> tuple[int, int, int, int]:
        return (
            int(width * 0.24),
            int(height * 0.08),
            int(width * 0.76),
            int(height * 0.30),
        )

    # ------------------------------------------------------------------
    # Etiqueta UI (PIL)
    # ------------------------------------------------------------------

    def _draw_label(
        self,
        draw: ImageDraw.ImageDraw,
        hairstyle_name: str | None,
        hairstyle_category: str | None,
        face_found: bool,
        used_segmentation: bool,
    ) -> None:
        label_name     = hairstyle_name or "Sin nombre"
        label_category = hairstyle_category or "Sin categoría"

        if used_segmentation:
            mode_text = "Segmentación IA activa"
            mode_color = (80, 200, 120)
        elif face_found:
            mode_text  = "Rostro detectado"
            mode_color = (212, 168, 83)
        else:
            mode_text  = "Sin detección de rostro"
            mode_color = (180, 100, 100)

        draw.rounded_rectangle(
            [(20, 20), (540, 140)],
            radius=18,
            fill=(10, 10, 10),
            outline=(212, 168, 83),
            width=3,
        )
        draw.text((35, 38),  f"Preview: {label_name}",      fill=(245, 240, 232))
        draw.text((35, 70),  f"Categoría: {label_category}", fill=(212, 168, 83))
        draw.text((35, 102), mode_text,                      fill=mode_color)
        draw.text((35, 120), "BarberVision AI",              fill=(80, 80, 80))

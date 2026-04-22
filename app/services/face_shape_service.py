"""
FaceShapeService — Clasificador de forma de cara.

Usa los landmarks de MediaPipe para calcular ratios faciales
y clasificar en: Oval | Cuadrada | Redondo | Corazon | Rectangular
"""
from __future__ import annotations

import math
from pathlib import Path

from app.services.face_landmarker_service import FaceLandmarkerService

# ── Índices de landmarks relevantes (FaceMesh 478 pts) ───────────────────────
_LM = {
    "cheek_l" : 234, "cheek_r"  : 454,
    "top"     : 10,  "chin"     : 152,
    "jaw_l"   : 172, "jaw_r"    : 397,
    "temple_l": 54,  "temple_r" : 284,
    "chin_l"  : 149, "chin_r"   : 378,
}

_RECOMMENDATIONS = {
    "Oval":        {"explanation": "La forma oval es la más versátil — casi cualquier corte te favorece.",              "categories": ["Fade","Pompadour","Undercut","Texturizado","Corto"]},
    "Cuadrada":    {"explanation": "Los cortes con volumen en la parte superior alargan visualmente la cara.",           "categories": ["Pompadour","Fade","Undercut"]},
    "Redondo":     {"explanation": "Los cortes con altura en el tope estilizan y alargan la cara redonda.",              "categories": ["Pompadour","Fade","Texturizado"]},
    "Corazon":     {"explanation": "Los cortes más voluminosos en los lados equilibran la frente ancha.",                "categories": ["Undercut","Texturizado","Fade"]},
    "Rectangular": {"explanation": "Los cortes con volumen lateral suavizan las mejillas y acortan la cara.",            "categories": ["Texturizado","Corto","Fade"]},
}


def _dist(p1, p2) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


class FaceShapeService:
    def __init__(self) -> None:
        self._landmarker = FaceLandmarkerService()

    def classify(self, image_path: Path, hairstyle_ids_by_category: dict) -> dict:
        """
        Retorna dict compatible con FaceShapeResponse.
        hairstyle_ids_by_category: {"Fade": ["id1","id2"], ...}
        """
        data = self._landmarker.detect_face_landmarks(image_path)
        if data is None:
            return {
                "face_shape": "Oval", "confidence": 0.0,
                "recommended_hairstyle_ids": [],
                "explanation": "No se detectó rostro. Se asume forma Oval por defecto.",
            }

        shape, confidence, _ = self._compute_shape(data["points"])
        rec_ids              = self._recommended_ids(shape, hairstyle_ids_by_category)

        return {
            "face_shape":               shape,
            "confidence":               round(confidence, 2),
            "recommended_hairstyle_ids": rec_ids,
            "explanation":              _RECOMMENDATIONS[shape]["explanation"],
        }

    def _compute_shape(self, pts):
        if len(pts) < 478:
            return "Oval", 0.5, {}

        face_w  = _dist(pts[_LM["cheek_l"]], pts[_LM["cheek_r"]])
        face_h  = _dist(pts[_LM["top"]],    pts[_LM["chin"]])
        jaw_w   = _dist(pts[_LM["jaw_l"]],  pts[_LM["jaw_r"]])
        fore_w  = _dist(pts[_LM["temple_l"]],pts[_LM["temple_r"]])
        chin_w  = _dist(pts[_LM["chin_l"]], pts[_LM["chin_r"]])

        if face_w == 0:
            return "Oval", 0.5, {}

        h_w      = face_h / face_w
        jaw_ch   = jaw_w  / face_w
        fore_jaw = fore_w / jaw_w  if jaw_w else 1.0
        chin_jaw = chin_w / jaw_w  if jaw_w else 1.0

        ratios = {"face_h_w": round(h_w,3), "jaw_cheek": round(jaw_ch,3),
                  "forehead_jaw": round(fore_jaw,3), "chin_jaw": round(chin_jaw,3)}

        shape, conf = self._rules(h_w, jaw_ch, fore_jaw, chin_jaw)
        return shape, conf, ratios

    def _rules(self, h_w, jaw_ch, fore_jaw, chin_jaw):
        scores = {k: 0.0 for k in _RECOMMENDATIONS}

        if 1.25 <= h_w <= 1.55 and 0.75 <= jaw_ch <= 0.92: scores["Oval"]        += 1.0
        if 0.80 <= fore_jaw <= 1.10:                        scores["Oval"]        += 0.4
        if h_w < 1.30 and jaw_ch >= 0.90:                  scores["Cuadrada"]    += 1.0
        if fore_jaw >= 0.95:                                scores["Cuadrada"]    += 0.3
        if h_w < 1.25 and jaw_ch < 0.90:                   scores["Redondo"]     += 1.0
        if chin_jaw > 0.75:                                 scores["Redondo"]     += 0.3
        if fore_jaw > 1.10 and chin_jaw < 0.65:            scores["Corazon"]     += 1.2
        if h_w >= 1.25:                                     scores["Corazon"]     += 0.2
        if h_w > 1.55 and jaw_ch >= 0.85:                  scores["Rectangular"] += 1.0
        if fore_jaw >= 0.95:                                scores["Rectangular"] += 0.2

        best  = max(scores, key=lambda k: scores[k])
        total = sum(scores.values()) or 1.0
        conf  = scores[best] / total

        return ("Oval", 0.4) if scores[best] < 0.3 else (best, min(conf, 0.98))

    def _recommended_ids(self, shape, ids_by_category):
        result = []
        for cat in _RECOMMENDATIONS.get(shape, {}).get("categories", []):
            result.extend(ids_by_category.get(cat, []))
        return result[:8]

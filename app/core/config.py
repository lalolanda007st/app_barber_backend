"""
app/core/config.py — Configuración global de BarberVision Backend.

Este módulo centraliza todas las variables de entorno y rutas del proyecto.
Se importa en cualquier módulo que necesite acceso a configuración global.

Variables de entorno requeridas (definir en .env o en Railway Variables):
    SUPABASE_URL      : URL del proyecto Supabase (https://xxxx.supabase.co)
    SUPABASE_KEY      : Anon key de Supabase (acepta también SUPABASE_ANON_KEY)
    SUPABASE_ANON_KEY : Alternativa a SUPABASE_KEY (compatible con Railway)

Rutas importantes:
    BASE_DIR    : Raíz del proyecto
    UPLOADS_DIR : Imágenes subidas por los usuarios (temporal)
    OUTPUTS_DIR : Imágenes procesadas por el preview service (servidas estáticamente)
"""

import os
from pathlib import Path

# ── Rutas del proyecto ────────────────────────────────────────────────────────

# Raíz del proyecto (tres niveles arriba de este archivo: core → app → raíz)
BASE_DIR    = Path(__file__).resolve().parent.parent.parent

# Directorio donde se guardan las imágenes subidas por los usuarios
UPLOADS_DIR = BASE_DIR / "uploads"

# Directorio donde se guardan las imágenes procesadas (preview con overlay de IA)
# Este directorio se monta como ruta estática en FastAPI (/outputs)
OUTPUTS_DIR = BASE_DIR / "outputs"

# ── Supabase ──────────────────────────────────────────────────────────────────

# URL del proyecto Supabase — se obtiene en Settings > API > Project URL
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")

# Anon key de Supabase — acepta dos nombres de variable para compatibilidad:
#   - SUPABASE_KEY      : nombre usado en desarrollo local (.env)
#   - SUPABASE_ANON_KEY : nombre usado en Railway (variable configurada en el dashboard)
SUPABASE_KEY: str = (
    os.environ.get("SUPABASE_KEY")
    or os.environ.get("SUPABASE_ANON_KEY")
    or ""
)

# Advertencia si faltan las variables — no lanza excepción para no bloquear Railway
if not SUPABASE_URL or not SUPABASE_KEY:
    import warnings
    warnings.warn(
        "SUPABASE_URL y SUPABASE_KEY no están definidas. "
        "Define estas variables en tu archivo .env (desarrollo) "
        "o en Railway Variables (producción).",
        stacklevel=2,
    )

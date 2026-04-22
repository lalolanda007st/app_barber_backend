"""
==============================================================================
app/core/config.py — Configuración central del proyecto BarberVision
==============================================================================
Este archivo es el punto único de configuración de la aplicación.
Se encarga de:
  1. Definir las rutas del sistema de archivos (uploads, outputs).
  2. Leer las variables de entorno del archivo .env usando python-dotenv.
  3. Exponer las credenciales de Supabase para que otros módulos las importen.
  4. Validar que las variables obligatorias existan al arrancar el servidor.

Todos los módulos que necesiten configuración deben importar desde aquí,
nunca leer os.getenv() directamente en otros archivos.
==============================================================================
"""

from pathlib import Path
from dotenv import load_dotenv
import os

# Carga las variables del archivo .env ubicado en la raíz del proyecto.
# Si el .env no existe, las variables deben estar definidas en el entorno del sistema.
load_dotenv()

# ── Rutas del sistema de archivos ────────────────────────────────────────────

# BASE_DIR apunta a la raíz del proyecto (3 niveles arriba de este archivo)
# Estructura: raíz / app / core / config.py  →  parent x3 = raíz
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Carpeta donde se guardan las imágenes subidas por los usuarios
UPLOADS_DIR = BASE_DIR / "uploads"

# Carpeta donde se guardan las imágenes procesadas (previews con cortes aplicados)
OUTPUTS_DIR = BASE_DIR / "outputs"

# ── Credenciales de Supabase ─────────────────────────────────────────────────

# URL del proyecto en Supabase, formato: https://xxxx.supabase.co
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")

# Clave pública (anon key): segura para operaciones generales con RLS activo
SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

# Clave secreta (service role): acceso total sin restricciones de RLS.
# Usar SOLO en operaciones administrativas del backend, nunca en el frontend.
SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# ── Validación al inicio ─────────────────────────────────────────────────────

# Si faltan las variables obligatorias, el servidor falla inmediatamente
# con un mensaje claro en lugar de errores crípticos más adelante.
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError(
        "Faltan variables de entorno obligatorias: SUPABASE_URL y SUPABASE_ANON_KEY "
        "deben estar definidas en el archivo .env de la raíz del proyecto."
    )

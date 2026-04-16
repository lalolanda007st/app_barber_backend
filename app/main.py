# Importaciones principales de FastAPI para crear la API y manejar archivos/formularios
from fastapi import FastAPI, UploadFile, File, Form, HTTPException

# Middleware para permitir solicitudes desde otros dominios (CORS)
from fastapi.middleware.cors import CORSMiddleware

# Para servir archivos estáticos (como imágenes generadas)
from fastapi.staticfiles import StaticFiles

# Esquemas (modelos de respuesta) definidos en la aplicación
from app.schemas import HealthResponse, PreviewResponse

# Servicio encargado de procesar las imágenes y generar previews
from app.services.preview_service import PreviewService

# Utilidades para manejo de archivos
from app.utils.file_utils import save_upload_file, ensure_dirs


# ==============================
# Inicialización de la aplicación
# ==============================

# Se crea la instancia principal de la API
app = FastAPI(title="BarberVision API", version="0.1.0")

# Instancia del servicio que procesa las imágenes
preview_service = PreviewService()


# ==============================
# Configuración de CORS
# ==============================

# Permite que cualquier origen acceda a la API (útil en desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los dominios
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos HTTP (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos los headers
)


# ==============================
# Preparación de directorios
# ==============================

# Asegura que existan los directorios necesarios (por ejemplo, outputs/)
ensure_dirs()


# ==============================
# Archivos estáticos
# ==============================

# Permite acceder a archivos generados (como imágenes) vía URL
# Ejemplo: http://localhost:8000/outputs/archivo.png
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")


# ==============================
# Endpoint de salud (health check)
# ==============================

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Endpoint para verificar que el servicio está funcionando correctamente.

    Retorna:
        HealthResponse:
            - status: estado del servicio ("ok")
            - service: nombre del servicio
    """
    return HealthResponse(
        status="ok",
        service="barbervision-backend",
    )


# ==============================
# Endpoint para generar preview
# ==============================

@app.post("/generate-preview", response_model=PreviewResponse)
async def generate_preview(
    file: UploadFile = File(...),  # Archivo de imagen subido por el usuario
    hairstyle_id: str | None = Form(default=None),  # ID opcional del peinado
    hairstyle_name: str | None = Form(default=None),  # Nombre opcional del peinado
) -> PreviewResponse:
    """
    Endpoint que recibe una imagen y genera un preview con un peinado.

    Parámetros:
        file (UploadFile): Imagen subida por el usuario.
        hairstyle_id (str | None): Identificador del peinado (opcional).
        hairstyle_name (str | None): Nombre del peinado (opcional).

    Retorna:
        PreviewResponse: Resultado del procesamiento de la imagen.

    Errores:
        - 400: Si el archivo no es una imagen.
        - 500: Si ocurre un error durante el procesamiento.
    """

    # Validación: verificar que el archivo sea una imagen
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser una imagen"
        )

    try:
        # Guardar la imagen en el servidor
        saved_path = save_upload_file(file)

        # Procesar la imagen usando el servicio
        result = preview_service.process_preview(
            image_path=saved_path,
            hairstyle_id=hairstyle_id,
            hairstyle_name=hairstyle_name,
        )

        # Retornar el resultado como respuesta estructurada
        return PreviewResponse(**result)

    except Exception as e:
        # Manejo de errores generales
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando imagen: {str(e)}"
        )

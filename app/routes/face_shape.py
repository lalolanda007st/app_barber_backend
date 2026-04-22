"""
==============================================================================
app/routes/face_shape.py — Endpoint de análisis de forma del rostro
==============================================================================
Recibe una foto del cliente, la procesa con IA (MediaPipe) y devuelve:
  - La forma del rostro detectada (oval, redondo, cuadrado, etc.)
  - Una lista de cortes de cabello recomendados para esa forma

Flujo del request:
  1. Cliente envía imagen → se valida que sea una imagen válida
  2. La imagen se guarda temporalmente en la carpeta uploads/
  3. FaceShapeService analiza la imagen con MediaPipe
  4. Se devuelve la forma del rostro y los cortes recomendados
  5. La imagen temporal permanece en uploads/ para posibles usos posteriores

Endpoint:
  POST /face-shape  → Analizar forma del rostro en una imagen

Dependencias:
  - app/services/face_shape_service.py : lógica de análisis y clasificación
  - app/utils/file_utils.py             : guardado de la imagen subida
==============================================================================
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import FaceShapeResponse
from app.services.face_shape_service import FaceShapeService
from app.utils.file_utils import save_file

router = APIRouter(prefix="/face-shape", tags=["Face Shape"])

# Instancia única del servicio de análisis facial.
# Se crea al arrancar el servidor para que el modelo de IA
# ya esté cargado en memoria cuando llegue el primer request.
face_shape_service = FaceShapeService()


@router.post("/", response_model=FaceShapeResponse)
async def analyze_face_shape(file: UploadFile = File(...)) -> FaceShapeResponse:
    """
    Analiza la forma del rostro en una foto y recomienda cortes de cabello.

    El cliente debe enviar la imagen como multipart/form-data con el campo 'file'.
    Solo se aceptan archivos de tipo imagen (image/jpeg, image/png, etc.).

    Args:
        file (UploadFile): Foto del cliente enviada como form-data.
                           Debe ser un archivo de imagen válido.

    Returns:
        FaceShapeResponse:
            - success=True  : con face_shape y recommended_hairstyles
            - success=False : si no se detectó ningún rostro en la imagen

    Raises:
        HTTPException 400: Si el archivo no es una imagen.
        HTTPException 500: Si ocurre un error durante el procesamiento de IA.
    """
    # Valida que el archivo subido sea realmente una imagen
    # file.content_type puede ser None si el cliente no envía el Content-Type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser una imagen (jpg, png, webp, etc.)"
        )

    try:
        # Guarda la imagen en la carpeta uploads/ y obtiene su ruta en disco
        image_path = save_file(file)

        # Analiza la imagen: detecta landmarks y clasifica la forma del rostro
        result = face_shape_service.analyze(image_path)

        # Convierte el dict resultado al schema de respuesta validado por Pydantic
        return FaceShapeResponse(**result)

    except Exception as e:
        import traceback
        traceback.print_exc()  # Imprime el stack trace completo en los logs del servidor
        raise HTTPException(status_code=500, detail=str(e))

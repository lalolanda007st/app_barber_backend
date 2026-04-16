# Importa BaseModel desde la librería Pydantic
# BaseModel permite definir modelos de datos con validación automática
from pydantic import BaseModel


# Define una clase llamada HealthResponse que hereda de BaseModel
class HealthResponse(BaseModel):
    
    # Campo obligatorio de tipo string
    # Indica el estado del servicio (ej: "ok", "down")
    status: str
    
    # Campo obligatorio de tipo string
    # Nombre del servicio que responde (ej: "api-usuarios")
    service: str


# Define una clase llamada PreviewResponse que también hereda de BaseModel
# Esta clase representa una respuesta más compleja (por ejemplo, resultado de procesar una imagen)
class PreviewResponse(BaseModel):
    
    # Campo obligatorio booleano
    # Indica si la operación fue exitosa (True o False)
    success: bool
    
    # Campo obligatorio string
    # Mensaje descriptivo del resultado (éxito o error)
    message: str
    
    # Campo opcional (puede ser string o None)
    # ID del peinado generado o seleccionado
    hairstyle_id: str | None = None
    
    # Campo opcional
    # Nombre del peinado
    hairstyle_name: str | None = None
    
    # Campo opcional
    # Nombre original del archivo que subió el usuario
    original_filename: str | None = None
    
    # Campo opcional
    # Ruta donde se guardó el archivo de entrada en el servidor
    saved_input_path: str | None = None
    
    # Campo opcional
    # URL de la imagen generada o vista previa
    preview_image_url: str | None = None

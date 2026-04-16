# Importa Path para manejar rutas de archivos de forma segura y moderna
from pathlib import Path

# Importa uuid4 para generar identificadores únicos (evita nombres repetidos)
from uuid import uuid4

# Importa UploadFile de FastAPI
# Representa un archivo subido por el usuario en una petición HTTP
from fastapi import UploadFile

# Importa shutil para copiar archivos fácilmente
import shutil


# Define la carpeta donde se guardarán los archivos subidos
UPLOAD_DIR = Path("uploads")

# Define la carpeta donde se guardarán los resultados/procesados
OUTPUT_DIR = Path("outputs")


# Función que asegura que existan las carpetas necesarias
def ensure_dirs() -> None:
    
    # Crea la carpeta 'uploads' si no existe
    # parents=True: crea carpetas intermedias si faltan
    # exist_ok=True: no lanza error si ya existe
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Crea la carpeta 'outputs' con las mismas condiciones
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Función para guardar un archivo subido por el usuario
def save_upload_file(upload_file: UploadFile, destination_dir: Path = UPLOAD_DIR) -> Path:
    
    # Asegura que las carpetas existan antes de guardar el archivo
    ensure_dirs()

    # Obtiene la extensión del archivo (ej: .jpg, .png)
    # upload_file.filename puede ser None, por eso se usa "or ''"
    # .suffix devuelve la extensión
    # .lower() normaliza a minúsculas
    # Si no hay extensión, usa ".jpg" por defecto
    suffix = Path(upload_file.filename or "").suffix.lower() or ".jpg"
    
    # Genera un nombre único usando UUID
    # .hex convierte el UUID a string sin guiones
    filename = f"{uuid4().hex}{suffix}"
    
    # Construye la ruta completa donde se guardará el archivo
    destination = destination_dir / filename

    # Abre el archivo destino en modo escritura binaria ("wb")
    # necesario para copiar archivos (como imágenes)
    with destination.open("wb") as buffer:
        
        # Copia el contenido del archivo subido al archivo destino
        # upload_file.file es un objeto tipo archivo
        shutil.copyfileobj(upload_file.file, buffer)

    # Devuelve la ruta donde se guardó el archivo
    return destination

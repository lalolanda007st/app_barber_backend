# Barber App Backend
Edu VC 
Backend de **Barber App**, una API desarrollada para gestionar la lógica del servidor de una aplicación de barbería.  
Este proyecto permite administrar usuarios, barberos, servicios, citas, autenticación y futuras integraciones con pagos, notificaciones e inteligencia artificial.

---

## Características

- Registro e inicio de sesión de usuarios
- Autenticación segura
- Gestión de perfiles de clientes y barberos
- Administración de servicios de barbería
- Creación y gestión de citas
- Control de disponibilidad de barberos
- API lista para conectar con app móvil en Flutter
- Estructura escalable para futuras integraciones
- Preparado para despliegue en producción

---

## Tecnologías usadas

Según tu stack, aquí puedes dejar o ajustar lo siguiente:

- **Python**
- **FastAPI** / **Flask** *(elige la que uses)*
- **SQLAlchemy** *(si usas ORM)*
- **PostgreSQL** / **MySQL** / **SQLite**
- **JWT** para autenticación
- **Uvicorn / Gunicorn**
- **Pydantic**
- **Docker** *(opcional)*

---
Modo de uso:
Primero clona el repositorio y accede a la ruta del proyecto

- git clone https://github.com/TU_USUARIO/barber_app_backend.git
- cd barber_app_backend
- activar el entorno virtual : source env/bin/activate
- instalar las dependencias necesarias : pip install -r requirements.txt
- Crear las variables de entorno :
```bash
APP_NAME=Barber App Backend
DEBUG=True
HOST=0.0.0.0
PORT=8000
DATABASE_URL=sqlite:///./barber.db
SECRET_KEY=tu_clave_secreta
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
-DATABASE_URL=sqlite:///./barber.db
-SECRET_KEY=tu_clave_secreta
-ALGORITHM=HS256
-ACCESS_TOKEN_EXPIRE_MINUTES=60
```
---
## Estructura del proyecto

```bash
barber_app_backend/
│
├── app/
│   ├── main.py
│   ├── routes/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── database/
│   ├── core/
│   └── utils/
│
├── requirements.txt
├── .env.example #Ejemplo del nombre del envoltorio
├── README.md
└── run.py


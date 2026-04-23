"""
==============================================================================
app/db/supabase_client.py — Cliente único de conexión a Supabase
==============================================================================
Este módulo crea y expone una única instancia del cliente de Supabase
que es reutilizada por todos los routes y servicios del proyecto.

¿Por qué un cliente único (singleton)?
  - Evita crear una conexión nueva en cada request, lo cual sería costoso.
  - Centraliza la configuración de conexión en un solo lugar.
  - Si las credenciales cambian, solo se modifica config.py.

Uso desde otros módulos:
    from app.db.supabase_client import supabase
    response = supabase.table("barbers").select("*").execute()

Variables de entorno requeridas (definidas en .env o Railway Variables):
  - SUPABASE_URL      : URL del proyecto Supabase (https://xxxx.supabase.co)
  - SUPABASE_KEY      : Anon key del proyecto (nombre local en .env)
  - SUPABASE_ANON_KEY : Alternativa a SUPABASE_KEY (nombre usado en Railway)

Nota: config.py acepta ambos nombres y los expone como SUPABASE_KEY.
Si ninguno está definido, se lanza RuntimeError al arrancar el servidor.

Dependencias:
  - supabase-py     : cliente oficial de Supabase para Python
  - app.core.config : provee SUPABASE_URL y SUPABASE_KEY desde el entorno
==============================================================================
"""

from supabase import create_client, Client

# Importar desde config.py — aquí se resuelve SUPABASE_KEY o SUPABASE_ANON_KEY
from app.core.config import SUPABASE_URL, SUPABASE_KEY

# Validar que las credenciales estén disponibles antes de intentar conectar
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "No se puede inicializar Supabase. "
        "Define SUPABASE_URL y SUPABASE_KEY (o SUPABASE_ANON_KEY) "
        "en tu archivo .env o en Railway Variables."
    )

# Crea el cliente usando la URL del proyecto y la clave pública (anon key).
# Este objeto es el punto de entrada para todas las operaciones con la base de datos:
# SELECT, INSERT, UPDATE, DELETE, llamadas a funciones RPC, storage, etc.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

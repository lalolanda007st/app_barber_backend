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

Dependencias:
  - supabase-py  : cliente oficial de Supabase para Python
  - app.core.config : provee SUPABASE_URL y SUPABASE_ANON_KEY desde el .env
==============================================================================
"""

from supabase import create_client, Client
from app.core.config import SUPABASE_URL, SUPABASE_ANON_KEY

# Crea el cliente usando la URL del proyecto y la clave pública (anon key).
# Este objeto es el punto de entrada para todas las operaciones con la base de datos:
# SELECT, INSERT, UPDATE, DELETE, llamadas a funciones RPC, storage, etc.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

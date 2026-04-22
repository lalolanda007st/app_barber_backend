"""
Middleware de autenticación JWT para BarberVision.
Valida el token de Supabase en los endpoints protegidos.

Uso en cualquier ruta:
    from app.core.auth_middleware import get_current_user
    
    @router.get("/protected")
    async def protected(user = Depends(get_current_user)):
        return {"user_id": user.id}
"""
from fastapi import Depends, HTTPException, Header
from app.db.supabase_client import supabase


class AuthUser:
    """Usuario autenticado extraído del JWT."""
    def __init__(self, user_id: str, email: str):
        self.id    = user_id
        self.email = email


async def get_current_user(authorization: str = Header(default="")) -> AuthUser:
    """
    Dependency de FastAPI que valida el Bearer token de Supabase.
    Lanza 401 si el token es inválido o ha expirado.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")

    token = authorization.replace("Bearer ", "").strip()

    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")
        return AuthUser(
            user_id = user_response.user.id,
            email   = user_response.user.email or "",
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


async def get_optional_user(authorization: str = Header(default="")) -> AuthUser | None:
    """
    Como get_current_user pero no lanza error si no hay token.
    Útil para endpoints que funcionan con o sin auth.
    """
    if not authorization.startswith("Bearer "):
        return None
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None

"""
Auth routes — registro, login, logout, perfil de usuario.
Usa Supabase Auth como proveedor de identidad.
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.db.supabase_client import supabase

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    face_shape: Optional[str] = None
    avatar_url: Optional[str] = None


class AuthResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None


class ProfileResponse(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    face_shape: str = "Oval"


# ── Helper: extraer token del header ─────────────────────────────────────────

def _get_token(authorization: str = "") -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    return authorization.replace("Bearer ", "").strip()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest) -> AuthResponse:
    """Registro con email y password. Crea perfil automáticamente via trigger."""
    try:
        res = supabase.auth.sign_up({
            "email"   : data.email,
            "password": data.password,
            "options" : {"data": {"full_name": data.full_name}},
        })
        if not res.user:
            raise HTTPException(status_code=400, detail="No se pudo crear el usuario")

        # Actualizar teléfono en perfil si se proporcionó
        if data.phone:
            supabase.table("profiles").update({"phone": data.phone}).eq("id", res.user.id).execute()

        return AuthResponse(
            success       = True,
            message       = "Registro exitoso. Revisa tu email para confirmar tu cuenta.",
            access_token  = res.session.access_token  if res.session else None,
            refresh_token = res.session.refresh_token if res.session else None,
            user_id       = res.user.id,
            email         = res.user.email,
            full_name     = data.full_name,
        )
    except HTTPException:
        raise
    except Exception as e:
        err = str(e).lower()
        if "already registered" in err or "already exists" in err:
            raise HTTPException(status_code=409, detail="Este email ya está registrado")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest) -> AuthResponse:
    """Login con email y password."""
    try:
        res = supabase.auth.sign_in_with_password({
            "email"   : data.email,
            "password": data.password,
        })
        if not res.user or not res.session:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        # Obtener perfil
        profile = None
        try:
            profile = (supabase.table("profiles")
                       .select("full_name")
                       .eq("id", res.user.id)
                       .single()
                       .execute()).data
        except Exception:
            pass

        return AuthResponse(
            success       = True,
            message       = "Login exitoso",
            access_token  = res.session.access_token,
            refresh_token = res.session.refresh_token,
            user_id       = res.user.id,
            email         = res.user.email,
            full_name     = profile.get("full_name") if profile else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        err = str(e).lower()
        if "invalid" in err or "credentials" in err:
            raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout")
async def logout(authorization: str = Header(default="")):
    """Invalida la sesión actual."""
    try:
        token = _get_token(authorization)
        supabase.auth.admin.sign_out(token)
    except Exception:
        pass  # logout siempre es exitoso desde el cliente
    return {"success": True, "message": "Sesión cerrada"}


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(refresh_token: str) -> AuthResponse:
    """Renueva el access_token usando el refresh_token."""
    try:
        res = supabase.auth.refresh_session(refresh_token)
        if not res.session:
            raise HTTPException(status_code=401, detail="Refresh token inválido")
        return AuthResponse(
            success       = True,
            message       = "Token renovado",
            access_token  = res.session.access_token,
            refresh_token = res.session.refresh_token,
            user_id       = res.user.id if res.user else None,
            email         = res.user.email if res.user else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(authorization: str = Header(default="")) -> ProfileResponse:
    """Obtiene el perfil del usuario autenticado."""
    token = _get_token(authorization)
    try:
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")

        profile = (supabase.table("profiles")
                   .select("*")
                   .eq("id", user.user.id)
                   .single()
                   .execute()).data

        return ProfileResponse(
            user_id    = user.user.id,
            email      = user.user.email or "",
            full_name  = profile.get("full_name") if profile else None,
            phone      = profile.get("phone")     if profile else None,
            avatar_url = profile.get("avatar_url") if profile else None,
            face_shape = profile.get("face_shape", "Oval") if profile else "Oval",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    data: UpdateProfileRequest,
    authorization: str = Header(default=""),
) -> ProfileResponse:
    """Actualiza el perfil del usuario autenticado."""
    token = _get_token(authorization)
    try:
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")

        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        if updates:
            supabase.table("profiles").update(updates).eq("id", user.user.id).execute()

        profile = (supabase.table("profiles")
                   .select("*")
                   .eq("id", user.user.id)
                   .single()
                   .execute()).data

        return ProfileResponse(
            user_id    = user.user.id,
            email      = user.user.email or "",
            full_name  = profile.get("full_name"),
            phone      = profile.get("phone"),
            avatar_url = profile.get("avatar_url"),
            face_shape = profile.get("face_shape", "Oval"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-password")
async def reset_password(email: str) -> dict:
    """Envía email para resetear contraseña."""
    try:
        supabase.auth.reset_password_email(email)
        return {"success": True, "message": "Email de recuperación enviado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
==============================================================================
app/routes/reviews.py — Endpoints para reseñas de barberos
==============================================================================
Permite a los clientes dejar reseñas con calificación (1-5 estrellas) y
comentario de texto sobre el servicio de un barbero.

Punto clave: al insertar una reseña en Supabase, el trigger de PostgreSQL
trg_update_barber_rating se dispara automáticamente y recalcula el campo
avg_rating del barbero afectado. No es necesario calcular el promedio aquí.

Endpoints:
  POST /reviews                           → Publicar una nueva reseña
  GET  /reviews                           → Listar reseñas (todas o por barbero)
  GET  /reviews/barber/{id}/summary       → Resumen estadístico de un barbero

Tabla Supabase utilizada: reviews
==============================================================================
"""

from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import ReviewRequest, ReviewResponse
from app.db.supabase_client import supabase

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("/", response_model=ReviewResponse)
async def create_review(data: ReviewRequest) -> ReviewResponse:
    """
    Publica una nueva reseña para un barbero.

    El trigger trg_update_barber_rating en Supabase se ejecuta automáticamente
    al insertar, actualizando el avg_rating del barbero sin intervención del backend.

    Args:
        data (ReviewRequest): Datos de la reseña validados por Pydantic.
                              El rating debe estar entre 1 y 5 (validado con Field).

    Returns:
        ReviewResponse: La reseña recién creada con su ID y timestamp.

    Raises:
        HTTPException 400: Si Supabase no devuelve datos (reseña no creada).
        HTTPException 500: Si ocurre un error inesperado.
    """
    try:
        # exclude_none=True omite campos opcionales que sean None
        # para no enviar valores nulos innecesarios a Supabase
        payload = data.model_dump(exclude_none=True)

        response = supabase.table("reviews").insert(payload).execute()

        if not response.data:
            raise HTTPException(status_code=400, detail="No se pudo guardar la reseña")

        # Devuelve el primer (y único) elemento insertado
        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=list[ReviewResponse])
async def get_reviews(
    barber_id: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
) -> list[ReviewResponse]:
    """
    Lista reseñas ordenadas por fecha de creación (más recientes primero).

    Args:
        barber_id (str, opcional): Si se proporciona, devuelve solo las reseñas
                                   de ese barbero específico.
        limit (int): Número máximo de reseñas a devolver. Máximo 100, default 20.
                     Evita cargar demasiados registros en una sola consulta.

    Returns:
        list[ReviewResponse]: Lista de reseñas con calificación y comentarios.

    Raises:
        HTTPException 500: Si ocurre un error al consultar Supabase.
    """
    try:
        query = (
            supabase.table("reviews")
            .select("*")
            .order("created_at", desc=True)  # Las más recientes primero
            .limit(limit)                     # Paginación básica por límite
        )

        # Filtra por barbero si se proporcionó el parámetro
        if barber_id:
            query = query.eq("barber_id", barber_id)

        response = query.execute()
        return response.data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/barber/{barber_id}/summary")
async def get_barber_rating_summary(barber_id: str) -> dict:
    """
    Devuelve un resumen estadístico de las calificaciones de un barbero.

    Útil para mostrar en el perfil del barbero: cuántas reseñas tiene,
    su promedio y cuántas personas dieron cada número de estrellas.

    Args:
        barber_id (str): UUID del barbero a analizar.

    Returns:
        dict con los campos:
            - barber_id    : UUID del barbero
            - total        : número total de reseñas
            - avg_rating   : promedio redondeado a 2 decimales
            - distribution : dict con conteo por estrella, ej: {"1":0,"2":1,"3":2,"4":5,"5":10}

    Raises:
        HTTPException 500: Si ocurre un error al consultar Supabase.
    """
    try:
        # Solo trae el campo rating para no traer datos innecesarios
        response = (
            supabase.table("reviews")
            .select("rating")
            .eq("barber_id", barber_id)
            .execute()
        )
        reviews = response.data

        # Si no tiene reseñas, devuelve estructura vacía en lugar de error
        if not reviews:
            return {
                "barber_id": barber_id,
                "total": 0,
                "avg_rating": 0,
                "distribution": {str(i): 0 for i in range(1, 6)},
            }

        total = len(reviews)

        # Calcula el promedio sumando todos los ratings y dividiendo entre el total
        avg = round(sum(r["rating"] for r in reviews) / total, 2)

        # Cuenta cuántas reseñas hay de cada calificación (1 a 5 estrellas)
        distribution = {
            str(i): sum(1 for r in reviews if r["rating"] == i)
            for i in range(1, 6)
        }

        return {
            "barber_id": barber_id,
            "total": total,
            "avg_rating": avg,
            "distribution": distribution,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import HairstyleResponse
from app.db.supabase_client import supabase

router = APIRouter(prefix="/hairstyles", tags=["Hairstyles"])


@router.get("/", response_model=list[HairstyleResponse])
async def get_hairstyles(
    category: str | None   = Query(default=None),
    face_shape: str | None = Query(default=None),
):
    """
    Lista cortes desde Supabase.
    Filtros opcionales: ?category=Fade  ?face_shape=Oval
    """
    try:
        query = supabase.table("hairstyles").select("*").order("popularity", desc=True)
        if category:
            query = query.eq("category", category)
        if face_shape:
            query = query.contains("suitable_for", [face_shape])
        rows = (query.execute()).data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [
        HairstyleResponse(
            id           = r["id"],
            name         = r["name"],
            category     = r["category"],
            description  = r.get("description"),
            price        = float(r["price"]),
            duration     = r.get("duration", 30),
            image_url    = r.get("image_url"),
            difficulty   = r.get("difficulty", "Medium"),
            popularity   = r.get("popularity", 80),
            tags         = r.get("tags") or [],
            suitable_for = r.get("suitable_for") or [],
        )
        for r in rows
    ]


@router.get("/{hairstyle_id}", response_model=HairstyleResponse)
async def get_hairstyle(hairstyle_id: str):
    try:
        r = supabase.table("hairstyles").select("*").eq("id", hairstyle_id).single().execute().data
    except Exception:
        raise HTTPException(status_code=404, detail="Corte no encontrado")

    return HairstyleResponse(
        id           = r["id"],
        name         = r["name"],
        category     = r["category"],
        description  = r.get("description"),
        price        = float(r["price"]),
        duration     = r.get("duration", 30),
        image_url    = r.get("image_url"),
        difficulty   = r.get("difficulty", "Medium"),
        popularity   = r.get("popularity", 80),
        tags         = r.get("tags") or [],
        suitable_for = r.get("suitable_for") or [],
    )

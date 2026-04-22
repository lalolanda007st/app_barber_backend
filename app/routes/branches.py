"""
Ruta /branches — lista las sucursales de la barbería.
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import BranchResponse
from app.db.supabase_client import supabase

router = APIRouter(prefix="/branches", tags=["Branches"])


@router.get("/", response_model=list[BranchResponse])
async def get_branches():
    """Lista todas las sucursales activas."""
    try:
        rows = (supabase.table("branches")
                .select("*")
                .eq("is_active", True)
                .execute()).data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [
        BranchResponse(
            id        = r["id"],
            name      = r["name"],
            address   = r.get("address"),
            phone     = r.get("phone"),
            city      = r.get("city"),
            is_active = r.get("is_active", True),
        )
        for r in rows
    ]


@router.get("/{branch_id}", response_model=BranchResponse)
async def get_branch(branch_id: str):
    try:
        r = (supabase.table("branches")
             .select("*")
             .eq("id", branch_id)
             .single()
             .execute()).data
    except Exception:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")

    return BranchResponse(
        id        = r["id"],
        name      = r["name"],
        address   = r.get("address"),
        phone     = r.get("phone"),
        city      = r.get("city"),
        is_active = r.get("is_active", True),
    )

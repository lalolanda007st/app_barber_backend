"""
barbers.py — Rutas para gestión y consulta de barberos.

Endpoints:
    GET  /barbers/                     → Lista barberos activos (con slots opcionales)
    GET  /barbers/{barber_id}          → Detalle de un barbero
    GET  /barbers/{barber_id}/availability → Slots libres y ocupados para una fecha
    GET  /barbers/{barber_id}/schedule → Horario semanal configurado

Tabla principal: barbers
    Columnas relevantes: full_name, avg_rating, is_active, avatar_url, branch_id

Los slots disponibles se calculan dinámicamente usando ScheduleService,
que combina barber_schedules + barber_schedule_overrides + appointments.
"""

from fastapi import APIRouter, HTTPException, Query

from app.db.supabase_client import supabase
from app.models.schemas import AvailabilityResponse, BarberResponse
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/barbers", tags=["Barbers"])

# Instancia singleton del servicio de horarios — se reutiliza entre requests
_sched = ScheduleService()


def _map(b: dict, free_slots: list[str] | None = None) -> BarberResponse:
    """
    Convierte una fila cruda de la tabla `barbers` a BarberResponse.

    Mapeo de columnas:
        full_name  → name
        avg_rating → rating
        is_active  → available
        avatar_url → photo_url

    Args:
        b:          Dict con los datos de la fila de `barbers`.
        free_slots: Lista de slots disponibles ya calculados. None = lista vacía.

    Returns:
        BarberResponse con los campos normalizados para la API.
    """
    return BarberResponse(
        id              = b["id"],
        name            = b.get("full_name") or "",
        specialty       = b.get("specialty") or "",
        bio             = b.get("bio"),
        photo_url       = b.get("avatar_url"),
        rating          = float(b.get("avg_rating") or 5.0),
        review_count    = b.get("review_count") or 0,
        available       = b.get("is_active", True),
        available_slots = free_slots or [],
        branch_id       = b.get("branch_id"),
    )


@router.get("/", response_model=list[BarberResponse])
async def get_barbers(
    date: str | None      = Query(default=None, description="Fecha YYYY-MM-DD para calcular slots libres"),
    branch_id: str | None = Query(default=None, description="UUID de sucursal para filtrar"),
) -> list[BarberResponse]:
    """
    Lista todos los barberos activos.

    Si se pasa `date`, cada barbero incluye su lista de slots disponibles
    para ese día, calculados según su horario configurado y las citas ya existentes.

    Si se pasa `branch_id`, solo retorna barberos de esa sucursal.

    Ejemplos:
        GET /barbers/
        GET /barbers/?date=2025-05-01
        GET /barbers/?date=2025-05-01&branch_id=uuid-sucursal
    """
    try:
        query = supabase.table("barbers").select("*").eq("is_active", True)
        if branch_id:
            query = query.eq("branch_id", branch_id)
        rows = query.execute().data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando barberos: {e}")

    result = []
    for b in rows:
        # Calcular slots solo si se pidió una fecha — evita consultas innecesarias
        free_slots = _sched.get_available_slots(b["id"], date) if date else []
        result.append(_map(b, free_slots))

    return result


@router.get("/{barber_id}", response_model=BarberResponse)
async def get_barber(
    barber_id: str,
    date: str | None = Query(default=None, description="Fecha YYYY-MM-DD para calcular slots libres"),
) -> BarberResponse:
    """
    Retorna el detalle de un barbero específico.

    Opcionalmente calcula sus slots disponibles para una fecha.

    Args:
        barber_id: UUID del barbero.
        date:      Fecha opcional "YYYY-MM-DD".

    Raises:
        404: Si el barbero no existe.
    """
    try:
        b = (
            supabase.table("barbers")
            .select("*")
            .eq("id", barber_id)
            .single()
            .execute()
        ).data
    except Exception:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")

    free_slots = _sched.get_available_slots(barber_id, date) if date else []
    return _map(b, free_slots)


@router.get("/{barber_id}/availability", response_model=AvailabilityResponse)
async def get_availability(
    barber_id: str,
    date: str = Query(..., description="Fecha YYYY-MM-DD requerida"),
) -> AvailabilityResponse:
    """
    Retorna los slots libres Y ocupados de un barbero para una fecha específica.

    Útil para mostrar en la UI un calendario visual donde se vean
    tanto los horarios disponibles como los ya reservados.

    Args:
        barber_id: UUID del barbero.
        date:      Fecha requerida "YYYY-MM-DD".

    Returns:
        AvailabilityResponse con available_slots y booked_slots separados.

    Ejemplo de respuesta:
        {
          "barber_id": "uuid",
          "date": "2025-05-01",
          "available_slots": ["09:00", "09:30", "11:00"],
          "booked_slots": ["10:00", "10:30"]
        }
    """
    data = _sched.get_full_availability(barber_id, date)
    return AvailabilityResponse(
        barber_id       = barber_id,
        date            = date,
        available_slots = data["available_slots"],
        booked_slots    = data["booked_slots"],
    )


@router.get("/{barber_id}/schedule", response_model=list[dict])
async def get_barber_schedule(barber_id: str) -> list[dict]:
    """
    Retorna el horario semanal completo configurado para un barbero.

    Cada elemento representa un día de la semana con su rango de atención
    y la duración de cada slot. Útil para la pantalla de administración.

    Args:
        barber_id: UUID del barbero.

    Returns:
        Lista de registros de barber_schedules ordenados por día.

    Ejemplo de un elemento:
        {
          "id": "uuid",
          "barber_id": "uuid",
          "day_of_week": "monday",
          "slot_start": "09:00:00",
          "slot_end": "18:00:00",
          "slot_duration_min": 30,
          "is_active": true
        }
    """
    return _sched.get_barber_schedule(barber_id)

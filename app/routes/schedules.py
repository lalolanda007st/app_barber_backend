"""
schedules.py — Gestión de horarios flexibles por barbero.

Permite que cada barbería configure exactamente cuándo trabaja cada barbero:
    - Qué días de la semana atiende
    - En qué rango horario (inicio y fin)
    - Cada cuántos minutos se genera un slot (ej. 30 o 45 minutos)
    - Excepciones puntuales: días libres, vacaciones, horario especial

Tablas:
    barber_schedules          → horario semanal recurrente
    barber_schedule_overrides → excepciones por fecha específica

Endpoints:
    GET    /schedules/barber/{barber_id}      → ver horario semanal
    POST   /schedules/                        → crear/editar horario de un día
    DELETE /schedules/{schedule_id}           → eliminar horario de un día
    POST   /schedules/override                → agregar excepción (feriado/vacación)
    GET    /schedules/overrides/{barber_id}   → ver excepciones del barbero
    DELETE /schedules/override/{override_id}  → eliminar una excepción
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.supabase_client import supabase

router = APIRouter(prefix="/schedules", tags=["Schedules"])

# Días válidos según el enum day_of_week en Supabase
_VALID_DAYS = frozenset({
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
})


# ── Schemas de request ────────────────────────────────────────────────────────

class ScheduleUpsertRequest(BaseModel):
    """
    Cuerpo para crear o actualizar el horario de un barbero en un día específico.

    Si ya existe un registro para (barber_id, day_of_week, branch_id),
    se sobreescribe con los nuevos valores (upsert).

    Campos:
        barber_id:         UUID del barbero.
        branch_id:         UUID de la sucursal donde trabaja.
        day_of_week:       Día de la semana en inglés minúsculas.
                           Valores: monday | tuesday | wednesday | thursday |
                                    friday | saturday | sunday
        slot_start:        Hora de inicio en formato "HH:MM". Ej: "09:00"
        slot_end:          Hora de fin en formato "HH:MM". Ej: "18:00"
                           El último slot generado termina en slot_end,
                           no en slot_end + duration.
        slot_duration_min: Duración de cada slot en minutos (10-240). Default: 30.
        is_active:         Si el barbero trabaja este día. Default: true.
    """
    barber_id: str
    branch_id: str
    day_of_week: str
    slot_start: str
    slot_end: str
    slot_duration_min: int = 30
    is_active: bool = True


class OverrideRequest(BaseModel):
    """
    Cuerpo para agregar una excepción de horario en una fecha específica.

    Las excepciones tienen prioridad sobre el horario semanal base.
    Si ya existe un override para (barber_id, override_date), se sobreescribe.

    Casos de uso:
        - Día libre: is_day_off=True (sin custom_start/end)
        - Horario reducido: is_day_off=False, custom_start="10:00", custom_end="14:00"
        - Feriado con label: is_day_off=True, reason="Navidad"

    Campos:
        barber_id:     UUID del barbero.
        override_date: Fecha exacta "YYYY-MM-DD".
        is_day_off:    True = el barbero no trabaja ese día. Default: false.
        custom_start:  Hora de inicio alternativa "HH:MM". None = usar la del horario base.
        custom_end:    Hora de fin alternativa "HH:MM". None = usar la del horario base.
        reason:        Descripción opcional. Ej: "Feriado nacional", "Vacaciones".
    """
    barber_id: str
    override_date: str
    is_day_off: bool = False
    custom_start: Optional[str] = None
    custom_end: Optional[str] = None
    reason: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/barber/{barber_id}")
async def get_barber_schedules(barber_id: str) -> list[dict]:
    """
    Retorna todos los horarios semanales configurados de un barbero.

    Cada elemento indica qué días trabaja el barbero, en qué rango horario
    y cada cuántos minutos tiene un slot disponible.

    Args:
        barber_id: UUID del barbero.

    Returns:
        Lista de registros de barber_schedules ordenados por día.
        Lista vacía si el barbero no tiene horarios configurados.
    """
    try:
        return (
            supabase.table("barber_schedules")
            .select("*")
            .eq("barber_id", barber_id)
            .order("day_of_week")
            .execute()
        ).data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def upsert_schedule(data: ScheduleUpsertRequest) -> dict:
    """
    Crea o actualiza el horario de un barbero para un día de la semana.

    Si ya existe un horario para la combinación (barber_id, day_of_week, branch_id),
    lo sobreescribe completamente con los nuevos valores.

    Validaciones:
        - day_of_week debe ser un día válido en inglés
        - slot_start y slot_end deben estar en formato "HH:MM"
        - slot_duration_min debe estar entre 10 y 240 minutos

    Args:
        data: ScheduleUpsertRequest con los datos del horario.

    Returns:
        Dict con success, message y el registro guardado.

    Raises:
        400: Si los datos son inválidos.
        500: Si hay error de base de datos.
    """
    # Validar día de la semana
    _validate_day(data.day_of_week)

    # Validar formato de horas
    _validate_time(data.slot_start, "slot_start")
    _validate_time(data.slot_end,   "slot_end")

    # Validar que slot_end sea posterior a slot_start
    if data.slot_start >= data.slot_end:
        raise HTTPException(
            status_code=400,
            detail="slot_end debe ser posterior a slot_start")

    # Validar duración del slot
    if not (10 <= data.slot_duration_min <= 240):
        raise HTTPException(
            status_code=400,
            detail="slot_duration_min debe estar entre 10 y 240 minutos")

    try:
        result = (
            supabase.table("barber_schedules")
            .upsert(
                {
                    "barber_id"        : data.barber_id,
                    "branch_id"        : data.branch_id,
                    "day_of_week"      : data.day_of_week,
                    "slot_start"       : data.slot_start,
                    "slot_end"         : data.slot_end,
                    "slot_duration_min": data.slot_duration_min,
                    "is_active"        : data.is_active,
                },
                on_conflict="barber_id,day_of_week,branch_id",
            )
            .execute()
        ).data[0]
        return {"success": True, "message": "Horario guardado", "schedule": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str) -> dict:
    """
    Elimina el horario de un día específico para un barbero.

    Después de eliminar, el barbero no tendrá slots disponibles
    para ese día de la semana a menos que se vuelva a configurar.

    Args:
        schedule_id: UUID del registro en barber_schedules.

    Returns:
        Dict con success y message de confirmación.

    Raises:
        500: Si hay error de base de datos.
    """
    try:
        supabase.table("barber_schedules").delete().eq("id", schedule_id).execute()
        return {"success": True, "message": "Horario eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/override")
async def create_override(data: OverrideRequest) -> dict:
    """
    Agrega una excepción de horario para una fecha específica.

    Las excepciones anulan el horario semanal recurrente para ese día.
    Si ya existe un override para el mismo barbero y fecha, se sobreescribe.

    Ejemplos de uso:
        # Día completamente libre (feriado)
        POST /schedules/override
        {"barber_id": "uuid", "override_date": "2025-12-25", "is_day_off": true, "reason": "Navidad"}

        # Horario reducido ese día
        POST /schedules/override
        {"barber_id": "uuid", "override_date": "2025-05-10",
         "is_day_off": false, "custom_start": "10:00", "custom_end": "14:00"}

    Args:
        data: OverrideRequest con los datos de la excepción.

    Returns:
        Dict con success, message y el registro guardado.
    """
    try:
        result = (
            supabase.table("barber_schedule_overrides")
            .upsert(
                {
                    "barber_id"    : data.barber_id,
                    "override_date": data.override_date,
                    "is_day_off"   : data.is_day_off,
                    "custom_start" : data.custom_start,
                    "custom_end"   : data.custom_end,
                    "reason"       : data.reason,
                },
                on_conflict="barber_id,override_date",
            )
            .execute()
        ).data[0]
        return {"success": True, "message": "Excepción guardada", "override": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overrides/{barber_id}")
async def get_overrides(barber_id: str) -> list[dict]:
    """
    Lista todas las excepciones de horario configuradas para un barbero.

    Útil para mostrar en la UI del administrador un calendario con
    los días especiales marcados (vacaciones, feriados, etc.).

    Args:
        barber_id: UUID del barbero.

    Returns:
        Lista de registros de barber_schedule_overrides ordenados por fecha.
    """
    try:
        return (
            supabase.table("barber_schedule_overrides")
            .select("*")
            .eq("barber_id", barber_id)
            .order("override_date")
            .execute()
        ).data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/override/{override_id}")
async def delete_override(override_id: str) -> dict:
    """
    Elimina una excepción de horario.

    Después de eliminar, el barbero vuelve a su horario semanal normal
    para esa fecha.

    Args:
        override_id: UUID del registro en barber_schedule_overrides.

    Returns:
        Dict con success y message de confirmación.
    """
    try:
        supabase.table("barber_schedule_overrides").delete().eq("id", override_id).execute()
        return {"success": True, "message": "Excepción eliminada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Funciones de validación ───────────────────────────────────────────────────

def _validate_day(day: str) -> None:
    """
    Valida que el día sea uno de los valores aceptados por el enum de Supabase.

    Args:
        day: String a validar.

    Raises:
        HTTPException 400: Si el día no es válido.
    """
    if day not in _VALID_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"day_of_week inválido: '{day}'. "
                   f"Valores válidos: {', '.join(sorted(_VALID_DAYS))}",
        )


def _validate_time(t: str, field_name: str = "time") -> None:
    """
    Valida que la hora esté en formato "HH:MM" con valores numéricos correctos.

    Args:
        t:          String de hora a validar.
        field_name: Nombre del campo para el mensaje de error.

    Raises:
        HTTPException 400: Si el formato o los valores son inválidos.
    """
    parts = t.split(":")
    if len(parts) != 2:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} tiene formato inválido: '{t}'. Usa HH:MM (ej: 09:00)",
        )
    try:
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} tiene hora inválida: '{t}'. "
                   f"Horas 0-23, minutos 0-59",
        )

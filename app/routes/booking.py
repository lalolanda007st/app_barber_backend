"""
booking.py — Gestión de citas (appointments).

Endpoints:
    POST /booking/                        → Crear cita con validación completa
    POST /booking/cancel                  → Cancelar cita existente
    GET  /booking/client/{client_phone}   → Historial de citas por teléfono

Tabla principal: appointments
    Columnas: id, branch_id, barber_id, service_id, client_name, client_phone,
              client_email, scheduled_at (timestamptz), status, notes, user_id

El campo scheduled_at es un timestamp ISO completo: "2025-05-01T10:00:00"
La validación anti double-booking extrae la hora (HH:MM) y compara con
las citas existentes del mismo barbero en el mismo día.
"""

from fastapi import APIRouter, HTTPException

from app.db.supabase_client import supabase
from app.models.schemas import (
    BookingCancelRequest,
    BookingRequest,
    BookingResponse,
)

router = APIRouter(prefix="/booking", tags=["Booking"])


def _parse_date_time(scheduled_at: str) -> tuple[str, str]:
    """
    Extrae la fecha y la hora de un string ISO datetime.

    Acepta formatos con T o con espacio como separador:
        "2025-05-01T10:00:00"  → ("2025-05-01", "10:00")
        "2025-05-01 10:00:00"  → ("2025-05-01", "10:00")
        "2025-05-01T10:00"     → ("2025-05-01", "10:00")

    Args:
        scheduled_at: String de fecha y hora.

    Returns:
        Tupla (date_str, time_str) con formato "YYYY-MM-DD" y "HH:MM".
    """
    # Normalizar separador — algunos clientes envían espacio en lugar de T
    dt    = scheduled_at.replace(" ", "T")
    parts = dt.split("T")
    date  = parts[0]
    time  = parts[1][:5] if len(parts) > 1 else "00:00"
    return date, time


@router.post("/", response_model=BookingResponse)
async def create_booking(data: BookingRequest) -> BookingResponse:
    """
    Crea una nueva cita en la tabla appointments.

    Validaciones en orden:
        1. El barbero existe y tiene is_active=True
        2. El servicio existe y tiene is_active=True
        3. No hay otra cita para el mismo barbero a la misma hora ese día
           (anti double-booking consultando appointments existentes)
        4. Inserción en DB — el UNIQUE constraint de Supabase actúa como
           segunda línea de defensa contra condiciones de carrera

    Args:
        data: BookingRequest con todos los datos de la cita.

    Returns:
        BookingResponse con success=True, el ID de la cita y su status.

    Raises:
        404: Barbero o servicio no encontrado.
        409: Barbero no disponible o slot ya ocupado.
        500: Error interno de base de datos.

    Ejemplo de body:
        {
          "barber_id": "uuid-barbero",
          "service_id": "uuid-servicio",
          "client_name": "Juan Pérez",
          "client_phone": "+52 55 1234 5678",
          "client_email": "juan@email.com",
          "scheduled_at": "2025-05-01T10:00:00",
          "branch_id": "uuid-sucursal",
          "notes": "Primera vez, prefiero degradado suave"
        }
    """
    date_str, time_str = _parse_date_time(data.scheduled_at)

    # ── 1. Verificar que el barbero existe y está activo ──────────────────────
    try:
        barber = (
            supabase.table("barbers")
            .select("id, is_active")
            .eq("id", data.barber_id)
            .single()
            .execute()
        ).data
    except Exception:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")

    if not barber.get("is_active", True):
        raise HTTPException(status_code=409, detail="El barbero no está disponible actualmente")

    # ── 2. Verificar que el servicio existe y está activo ─────────────────────
    try:
        service = (
            supabase.table("services")
            .select("id, is_active")
            .eq("id", data.service_id)
            .single()
            .execute()
        ).data
        if not service:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    # ── 3. Anti double-booking ────────────────────────────────────────────────
    # Buscar citas del mismo barbero en el mismo día y comparar la hora
    try:
        start = f"{date_str}T00:00:00"
        end   = f"{date_str}T23:59:59"

        existing = (
            supabase.table("appointments")
            .select("id, scheduled_at")
            .eq("barber_id", data.barber_id)
            .neq("status", "cancelled")   # ignorar canceladas
            .gte("scheduled_at", start)
            .lte("scheduled_at", end)
            .execute()
        ).data or []

        for appt in existing:
            existing_ts   = appt.get("scheduled_at", "")
            existing_hhmm = existing_ts.split("T")[1][:5] if "T" in existing_ts else ""
            if existing_hhmm == time_str:
                raise HTTPException(
                    status_code=409,
                    detail=f"El horario {time_str} del {date_str} ya está ocupado. "
                           f"Por favor elige otro horario.",
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # ── 4. Insertar la cita ───────────────────────────────────────────────────
    try:
        # Normalizar scheduled_at a formato ISO estándar
        scheduled_iso = f"{date_str}T{time_str}:00"

        insert_data: dict = {
            "barber_id"   : data.barber_id,
            "service_id"  : data.service_id,
            "client_name" : data.client_name,
            "client_phone": data.client_phone,
            "client_email": data.client_email,
            "scheduled_at": scheduled_iso,
            "notes"       : data.notes,
            "status"      : "confirmed",
        }

        # branch_id es opcional — solo se agrega si se proporcionó
        if data.branch_id:
            insert_data["branch_id"] = data.branch_id

        appointment = (
            supabase.table("appointments")
            .insert(insert_data)
            .execute()
        ).data[0]

    except Exception as e:
        # Si el UNIQUE constraint de DB detecta un conflicto de concurrencia
        if "unique" in str(e).lower() or "23505" in str(e):
            raise HTTPException(
                status_code=409,
                detail="Ese horario acaba de ser reservado por otro cliente. "
                       "Por favor elige otro.",
            )
        raise HTTPException(status_code=500, detail=str(e))

    return BookingResponse(
        success    = True,
        message    = f"Cita confirmada para el {date_str} a las {time_str}",
        booking_id = appointment["id"],
        status     = appointment["status"],
    )


@router.post("/cancel", response_model=BookingResponse)
async def cancel_booking(data: BookingCancelRequest) -> BookingResponse:
    """
    Cancela una cita cambiando su status a 'cancelled'.

    No elimina el registro — mantiene el historial de la cita.
    Los slots cancelados quedan disponibles automáticamente para nuevas reservas.

    Args:
        data: BookingCancelRequest con el booking_id a cancelar.

    Returns:
        BookingResponse con success=True y status='cancelled'.

    Raises:
        404: Si la cita no se encuentra.
        500: Error de base de datos.
    """
    try:
        res = (
            supabase.table("appointments")
            .update({"status": "cancelled"})
            .eq("id", data.booking_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Cita no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return BookingResponse(
        success    = True,
        message    = "Cita cancelada correctamente",
        booking_id = data.booking_id,
        status     = "cancelled",
    )


@router.get("/client/{client_phone}", response_model=list[dict])
async def get_client_bookings(client_phone: str) -> list[dict]:
    """
    Retorna el historial de citas de un cliente buscando por su teléfono.

    Incluye datos del barbero y del servicio via JOIN automático de Supabase.
    Las citas se ordenan de más reciente a más antigua.

    Args:
        client_phone: Número de teléfono del cliente (exacto, tal como se guardó).

    Returns:
        Lista de citas con datos anidados de barbers y services.

    Ejemplo de un elemento:
        {
          "id": "uuid",
          "scheduled_at": "2025-05-01T10:00:00+00:00",
          "status": "confirmed",
          "barbers": {"full_name": "Carlos", "avatar_url": "..."},
          "services": {"name": "Fade Clásico", "price": 250}
        }
    """
    try:
        return (
            supabase.table("appointments")
            # JOIN con barbers y services para datos completos en una sola consulta
            .select("*, barbers(full_name, avatar_url), services(name, price)")
            .eq("client_phone", client_phone)
            .order("scheduled_at", desc=True)
            .execute()
        ).data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

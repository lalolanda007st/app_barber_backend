"""
schedule_service.py — Servicio de generación de slots de disponibilidad.

Responsabilidad:
    Calcular los horarios disponibles de un barbero para una fecha específica,
    combinando tres fuentes de información:
        1. barber_schedules   → horario semanal base (qué días y en qué rango trabaja)
        2. barber_schedule_overrides → excepciones puntuales (feriados, vacaciones, horario especial)
        3. appointments       → citas ya reservadas (slots ocupados)

Flujo principal (get_available_slots):
    fecha → día de la semana → horario base → override? → generar slots → descontar ocupados → retornar libres

Uso:
    from app.services.schedule_service import ScheduleService
    sched = ScheduleService()
    slots = sched.get_available_slots("barber-uuid", "2025-05-01")
    # → ["09:00", "09:30", "10:00", ...]
"""

from __future__ import annotations

from datetime import datetime
from datetime import time as dt_time

from app.db.supabase_client import supabase

# ---------------------------------------------------------------------------
# Mapeo de weekday() de Python al nombre usado en la columna day_of_week de DB
# Python: lunes=0, martes=1, ..., domingo=6
# ---------------------------------------------------------------------------
_WEEKDAY_MAP: dict[int, str] = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}


class ScheduleService:
    """
    Servicio que encapsula toda la lógica de horarios de barberos.

    No tiene estado interno — puede instanciarse una sola vez y reutilizarse
    en múltiples requests (patrón singleton en las rutas).
    """

    # ── API pública ───────────────────────────────────────────────────────────

    def get_available_slots(self, barber_id: str, date_str: str) -> list[str]:
        """
        Retorna los slots libres de un barbero para una fecha dada.

        Args:
            barber_id: UUID del barbero en Supabase.
            date_str:  Fecha en formato "YYYY-MM-DD".

        Returns:
            Lista ordenada de strings "HH:MM" de los slots disponibles.
            Lista vacía si el barbero no trabaja ese día o tiene día libre.

        Ejemplo:
            >>> sched.get_available_slots("abc-123", "2025-05-01")
            ["09:00", "09:30", "10:00", "10:30", ...]
        """
        date     = datetime.strptime(date_str, "%Y-%m-%d").date()
        day_name = _WEEKDAY_MAP[date.weekday()]

        # Paso 1: verificar si hay excepción para esta fecha exacta
        override = self._get_override(barber_id, date_str)
        if override and override.get("is_day_off"):
            return []  # Día libre — sin slots

        # Paso 2: obtener horario base del día de la semana
        schedule = self._get_schedule(barber_id, day_name)
        if not schedule:
            return []  # El barbero no trabaja ese día de la semana

        # Paso 3: determinar rango efectivo (el override puede cambiar las horas)
        if override and override.get("custom_start"):
            start_str = override["custom_start"]
            end_str   = override.get("custom_end") or schedule["slot_end"]
        else:
            start_str = schedule["slot_start"]
            end_str   = schedule["slot_end"]

        duration_min = schedule["slot_duration_min"]

        # Paso 4: generar todos los slots posibles del rango
        all_slots = self._generate_slots(start_str, end_str, duration_min)

        # Paso 5: descontar los slots ya reservados en appointments
        booked = self._get_booked_slots(barber_id, date_str)

        return [s for s in all_slots if s not in booked]

    def get_full_availability(self, barber_id: str, date_str: str) -> dict:
        """
        Retorna slots libres Y ocupados para mostrar en la pantalla de disponibilidad.

        Útil para que la UI muestre visualmente qué horarios están tomados
        y cuáles están disponibles.

        Args:
            barber_id: UUID del barbero.
            date_str:  Fecha "YYYY-MM-DD".

        Returns:
            Dict con:
                available_slots: list[str] — slots libres "HH:MM"
                booked_slots:    list[str] — slots ocupados "HH:MM"
                is_day_off:      bool      — True si el barbero no trabaja ese día
        """
        date     = datetime.strptime(date_str, "%Y-%m-%d").date()
        day_name = _WEEKDAY_MAP[date.weekday()]

        # Verificar excepción de día libre
        override = self._get_override(barber_id, date_str)
        if override and override.get("is_day_off"):
            return {"available_slots": [], "booked_slots": [], "is_day_off": True}

        # Verificar horario base
        schedule = self._get_schedule(barber_id, day_name)
        if not schedule:
            return {"available_slots": [], "booked_slots": [], "is_day_off": False}

        # Determinar rango (puede estar modificado por override)
        start_str    = (override.get("custom_start") or schedule["slot_start"]) if override else schedule["slot_start"]
        end_str      = (override.get("custom_end")   or schedule["slot_end"])   if override else schedule["slot_end"]
        duration_min = schedule["slot_duration_min"]

        all_slots = self._generate_slots(start_str, end_str, duration_min)
        booked    = self._get_booked_slots(barber_id, date_str)

        return {
            "available_slots": [s for s in all_slots if s not in booked],
            "booked_slots"   : sorted(booked),
            "is_day_off"     : False,
        }

    def get_barber_schedule(self, barber_id: str) -> list[dict]:
        """
        Retorna el horario semanal completo configurado para un barbero.

        Útil para la pantalla de administración donde el dueño de la barbería
        puede ver y editar los horarios de cada barbero.

        Args:
            barber_id: UUID del barbero.

        Returns:
            Lista de filas de barber_schedules, una por día activo.
        """
        try:
            return (
                supabase.table("barber_schedules")
                .select("*")
                .eq("barber_id", barber_id)
                .eq("is_active", True)
                .execute()
            ).data or []
        except Exception:
            return []

    # ── Métodos privados ──────────────────────────────────────────────────────

    def _get_schedule(self, barber_id: str, day_name: str) -> dict | None:
        """
        Busca el horario configurado para un barbero en un día de la semana.

        Args:
            barber_id: UUID del barbero.
            day_name:  Nombre del día en inglés minúsculas ("monday", "tuesday", etc.).

        Returns:
            Dict con los datos de barber_schedules o None si no trabaja ese día.
        """
        try:
            rows = (
                supabase.table("barber_schedules")
                .select("*")
                .eq("barber_id", barber_id)
                .eq("day_of_week", day_name)
                .eq("is_active", True)
                .execute()
            ).data or []
            return rows[0] if rows else None
        except Exception:
            return None

    def _get_override(self, barber_id: str, date_str: str) -> dict | None:
        """
        Busca si existe una excepción de horario para una fecha específica.

        Las excepciones tienen prioridad sobre el horario semanal base.
        Casos de uso: feriados, vacaciones, horario reducido un día especial.

        Args:
            barber_id: UUID del barbero.
            date_str:  Fecha exacta "YYYY-MM-DD".

        Returns:
            Dict de barber_schedule_overrides o None si no hay excepción.
        """
        try:
            rows = (
                supabase.table("barber_schedule_overrides")
                .select("*")
                .eq("barber_id", barber_id)
                .eq("override_date", date_str)
                .execute()
            ).data or []
            return rows[0] if rows else None
        except Exception:
            return None

    def _generate_slots(
        self,
        start_str: str,
        end_str: str,
        duration_min: int,
    ) -> list[str]:
        """
        Genera la lista de slots de tiempo entre start y end con pasos de duration_min.

        El último slot generado es el que aún cabe dentro del rango:
        si duration=30 y end=18:00, el último slot es 17:30 (no 18:00).

        Args:
            start_str:    Hora de inicio "HH:MM" o "HH:MM:SS".
            end_str:      Hora de fin "HH:MM" o "HH:MM:SS".
            duration_min: Duración de cada slot en minutos.

        Returns:
            Lista ordenada de strings "HH:MM".

        Ejemplo:
            >>> _generate_slots("09:00", "11:00", 30)
            ["09:00", "09:30", "10:00", "10:30"]
        """
        try:
            # Normalizar a "HH:MM" eliminando segundos si los hay
            start_parts = start_str[:5].split(":")
            end_parts   = end_str[:5].split(":")

            start = dt_time(int(start_parts[0]), int(start_parts[1]))
            end   = dt_time(int(end_parts[0]),   int(end_parts[1]))

            # Convertir a minutos desde medianoche para aritmética simple
            start_min = start.hour * 60 + start.minute
            end_min   = end.hour   * 60 + end.minute

            slots: list[str] = []
            current = start_min

            # Generar slots mientras quede espacio para un slot completo
            while current + duration_min <= end_min:
                h = current // 60
                m = current % 60
                slots.append(f"{h:02d}:{m:02d}")
                current += duration_min

            return slots

        except Exception:
            return []

    def _get_booked_slots(self, barber_id: str, date_str: str) -> set[str]:
        """
        Consulta las citas ya reservadas para un barbero en una fecha.

        Filtra por rango del día completo en scheduled_at y extrae la hora
        de cada cita para comparar con los slots generados.

        Args:
            barber_id: UUID del barbero.
            date_str:  Fecha "YYYY-MM-DD".

        Returns:
            Set de strings "HH:MM" de slots ya ocupados.
            Set vacío si no hay citas o si ocurre un error.
        """
        try:
            # Filtrar appointments del día completo usando rango de timestamps
            start = f"{date_str}T00:00:00"
            end   = f"{date_str}T23:59:59"

            rows = (
                supabase.table("appointments")
                .select("scheduled_at")
                .eq("barber_id", barber_id)
                .neq("status", "cancelled")   # ignorar citas canceladas
                .gte("scheduled_at", start)
                .lte("scheduled_at", end)
                .execute()
            ).data or []

            booked: set[str] = set()
            for r in rows:
                scheduled_at = r.get("scheduled_at", "")
                if "T" in scheduled_at:
                    # Extraer "HH:MM" del timestamp "YYYY-MM-DDTHH:MM:SS+TZ"
                    booked.add(scheduled_at.split("T")[1][:5])

            return booked

        except Exception:
            # En caso de error, retornar set vacío para no bloquear al usuario
            return set()

"""
Schemas Pydantic para todos los endpoints de BarberVision.
Ajustados al esquema real de Supabase.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    service: str


# ── Preview ───────────────────────────────────────────────────────────────────

class PreviewResponse(BaseModel):
    success: bool
    message: str
    hairstyle_id: Optional[str] = None
    hairstyle_name: Optional[str] = None
    hairstyle_category: Optional[str] = None
    preview_image_url: Optional[str] = None
    used_segmentation: Optional[bool] = None
    face_detected: Optional[bool] = None


# ── Services (cortes) ─────────────────────────────────────────────────────────

class HairstyleResponse(BaseModel):
    id: str
    name: str
    category: str = "General"
    description: Optional[str] = None
    price: float
    duration: int = 30          # duration_min en DB
    image_url: Optional[str] = None
    difficulty: str = "Medium"
    popularity: int = 80
    tags: List[str] = []
    suitable_for: List[str] = []
    branch_id: Optional[str] = None


# ── Face shape ────────────────────────────────────────────────────────────────

class FaceShapeResponse(BaseModel):
    face_shape: str
    confidence: float
    recommended_hairstyle_ids: List[str]
    explanation: str


# ── Branches (sucursales) ─────────────────────────────────────────────────────

class BranchResponse(BaseModel):
    id: str
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    is_active: bool = True


# ── Barbers ───────────────────────────────────────────────────────────────────

class BarberResponse(BaseModel):
    id: str
    name: str                   # full_name en DB
    specialty: str = ""
    bio: Optional[str] = None
    photo_url: Optional[str] = None   # avatar_url en DB
    rating: float = 5.0         # avg_rating en DB
    review_count: int = 0
    available: bool = True      # is_active en DB
    available_slots: List[str] = []
    branch_id: Optional[str] = None


# ── Availability ──────────────────────────────────────────────────────────────

class AvailabilityResponse(BaseModel):
    barber_id: str
    date: str
    available_slots: List[str]
    booked_slots: List[str]


# ── Appointments (citas) ──────────────────────────────────────────────────────

class BookingRequest(BaseModel):
    barber_id: str
    service_id: str             # hairstyle_id → service_id
    client_name: str
    client_phone: Optional[str] = None
    client_email: Optional[str] = None
    scheduled_at: str           # ISO datetime: "2025-05-01T10:00:00"
    branch_id: Optional[str] = None
    notes: Optional[str] = None


class BookingResponse(BaseModel):
    success: bool
    message: str
    booking_id: Optional[str] = None
    status: Optional[str] = None


class BookingCancelRequest(BaseModel):
    booking_id: str


# ── Reviews ───────────────────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    barber_id: str
    appointment_id: Optional[str] = None   # booking_id → appointment_id
    client_name: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    success: bool
    message: str
    review_id: Optional[str] = None
    new_barber_rating: Optional[float] = None

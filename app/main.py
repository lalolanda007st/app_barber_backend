"""
BarberVision API v2.2 — con horarios flexibles por barbero.
"""
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import OUTPUTS_DIR
from app.routes.health      import router as health_router
from app.routes.preview     import router as preview_router
from app.routes.hairstyles  import router as hairstyles_router
from app.routes.booking     import router as booking_router
from app.routes.barbers     import router as barbers_router
from app.routes.reviews     import router as reviews_router
from app.routes.face_shape  import router as face_shape_router
from app.routes.auth        import router as auth_router
from app.routes.branches    import router as branches_router
from app.routes.schedules   import router as schedules_router

app = FastAPI(title="BarberVision API", version="2.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(preview_router)
app.include_router(hairstyles_router)
app.include_router(booking_router)
app.include_router(barbers_router)
app.include_router(reviews_router)
app.include_router(face_shape_router)
app.include_router(branches_router)
app.include_router(schedules_router)

app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.models.schemas import PreviewResponse
from app.services.preview_service import PreviewService

router = APIRouter(prefix="/preview", tags=["Preview"])
preview_service = PreviewService()


@router.post("/", response_model=PreviewResponse)
async def generate_preview(
    file: UploadFile = File(...),
    hairstyle_id: str | None = Form(default=None),
    hairstyle_name: str | None = Form(default=None),
    hairstyle_category: str | None = Form(default=None),
) -> PreviewResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
    try:
        result = preview_service.process(
            file=file,
        hairstyle_id=hairstyle_id,
        hairstyle_name=hairstyle_name,
        hairstyle_category=hairstyle_category,
    )
        return PreviewResponse(**result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

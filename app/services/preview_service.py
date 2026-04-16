from pathlib import Path
from uuid import uuid4
from PIL import Image, ImageDraw


class PreviewService:
    def process_preview(
        self,
        image_path: Path,
        hairstyle_id: str | None,
        hairstyle_name: str | None,
    ) -> dict:
        with Image.open(image_path) as img:
            img = img.convert("RGB")

            draw = ImageDraw.Draw(img)
            label = hairstyle_name or "Corte sin nombre"

            # Marca simple para probar que el backend sí regresó una imagen nueva
            draw.rectangle([(20, 20), (420, 100)], fill=(0, 0, 0))
            draw.text((30, 45), f"Preview: {label}", fill=(212, 168, 83))

            output_name = f"{uuid4().hex}.jpg"
            output_path = Path("outputs") / output_name
            img.save(output_path, format="JPEG", quality=90)

        return {
            "success": True,
            "message": "Preview generada correctamente",
            "hairstyle_id": hairstyle_id,
            "hairstyle_name": hairstyle_name,
            "original_filename": image_path.name,
            "saved_input_path": str(image_path),
            "preview_image_url": f"/outputs/{output_name}",
        }

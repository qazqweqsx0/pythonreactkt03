"""Backend: загрузка изображений, создание миниатюр и отдача файлов клиенту.

Практическое задание 3.3 — «Отдача файлов клиенту и отображение в React».
"""

from __future__ import annotations

import io
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
ORIGINALS_DIR = UPLOAD_DIR / "originals"
THUMBNAILS_DIR = UPLOAD_DIR / "thumbnails"

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 МБ
ALLOWED_TYPES = {"image/png": ".png", "image/jpeg": ".jpg"}
ALLOWED_FORMATS = {"PNG": ".png", "JPEG": ".jpg"}
THUMBNAIL_SIZE = (320, 320)

ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Image Upload API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Папка с изображениями раздаётся как статика:
# /uploads/originals/<file> и /uploads/thumbnails/<file>.
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


def build_public_url(request: Request, path: str) -> str:
    """Возвращает полный URL (с http://...), а не относительный путь."""
    base = os.getenv("PUBLIC_BASE_URL") or str(request.base_url)
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def validate_and_open(data: bytes, content_type: str) -> tuple[Image.Image, str]:
    """Проверяет тип/размер/содержимое файла и возвращает изображение + расширение."""
    if not data:
        raise HTTPException(status_code=400, detail="Файл пустой. Выберите изображение.")

    if len(data) > MAX_FILE_SIZE:
        size_mb = len(data) / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=(
                f"Файл слишком большой: {size_mb:.2f} МБ. "
                f"Максимальный размер — {MAX_FILE_SIZE // (1024 * 1024)} МБ."
            ),
        )

    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Неподдерживаемый формат файла. Разрешены только PNG и JPEG.",
        )

    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=400,
            detail="Не удалось прочитать изображение. Файл повреждён или не является картинкой.",
        )

    extension = ALLOWED_FORMATS.get(image.format or "")
    if extension is None:
        raise HTTPException(
            status_code=400,
            detail="Неподдерживаемый формат файла. Разрешены только PNG и JPEG.",
        )

    return image, extension


def make_thumbnail(image: Image.Image, destination: Path) -> None:
    """Создаёт миниатюру с сохранением пропорций и сохраняет её отдельно от оригинала."""
    thumbnail = image.copy()
    thumbnail.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

    if thumbnail.mode not in ("RGB", "L"):
        thumbnail = thumbnail.convert("RGB")

    if destination.suffix.lower() in (".jpg", ".jpeg"):
        thumbnail.save(destination, format="JPEG", quality=85, optimize=True)
    else:
        thumbnail.save(destination, format="PNG", optimize=True)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_image(request: Request, file: UploadFile = File(...)) -> dict:
    data = await file.read()
    image, extension = validate_and_open(data, file.content_type or "")

    file_id = uuid.uuid4().hex
    original_name = f"{file_id}{extension}"
    thumbnail_name = f"{file_id}_thumb{extension}"

    original_path = ORIGINALS_DIR / original_name
    thumbnail_path = THUMBNAILS_DIR / thumbnail_name

    original_path.write_bytes(data)
    make_thumbnail(image, thumbnail_path)

    return {
        "id": file_id,
        "filename": file.filename,
        "size": len(data),
        "width": image.width,
        "height": image.height,
        "original_url": build_public_url(request, f"uploads/originals/{original_name}"),
        "thumbnail_url": build_public_url(request, f"uploads/thumbnails/{thumbnail_name}"),
    }


@app.get("/api/images")
def list_images(request: Request) -> list[dict]:
    """Список ранее загруженных изображений (свежие — первыми)."""
    images = []
    for original in sorted(
        ORIGINALS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        if not original.is_file():
            continue
        thumbnail = THUMBNAILS_DIR / f"{original.stem}_thumb{original.suffix}"
        if not thumbnail.exists():
            continue
        images.append(
            {
                "id": original.stem,
                "filename": original.name,
                "original_url": build_public_url(request, f"uploads/originals/{original.name}"),
                "thumbnail_url": build_public_url(
                    request, f"uploads/thumbnails/{thumbnail.name}"
                ),
            }
        )
    return images

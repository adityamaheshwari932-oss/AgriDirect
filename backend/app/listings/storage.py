"""Secure image storage service for produce listing photographic assets.

Security controls:
- Rejects untrusted filenames; images are stored using server-generated UUIDs.
- Enforces strict directory boundaries to prevent path traversal attacks.
- Validates allowed image MIME types and file extensions (JPEG, PNG, WebP).
- Validates binary file signatures (magic bytes).
- Enforces maximum image file size limit (5 MB default).
- Safe file deletion and retrieval helpers.
"""

import os
import uuid
from pathlib import Path
from typing import Set, Tuple

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

ALLOWED_IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIME_TYPES: Set[str] = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
MAX_IMAGE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
CHUNK_SIZE_BYTES: int = 64 * 1024  # 64 KB streaming chunks


def validate_image_signature(header: bytes, ext: str, content_type: str) -> None:
    """Validate initial file bytes against expected binary image file signatures.

    Args:
        header: Initial bytes of uploaded file.
        ext: Normalised file extension (e.g. '.jpg', '.png').
        content_type: Normalised MIME content type.

    Raises:
        HTTPException: 422 if signature does not match format or is truncated.
    """
    if len(header) < 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Image is truncated or too small to verify file format signature",
        )

    if ext in (".jpg", ".jpeg") or content_type == "image/jpeg":
        if not header.startswith(b"\xff\xd8\xff"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid file signature: content does not match JPEG format",
            )
    elif ext == ".png" or content_type == "image/png":
        if not header.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid file signature: content does not match PNG format",
            )
    elif ext == ".webp" or content_type == "image/webp":
        if len(header) < 12 or not (header.startswith(b"RIFF") and header[8:12] == b"WEBP"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid file signature: content does not match WebP format",
            )


class ListingImageStorageService:
    """Manages secure file persistence and retrieval for produce listing photos."""

    def __init__(self, upload_dir: str | None = None) -> None:
        settings = get_settings()
        configured_dir = upload_dir or settings.listing_images_dir
        self.upload_dir = Path(configured_dir).resolve()
        self.max_size_bytes = MAX_IMAGE_SIZE_BYTES
        os.makedirs(self.upload_dir, exist_ok=True)

    def save_image(self, upload_file: UploadFile) -> Tuple[str, str, int]:
        """Validate, verify signatures, and stream an uploaded image to secure storage.

        Args:
            upload_file: FastAPI UploadFile instance.

        Returns:
            Tuple of (image_uri: str, mime_type: str, file_size_bytes: int).

        Raises:
            HTTPException: 400 if empty or invalid filename.
            HTTPException: 422 if extension, MIME type, or signature is disallowed.
            HTTPException: 413 if file exceeds maximum permitted size.
        """
        raw_filename = upload_file.filename or ""
        ext = Path(raw_filename).suffix.lower()

        if not ext:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Uploaded file must have a valid image file extension (.jpg, .jpeg, .png, .webp)",
            )

        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Disallowed image extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}",
            )

        content_type = (upload_file.content_type or "").lower().strip()
        if content_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Disallowed image content type '{content_type}'. Allowed: {', '.join(sorted(ALLOWED_IMAGE_MIME_TYPES))}",
            )

        # Generate unique storage filename
        stored_filename = f"{uuid.uuid4()}{ext}"
        target_path = (self.upload_dir / stored_filename).resolve()

        # Enforce directory boundary against path traversal
        if not target_path.is_relative_to(self.upload_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid destination storage path",
            )

        total_bytes = 0
        header_checked = False

        try:
            with open(target_path, "wb") as destination:
                while chunk := upload_file.file.read(CHUNK_SIZE_BYTES):
                    if not header_checked:
                        validate_image_signature(chunk, ext, content_type)
                        header_checked = True

                    total_bytes += len(chunk)
                    if total_bytes > self.max_size_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Image exceeds maximum permitted size of {self.max_size_bytes // (1024 * 1024)} MB",
                        )
                    destination.write(chunk)

            if total_bytes == 0:
                self.delete_image_file(str(target_path))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file is empty (0 bytes)",
                )

        except Exception:
            if target_path.exists():
                try:
                    target_path.unlink()
                except OSError:
                    pass
            raise

        # Return relative storage URI
        image_uri = f"uploads/listings/{stored_filename}"
        return image_uri, content_type, total_bytes

    def resolve_path(self, image_uri: str) -> Path:
        """Resolve an image URI to an absolute filesystem Path within upload_dir.

        Args:
            image_uri: Relative URI stored in the database.

        Returns:
            Resolved absolute Path.

        Raises:
            HTTPException: 404 if file does not exist, 400 if outside upload_dir.
        """
        filename = Path(image_uri).name
        target_path = (self.upload_dir / filename).resolve()
        if not target_path.is_relative_to(self.upload_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image path",
            )
        if not target_path.exists() or not target_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image file not found on server",
            )
        return target_path

    def delete_image_file(self, image_uri: str) -> None:
        """Safely delete an image file from storage if it exists.

        Args:
            image_uri: Image storage URI or filesystem path.
        """
        try:
            filename = Path(image_uri).name
            target_path = (self.upload_dir / filename).resolve()
            if target_path.is_relative_to(self.upload_dir) and target_path.exists():
                target_path.unlink()
        except OSError:
            pass


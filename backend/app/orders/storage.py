"""Secure image storage service for order photographs and quality evidence assets.

Security controls:
- Enforces strict directory boundaries to prevent path traversal attacks.
- Validates allowed image MIME types and file extensions (JPEG, PNG, WebP).
- Validates binary magic byte signatures and Pillow image decoding.
- Enforces maximum file size (5 MB default).
- Safe file deletion and retrieval helpers.
"""

import os
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings
from app.listings.storage import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_IMAGE_MIME_TYPES,
    CHUNK_SIZE_BYTES,
    MAX_IMAGE_SIZE_BYTES,
    validate_image_content,
    validate_image_signature,
)


class OrderImageStorageService:
    """Manages secure file persistence and retrieval for order photos and attachments."""

    def __init__(self, upload_dir: str | None = None) -> None:
        settings = get_settings()
        base_dir = getattr(settings, "order_images_dir", None)
        if not base_dir:
            listing_dir = getattr(settings, "product_images_dir", None) or settings.listing_images_dir
            base_dir = Path(listing_dir).parent / "orders"
        self.upload_dir = Path(upload_dir or base_dir).resolve()
        self.max_size_bytes = getattr(settings, "max_product_image_size_bytes", MAX_IMAGE_SIZE_BYTES)
        os.makedirs(self.upload_dir, exist_ok=True)

    def save_image(self, upload_file: UploadFile) -> Tuple[str, str, int]:
        """Validate, verify signatures, and stream an uploaded order photo to secure storage.

        Args:
            upload_file: FastAPI UploadFile instance.

        Returns:
            Tuple of (image_uri: str, mime_type: str, file_size_bytes: int).
        """
        raw_filename = upload_file.filename or ""
        ext = Path(raw_filename).suffix.lower()

        if not ext:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Image file has no extension. Allowed formats: .jpg, .jpeg, .png, .webp",
            )

        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported file extension '{ext}'. Allowed: .jpg, .jpeg, .png, .webp",
            )

        content_type = (upload_file.content_type or "").lower()
        if content_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported MIME type '{content_type}'. Allowed: image/jpeg, image/png, image/webp",
            )

        # Generate non-colliding UUID filename
        stored_filename = f"{uuid.uuid4().hex}{ext}"
        destination_path = (self.upload_dir / stored_filename).resolve()

        # Path traversal guard
        try:
            destination_path.relative_to(self.upload_dir)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid destination path traversal detected",
            )

        # Read initial chunk to verify magic bytes before writing full file
        header = upload_file.file.read(16)
        validate_image_signature(header, ext, content_type)

        upload_file.file.seek(0)
        bytes_written = 0

        try:
            with open(destination_path, "wb") as dest:
                while True:
                    chunk = upload_file.file.read(CHUNK_SIZE_BYTES)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if bytes_written > self.max_size_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Image file exceeds maximum permitted size of {self.max_size_bytes // (1024 * 1024)} MB",
                        )
                    dest.write(chunk)

            # Pillow deep content validation
            validate_image_content(destination_path, ext, content_type)

        except Exception:
            if destination_path.exists():
                try:
                    destination_path.unlink()
                except OSError:
                    pass
            raise

        relative_uri = f"orders/{stored_filename}"
        return relative_uri, content_type, bytes_written

    def resolve_image_path(self, image_uri: str) -> Path:
        """Resolve a relative image URI to an absolute filesystem Path with security checks.

        Args:
            image_uri: Stored relative image URI.

        Returns:
            Resolved Path object.
        """
        # Strip optional leading 'orders/' prefix
        normalized = image_uri.replace("\\", "/")
        if normalized.startswith("orders/"):
            filename = normalized[len("orders/"):]
        else:
            filename = Path(normalized).name

        resolved = (self.upload_dir / filename).resolve()

        try:
            resolved.relative_to(self.upload_dir)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path traversal attempt detected",
            )

        if not resolved.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical image asset does not exist on disk",
            )

        return resolved

    def delete_image_file(self, image_uri: str) -> None:
        """Safely remove physical image asset from disk."""
        try:
            path = self.resolve_image_path(image_uri)
            if path.exists():
                path.unlink()
        except HTTPException:
            pass

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
from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError

from app.core.config import get_settings

ALLOWED_IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIME_TYPES: Set[str] = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
MAX_IMAGE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
CHUNK_SIZE_BYTES: int = 64 * 1024  # 64 KB streaming chunks

# Dimension and pixel limits for image security
MAX_IMAGE_WIDTH: int = 8000
MAX_IMAGE_HEIGHT: int = 8000
MAX_IMAGE_PIXELS: int = 25_000_000  # 25 MP limit protects against decompression bomb DOS attacks

# Configure Pillow decompression bomb protection
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

FORMAT_EXTENSION_MAP = {
    "JPEG": {".jpg", ".jpeg"},
    "PNG": {".png"},
    "WEBP": {".webp"},
}

FORMAT_MIME_MAP = {
    "JPEG": {"image/jpeg"},
    "PNG": {"image/png"},
    "WEBP": {"image/webp"},
}


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


def validate_image_content(file_path: Path, ext: str, content_type: str) -> Tuple[int, int, str]:
    """Inspect and decode image file using Pillow to enforce integrity and security.

    Validates:
    - Decodable image file structure.
    - Decoded format is supported (JPEG, PNG, WEBP).
    - Format matches claimed extension and MIME type.
    - Dimensions do not exceed MAX_IMAGE_WIDTH x MAX_IMAGE_HEIGHT.
    - Pixel count does not exceed MAX_IMAGE_PIXELS (decompression bomb protection).
    - File structure is not truncated or corrupted.

    Returns:
        Tuple of (width: int, height: int, detected_format: str).

    Raises:
        HTTPException(422): If image fails decoding, has mismatched formats, or exceeds limits.
    """
    try:
        with Image.open(file_path) as im:
            detected_format = (im.format or "").upper()
            if detected_format not in FORMAT_EXTENSION_MAP:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Unsupported image format '{detected_format}'. Allowed: JPEG, PNG, WebP",
                )

            # Match detected format with claimed extension
            allowed_exts = FORMAT_EXTENSION_MAP.get(detected_format, set())
            if ext not in allowed_exts:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Image content format '{detected_format}' does not match file extension '{ext}'",
                )

            # Match detected format with claimed MIME type
            allowed_mimes = FORMAT_MIME_MAP.get(detected_format, set())
            if content_type not in allowed_mimes:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Image content format '{detected_format}' does not match MIME type '{content_type}'",
                )

            width, height = im.size
            if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Image dimensions ({width}x{height}) exceed maximum permitted dimensions ({MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT})",
                )

            if width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Image resolution ({width * height} pixels) exceeds maximum permitted pixel limit ({MAX_IMAGE_PIXELS} pixels)",
                )

            # Structural verification
            im.verify()

        # Reopen to test pixel unpack / truncation for formats that support it
        with Image.open(file_path) as im_check:
            im_check.load()

        return width, height, detected_format

    except DecompressionBombError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Image exceeds decompression pixel limits (potential decompression bomb)",
        )
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid image content: file is corrupt, malformed, or not a recognized image",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Image validation failed: {str(e)}",
        )


class ListingImageStorageService:
    """Manages secure file persistence and retrieval for produce listing photos."""

    def __init__(self, upload_dir: str | None = None) -> None:
        settings = get_settings()
        configured_dir = upload_dir or getattr(settings, "product_images_dir", None) or settings.listing_images_dir
        self.upload_dir = Path(configured_dir).resolve()
        self.max_size_bytes = getattr(settings, "max_product_image_size_bytes", MAX_IMAGE_SIZE_BYTES)
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
                            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                            detail=f"Image exceeds maximum permitted size of {self.max_size_bytes // (1024 * 1024)} MB",
                        )
                    destination.write(chunk)

            if total_bytes == 0:
                self.delete_image_file(str(target_path))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file is empty (0 bytes)",
                )

            # Deep image content inspection and validation via Pillow
            validate_image_content(target_path, ext, content_type)

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
            # Check secondary/fallback directory (listings vs products)
            settings = get_settings()
            fallback_dir = Path(settings.listing_images_dir).resolve()
            fallback_path = (fallback_dir / filename).resolve()
            if fallback_path.is_relative_to(fallback_dir) and fallback_path.exists() and fallback_path.is_file():
                return fallback_path
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
                return
            settings = get_settings()
            fallback_dir = Path(settings.listing_images_dir).resolve()
            fallback_path = (fallback_dir / filename).resolve()
            if fallback_path.is_relative_to(fallback_dir) and fallback_path.exists():
                fallback_path.unlink()
        except OSError:
            pass


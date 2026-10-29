"""Secure local document storage service for verification evidence.

Security controls:
- Rejects untrusted filenames; files are stored using server-generated UUIDs.
- Enforces strict directory boundaries to prevent path traversal attacks.
- Validates allowed MIME types and file extensions.
- Validates binary file signatures (magic bytes) for PDF, JPEG, PNG, and WebP.
- Enforces a configurable maximum file size limit (default 10 MB) during chunked streaming.
- Stored outside publicly accessible document roots.
"""

import os
import uuid
from pathlib import Path
from typing import Set, Tuple

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings
from app.models.verification import MAX_DOCUMENT_SIZE_BYTES

ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES: Set[str] = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}
CHUNK_SIZE_BYTES: int = 64 * 1024  # 64 KB streaming chunks


def validate_file_signature(header: bytes, ext: str, content_type: str) -> None:
    """Validate initial file bytes against expected binary file signatures.

    Args:
        header: Initial bytes of uploaded file.
        ext: Normalised file extension (e.g. '.pdf', '.jpg').
        content_type: Normalised MIME content type.

    Raises:
        HTTPException: 422 if signature does not match the claimed format or is truncated.
    """
    if len(header) < 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File is truncated or too small to verify file format signature",
        )

    if ext == ".pdf" or content_type == "application/pdf":
        if not header.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid file signature: content does not match PDF format",
            )
    elif ext in (".jpg", ".jpeg") or content_type == "image/jpeg":
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


class DocumentStorageService:
    """Manages file persistence and retrieval for verification evidence."""

    def __init__(self, upload_dir: str | None = None) -> None:
        settings = get_settings()
        self.upload_dir = Path(upload_dir or getattr(settings, "upload_dir", "uploads/verification")).resolve()
        self.max_size_bytes = getattr(settings, "max_upload_size_bytes", MAX_DOCUMENT_SIZE_BYTES)
        # Ensure target upload directory exists
        os.makedirs(self.upload_dir, exist_ok=True)

    def save_upload(self, upload_file: UploadFile) -> Tuple[str, str, int]:
        """Validate, verify signatures, and stream an uploaded file to secure storage.

        Args:
            upload_file: FastAPI/Starlette UploadFile instance.

        Returns:
            Tuple of (file_uri: str, mime_type: str, file_size_bytes: int).

        Raises:
            HTTPException: 400 if file is empty or destination path is invalid.
            HTTPException: 422 if extension, MIME type, or file signature is disallowed.
            HTTPException: 413 if file exceeds maximum permitted size.
        """
        raw_filename = upload_file.filename or ""
        ext = Path(raw_filename).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

        content_type = (upload_file.content_type or "").lower()
        if content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported content type '{content_type}'. Allowed types: {', '.join(sorted(ALLOWED_MIME_TYPES))}",
            )

        # Read the first chunk to inspect signature and check for empty file
        first_chunk = upload_file.file.read(CHUNK_SIZE_BYTES)
        if not first_chunk or len(first_chunk) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file cannot be empty",
            )

        # Validate file signature against claimed extension and MIME type
        validate_file_signature(first_chunk, ext, content_type)

        # Generate non-guessable, server-controlled storage filename
        stored_filename = f"{uuid.uuid4()}{ext}"
        destination_path = (self.upload_dir / stored_filename).resolve()

        # Path traversal prevention check
        if not str(destination_path).startswith(str(self.upload_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid destination path detected",
            )

        total_bytes = len(first_chunk)
        if total_bytes > self.max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds maximum permitted size of {self.max_size_bytes // (1024 * 1024)} MB",
            )

        try:
            with open(destination_path, "wb") as out_file:
                out_file.write(first_chunk)
                while True:
                    chunk = upload_file.file.read(CHUNK_SIZE_BYTES)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > self.max_size_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                            detail=f"File exceeds maximum permitted size of {self.max_size_bytes // (1024 * 1024)} MB",
                        )
                    out_file.write(chunk)
        except Exception:
            # Clean up partial file on failure
            if destination_path.exists():
                destination_path.unlink()
            raise

        # Store relative file URI for portability
        file_uri = f"verification/{stored_filename}"
        return file_uri, content_type, total_bytes

    def get_file_path(self, file_uri: str) -> Path:
        """Resolve a stored document URI to a verified absolute filesystem path.

        Args:
            file_uri: Stored relative file URI.

        Returns:
            Resolved absolute Path.

        Raises:
            HTTPException: 400 if URI contains path traversal sequences.
            HTTPException: 404 if file does not exist on disk.
        """
        # Normalize relative path (strip leading 'verification/' if present)
        rel_path = file_uri.removeprefix("verification/").removeprefix("verification\\")
        resolved_path = (self.upload_dir / rel_path).resolve()

        if not str(resolved_path).startswith(str(self.upload_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path detected",
            )

        if not resolved_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found on storage",
            )

        return resolved_path

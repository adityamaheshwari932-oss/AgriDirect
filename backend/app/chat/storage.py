"""Secure local storage service for chat attachments (images and documents).

Security controls (implements M5-05, M5-06, M5-11):
- Rejects untrusted filenames; files are stored using server-generated UUIDs.
- Enforces strict directory boundaries to prevent path traversal attacks.
- Validates allowed extensions and MIME types via strict explicit allowlists.
- Validates binary file signatures (magic bytes) for images (JPEG, PNG, WebP) and documents (PDF, DOCX, XLSX, OLE).
- Explicitly rejects executable formats (e.g. PE 'MZ', ELF, Shell scripts).
- Enforces a configurable maximum file size limit (default 10 MB) during chunked streaming.
- Rejects 0-byte (empty) files.
- Stored outside publicly accessible document roots in `uploads/chat`.
- Provides atomic cleanup helpers for failed database transactions.
"""

import os
import uuid
from pathlib import Path
from typing import Set, Tuple

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

# Maximum chat attachment size (10 MB)
MAX_CHAT_ATTACHMENT_SIZE_BYTES: int = 10 * 1024 * 1024
CHUNK_SIZE_BYTES: int = 64 * 1024  # 64 KB streaming chunks

# Explicit Allowlists
IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp"}
IMAGE_MIME_TYPES: Set[str] = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

DOCUMENT_EXTENSIONS: Set[str] = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".csv",
    ".txt",
}
DOCUMENT_MIME_TYPES: Set[str] = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "text/plain",
}

ALLOWED_EXTENSIONS: Set[str] = IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS
ALLOWED_MIME_TYPES: Set[str] = IMAGE_MIME_TYPES | DOCUMENT_MIME_TYPES

# Dangerous / executable signatures to strictly reject
EXECUTABLE_SIGNATURES = (
    b"MZ",  # DOS / Windows PE executable
    b"\x7fELF",  # Linux ELF executable
    b"\xca\xfe\xba\xbe",  # Mach-O / Java Class
    b"#!",  # Shell script shebang
)


def validate_chat_file_signature(header: bytes, ext: str, content_type: str) -> None:
    """Validate initial file bytes against expected binary signatures and reject executables.

    Args:
        header: Initial bytes of uploaded file.
        ext: Normalised file extension (e.g. '.pdf', '.jpg').
        content_type: Normalised MIME content type.

    Raises:
        HTTPException: 422 if signature does not match the claimed format, is truncated,
                       or matches executable signatures.
    """
    if len(header) < 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File is truncated or too small to verify file format signature",
        )

    # Check for executable magic bytes
    for sig in EXECUTABLE_SIGNATURES:
        if header.startswith(sig):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Security violation: executable file content detected and rejected",
            )

    if ext in (".jpg", ".jpeg") or content_type == "image/jpeg":
        if not header.startswith(b"\xff\xd8\xff"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid file signature: content does not match JPEG image format",
            )
    elif ext == ".png" or content_type == "image/png":
        if not header.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid file signature: content does not match PNG image format",
            )
    elif ext == ".webp" or content_type == "image/webp":
        if len(header) < 12 or not (header.startswith(b"RIFF") and header[8:12] == b"WEBP"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid file signature: content does not match WebP image format",
            )
    elif ext == ".pdf" or content_type == "application/pdf":
        if not header.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid file signature: content does not match PDF document format",
            )
    elif ext in (".docx", ".xlsx"):
        # OpenXML documents are ZIP archives
        if not header.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid file signature: content does not match Office OpenXML document format",
            )
    elif ext in (".doc", ".xls"):
        # Legacy binary office files or OLE compound documents
        if not (header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1") or header.startswith(b"PK\x03\x04")):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid file signature: content does not match binary Office document format",
            )
    elif ext in (".csv", ".txt"):
        # Plain text / CSV: inspect that initial bytes can be decoded as text without null bytes
        try:
            sample = header[:512].decode("utf-8")
            if "\x00" in sample:
                raise ValueError("Null bytes found")
        except UnicodeDecodeError:
            try:
                sample = header[:512].decode("latin-1")
                if "\x00" in sample:
                    raise ValueError("Null bytes found")
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Invalid text format: binary data detected in text file",
                )


class ChatStorageService:
    """Manages file persistence, validation, and retrieval for chat attachments."""

    def __init__(self, upload_dir: str | None = None) -> None:
        settings = get_settings()
        base_dir = getattr(settings, "upload_dir", "uploads")
        self.upload_dir = Path(upload_dir or Path(base_dir) / "chat").resolve()
        self.max_size_bytes = getattr(settings, "max_chat_upload_size_bytes", MAX_CHAT_ATTACHMENT_SIZE_BYTES)
        # Ensure target directory exists
        os.makedirs(self.upload_dir, exist_ok=True)

    def save_upload(self, upload_file: UploadFile) -> Tuple[str, str, int, str]:
        """Validate, verify signatures, stream to secure storage, and classify attachment.

        Args:
            upload_file: FastAPI UploadFile instance.

        Returns:
            Tuple of (file_uri: str, file_mime_type: str, file_size_bytes: int, attachment_type: str).

        Raises:
            HTTPException: 400 if empty or path invalid.
            HTTPException: 422 if extension, MIME type, or signature disallowed.
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

        # Inspect initial chunk
        first_chunk = upload_file.file.read(CHUNK_SIZE_BYTES)
        if not first_chunk or len(first_chunk) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file cannot be empty",
            )

        # Validate signature
        validate_chat_file_signature(first_chunk, ext, content_type)

        # Determine attachment type category
        attachment_type = "image" if ext in IMAGE_EXTENSIONS else "document"

        # Generate non-guessable, server-controlled filename
        stored_filename = f"{uuid.uuid4()}{ext}"
        destination_path = (self.upload_dir / stored_filename).resolve()

        # Path traversal guard using strict resolved path containment
        try:
            if not destination_path.is_relative_to(self.upload_dir):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid destination path detected",
                )
        except ValueError:
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

        file_uri = f"chat/{stored_filename}"
        return file_uri, content_type, total_bytes, attachment_type

    def get_file_path(self, file_uri: str) -> Path:
        """Resolve a stored attachment URI to a verified absolute filesystem path.

        Args:
            file_uri: Stored relative file URI (e.g. 'chat/uuid.png').

        Returns:
            Resolved absolute Path.

        Raises:
            HTTPException: 400 if URI contains path traversal sequences.
            HTTPException: 404 if file does not exist on disk.
        """
        rel_path = file_uri.removeprefix("chat/").removeprefix("chat\\")
        resolved_path = (self.upload_dir / rel_path).resolve()

        # Path traversal guard using strict resolved path containment
        try:
            if not resolved_path.is_relative_to(self.upload_dir):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file path detected",
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path detected",
            )

        if not resolved_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attachment file not found on storage",
            )

        return resolved_path

    def delete_file(self, file_uri: str) -> None:
        """Safely delete an attachment file from storage if present."""
        try:
            path = self.get_file_path(file_uri)
            if path.is_file():
                path.unlink()
        except HTTPException:
            pass


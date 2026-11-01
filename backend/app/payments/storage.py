"""Secure file storage service for payment proof and dispute evidence attachments.

Implements Module 6 security and non-custodial record-keeping requirements:
- Validates binary file signatures (magic bytes) for JPEG, PNG, and PDF.
- Explicitly rejects executable signatures (PE 'MZ', ELF, Java/Mach-O, Shebang).
- Enforces strict resolved path containment (Path.is_relative_to) to prevent path traversal
  and sibling directory string-prefix matching exploits.
- Replaces client-supplied filenames with server-controlled UUIDs.
- Enforces a 10 MB maximum upload size limit.
- Rejects 0-byte (empty) files.
- Provides atomic cleanup helpers for transaction rollbacks.
"""

import os
import uuid
from pathlib import Path
from typing import Set, Tuple

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

# Maximum payment proof / evidence attachment size (10 MB)
MAX_PAYMENT_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024
CHUNK_SIZE_BYTES: int = 64 * 1024  # 64 KB streaming chunks

# Explicit Allowlists
ALLOWED_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".pdf"}
ALLOWED_MIME_TYPES: Set[str] = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}

# Dangerous / executable signatures to strictly reject
EXECUTABLE_SIGNATURES = (
    b"MZ",  # DOS / Windows PE executable
    b"\x7fELF",  # Linux ELF executable
    b"\xca\xfe\xba\xbe",  # Mach-O / Java Class
    b"#!",  # Shell script shebang
)


def validate_payment_file_signature(header: bytes, ext: str, content_type: str) -> None:
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is truncated or too small to verify file format signature",
        )

    # Check for executable magic bytes
    for sig in EXECUTABLE_SIGNATURES:
        if header.startswith(sig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: executable file content detected and rejected",
            )

    if ext in (".jpg", ".jpeg") or content_type == "image/jpeg":
        if not header.startswith(b"\xff\xd8\xff"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file signature: content does not match JPEG image format",
            )
    elif ext == ".png" or content_type == "image/png":
        if not header.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file signature: content does not match PNG image format",
            )
    elif ext == ".pdf" or content_type == "application/pdf":
        if not header.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file signature: content does not match PDF document format",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )


class PaymentStorageService:
    """Manages secure file persistence, validation, and retrieval for payment evidence."""

    def __init__(self, upload_dir: str | None = None, base_dir: str | None = None) -> None:
        settings = get_settings()
        default_base = getattr(settings, "upload_dir", "uploads")
        resolved_root = upload_dir or base_dir or Path(default_base) / "payments"
        self.upload_dir = Path(resolved_root).resolve()
        self.proofs_dir = (self.upload_dir / "proofs").resolve()
        self.evidence_dir = (self.upload_dir / "evidence").resolve()
        self.max_size_bytes = getattr(settings, "max_payment_upload_size_bytes", MAX_PAYMENT_UPLOAD_SIZE_BYTES)

        # Ensure target directories exist
        os.makedirs(self.proofs_dir, exist_ok=True)
        os.makedirs(self.evidence_dir, exist_ok=True)

    def _save_file(self, upload_file: UploadFile, subfolder: str) -> Tuple[str, str, int]:
        """Validate signature, stream file to isolated directory, and return metadata."""
        raw_filename = upload_file.filename or ""
        ext = Path(raw_filename).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

        content_type = (upload_file.content_type or "").lower()
        if content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
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
        validate_payment_file_signature(first_chunk, ext, content_type)

        target_dir = self.proofs_dir if subfolder == "proofs" else self.evidence_dir
        stored_filename = f"{uuid.uuid4()}{ext}"
        destination_path = (target_dir / stored_filename).resolve()

        # Path traversal guard using strict resolved path containment
        try:
            if not destination_path.is_relative_to(target_dir):
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
            if destination_path.exists():
                destination_path.unlink()
            raise

        file_uri = f"payments/{subfolder}/{stored_filename}"
        return file_uri, content_type, total_bytes

    def save_proof(self, upload_file: UploadFile) -> Tuple[str, str, int]:
        """Save payment proof receipt file."""
        return self._save_file(upload_file, "proofs")

    def save_evidence(self, upload_file: UploadFile) -> Tuple[str, str, int]:
        """Save payment dispute evidence file."""
        return self._save_file(upload_file, "evidence")

    def get_file_path(self, file_uri: str) -> Path:
        """Resolve a stored relative file URI to a verified absolute filesystem path.

        Args:
            file_uri: Stored relative file URI (e.g. 'payments/proofs/uuid.png').

        Returns:
            Resolved absolute Path.

        Raises:
            HTTPException: 400 if URI contains path traversal sequences.
            HTTPException: 404 if file does not exist on disk.
        """
        rel_path = file_uri.removeprefix("payments/").removeprefix("payments\\")
        resolved_path = (self.upload_dir / rel_path).resolve()

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
                detail="Payment attachment file not found on storage",
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


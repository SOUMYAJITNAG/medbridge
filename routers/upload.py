"""
Upload router — handles patient creation and evidence file uploads.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from database.init_db import db_conn
from models.schemas import PatientCreate, PatientResponse

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 20 * 1024 * 1024))

ALLOWED_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp", "image/bmp",
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", "audio/mp4", "audio/webm",
    "application/pdf",
    "text/plain",
}

CATEGORY_MAP = {
    "prescription": "prescription",
    "medicine_strip": "medicine_strip",
    "medicine": "medicine_strip",
    "lab_report": "lab_report",
    "lab": "lab_report",
    "vaccination": "vaccination",
    "vaccine": "vaccination",
    "voice_note": "voice_note",
    "voice": "voice_note",
    "audio": "voice_note",
    "other": "other",
    "discharge": "other",
    "report": "lab_report",
}


def _detect_category(filename: str, content_type: str, hint: str = "other") -> str:
    """Detect evidence category from filename, content type, or hint."""
    if hint and hint.lower() in CATEGORY_MAP:
        return CATEGORY_MAP[hint.lower()]

    name_lower = filename.lower()
    if any(k in name_lower for k in ["rx", "prescription", "prescript", "recepta"]):
        return "prescription"
    if any(k in name_lower for k in ["strip", "tablet", "pill", "medicine", "med_"]):
        return "medicine_strip"
    if any(k in name_lower for k in ["lab", "blood", "urine", "test", "report"]):
        return "lab_report"
    if any(k in name_lower for k in ["vac", "vaccine", "immun"]):
        return "vaccination"
    if content_type.startswith("audio/"):
        return "voice_note"
    return "other"


@router.post("/patient", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(patient: PatientCreate):
    """Create a new patient record."""
    patient_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Normalise the custom-language label (only kept when language == "custom").
    language_other = (patient.language_other or "").strip() or None
    if patient.language != "custom":
        language_other = None

    with db_conn() as conn:
        conn.execute(
            "INSERT INTO patients (id, name, language, language_other, age, "
            "additional_notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (patient_id, patient.name, patient.language, language_other,
             patient.age, patient.additional_notes, now),
        )

    return PatientResponse(
        id=patient_id,
        name=patient.name,
        language=patient.language,
        language_other=language_other,
        age=patient.age,
        additional_notes=patient.additional_notes,
        created_at=now,
    )


@router.post("/files/{patient_id}")
async def upload_evidence_files(
    patient_id: str,
    files: List[UploadFile] = File(...),
    categories: Optional[str] = Form(default=""),
):
    """Upload one or more evidence files for a patient.
    
    Categories can be a comma-separated list of hints per file
    (prescription, medicine_strip, lab_report, vaccination, voice_note, other).
    """
    # Verify patient exists
    with db_conn() as conn:
        patient = conn.execute(
            "SELECT id FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    category_hints = [c.strip() for c in (categories or "").split(",")]
    patient_upload_dir = Path(UPLOAD_DIR) / patient_id
    patient_upload_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    errors = []

    for idx, file in enumerate(files):
        # Validate file type
        content_type = file.content_type or "application/octet-stream"
        if content_type not in ALLOWED_TYPES:
            errors.append({"file": file.filename, "error": f"Unsupported file type: {content_type}"})
            continue

        # Read and validate size
        data = await file.read()
        if len(data) > MAX_FILE_SIZE:
            errors.append({"file": file.filename, "error": "File too large (max 20MB)"})
            continue

        # Save file
        file_id = str(uuid.uuid4())
        ext = Path(file.filename or "file").suffix or ".bin"
        safe_name = f"{file_id}{ext}"
        file_path = patient_upload_dir / safe_name

        with open(file_path, "wb") as f:
            f.write(data)

        # Detect category
        hint = category_hints[idx] if idx < len(category_hints) else "other"
        category = _detect_category(file.filename or "", content_type, hint)

        # Determine file type group
        if content_type.startswith("image/"):
            file_type = "image"
        elif content_type.startswith("audio/"):
            file_type = "audio"
        elif content_type == "application/pdf":
            file_type = "pdf"
        else:
            file_type = "text"

        now = datetime.now(timezone.utc).isoformat()
        with db_conn() as conn:
            conn.execute(
                "INSERT INTO evidence_files "
                "(id, patient_id, original_name, file_path, file_type, evidence_category, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (file_id, patient_id, file.filename or safe_name,
                 str(file_path), file_type, category, now),
            )

        saved_files.append({
            "id": file_id,
            "original_name": file.filename,
            "file_type": file_type,
            "evidence_category": category,
            "size_bytes": len(data),
        })

    return {
        "patient_id": patient_id,
        "saved": saved_files,
        "errors": errors,
        "total_saved": len(saved_files),
    }


@router.get("/patient/{patient_id}/files")
async def list_patient_files(patient_id: str):
    """List all evidence files for a patient."""
    with db_conn() as conn:
        patient = conn.execute(
            "SELECT id, name, language FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        files = conn.execute(
            "SELECT id, original_name, file_type, evidence_category, created_at "
            "FROM evidence_files WHERE patient_id = ? ORDER BY created_at",
            (patient_id,),
        ).fetchall()

    return {
        "patient_id": patient_id,
        "patient_name": patient["name"],
        "files": [dict(f) for f in files],
        "total": len(files),
    }


@router.get("/patients")
async def list_patients():
    """List all patients."""
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT p.id, p.name, p.language, p.age, p.created_at, "
            "COUNT(ef.id) as file_count "
            "FROM patients p LEFT JOIN evidence_files ef ON p.id = ef.patient_id "
            "GROUP BY p.id ORDER BY p.created_at DESC LIMIT 50"
        ).fetchall()
    return {"patients": [dict(r) for r in rows]}


# ── Combined upload endpoint called by frontend ──────────────────────

@router.post("")
@router.post("/")
async def combined_upload(
    full_name: str = Form(""),
    dob: str = Form(""),
    gender: str = Form(""),
    blood_type: str = Form(""),
    primary_language: str = Form("Ukrainian"),
    secondary_language: str = Form("English"),
    origin_city: str = Form(""),
    current_location: str = Form(""),
    contact_info: str = Form(""),
    special_notes: str = Form(""),
    files: List[UploadFile] = File(default=[]),
    categories: List[str] = Form(default=[]),
):
    """
    Combined endpoint: create patient record + save evidence files + allocate run_id.
    Returns { run_id, patient_id, saved_count }.
    """
    import uuid as _uuid
    from datetime import datetime, timezone as _tz

    name = full_name.strip() or "Unknown Patient"
    language_map = {
        "Ukrainian": "uk", "English": "en", "German": "de",
        "Polish": "pl", "Czech": "cs", "French": "fr", "Romanian": "ro",
    }
    language_code = language_map.get(primary_language, primary_language[:2].lower() if primary_language else "uk")

    # Build additional notes
    notes_parts = []
    if dob: notes_parts.append(f"DOB: {dob}")
    if gender: notes_parts.append(f"Gender: {gender}")
    if blood_type: notes_parts.append(f"Blood type: {blood_type}")
    if secondary_language: notes_parts.append(f"Secondary language: {secondary_language}")
    if origin_city: notes_parts.append(f"Origin: {origin_city}")
    if current_location: notes_parts.append(f"Current location: {current_location}")
    if contact_info: notes_parts.append(f"Contact: {contact_info}")
    if special_notes: notes_parts.append(special_notes)
    additional_notes = " | ".join(notes_parts)

    patient_id = str(_uuid.uuid4())
    run_id = str(_uuid.uuid4())
    now = _tz.utc
    now_str = datetime.now(now).isoformat()

    with db_conn() as conn:
        conn.execute(
            "INSERT INTO patients (id, name, language, age, additional_notes, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (patient_id, name, language_code, None, additional_notes, now_str),
        )
        # Pre-allocate pipeline run as 'pending'
        conn.execute(
            "INSERT INTO pipeline_runs (id, patient_id, status, created_at) VALUES (?, ?, 'pending', ?)",
            (run_id, patient_id, now_str),
        )

    # Save files
    patient_upload_dir = Path(UPLOAD_DIR) / patient_id
    patient_upload_dir.mkdir(parents=True, exist_ok=True)
    saved_count = 0
    errors = []

    for idx, file in enumerate(files):
        content_type = file.content_type or "application/octet-stream"
        if content_type not in ALLOWED_TYPES and not content_type.startswith("image/") and not content_type.startswith("audio/"):
            errors.append({"file": file.filename, "error": f"Unsupported type: {content_type}"})
            continue

        data = await file.read()
        if len(data) > MAX_FILE_SIZE:
            errors.append({"file": file.filename, "error": "File too large"})
            continue

        file_id = str(_uuid.uuid4())
        ext = Path(file.filename or "file").suffix or ".bin"
        safe_name = f"{file_id}{ext}"
        file_path = patient_upload_dir / safe_name

        with open(file_path, "wb") as fp:
            fp.write(data)

        hint = categories[idx] if idx < len(categories) else "other"
        category = _detect_category(file.filename or "", content_type, hint)

        if content_type.startswith("image/"):
            file_type = "image"
        elif content_type.startswith("audio/"):
            file_type = "audio"
        elif content_type == "application/pdf":
            file_type = "pdf"
        else:
            file_type = "text"

        with db_conn() as conn:
            conn.execute(
                "INSERT INTO evidence_files "
                "(id, patient_id, original_name, file_path, file_type, evidence_category, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (file_id, patient_id, file.filename or safe_name,
                 str(file_path), file_type, category, now_str),
            )
        saved_count += 1

    return JSONResponse({
        "run_id": run_id,
        "patient_id": patient_id,
        "patient_name": name,
        "saved_count": saved_count,
        "errors": errors,
        "status": "ready",
        "pipeline_url": f"/pipeline/{run_id}",
    }, status_code=201)

"""
Passport router — retrieve Emergency Medical Passport data and handle verifications.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from models.schemas import VerificationUpdate
from database.init_db import db_conn

router = APIRouter()


def _parse_json_field(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


@router.get("/{run_id}")
async def get_passport(run_id: str):
    """Retrieve full Emergency Medical Passport for a pipeline run."""
    with db_conn() as conn:
        run = conn.execute(
            "SELECT pr.*, p.name as patient_name, p.language, p.age "
            "FROM pipeline_runs pr "
            "JOIN patients p ON pr.patient_id = p.id "
            "WHERE pr.id = ?",
            (run_id,),
        ).fetchone()

    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    if run["status"] not in ("completed",):
        return {
            "run_id": run_id,
            "status": run["status"],
            "patient_name": run["patient_name"],
            "message": f"Pipeline is {run['status']}. Passport not yet available.",
        }

    passport_data = _parse_json_field(run["passport_data"]) or {}
    structured_data = _parse_json_field(run["structured_data"]) or {}
    risk_report = _parse_json_field(run["risk_report"]) or {}
    timeline_data = _parse_json_field(run["timeline_data"]) or {}
    verification_checklist = _parse_json_field(run["verification_checklist"]) or {}

    # Merge passport_data and structured_data fields to top level for frontend
    merged = {
        "run_id": run_id,
        "patient_id": run["patient_id"],
        "patient_name": run["patient_name"],
        "patient_language": run["language"],
        "patient_age": run["age"],
        "status": run["status"],
        "created_at": run["created_at"],
        "completed_at": run["completed_at"],
        # Nested originals
        "passport_data": passport_data,
        "structured_data": structured_data,
        "timeline_data": timeline_data,
        "risk_report": risk_report,
        "verification_checklist": verification_checklist,
    }

    # Flatten for easy frontend access
    merged["confidence_score"] = (
        passport_data.get("confidence_score")
        or risk_report.get("overall_confidence")
        or structured_data.get("confidence_score")
        or 0
    )
    merged["allergies"] = (
        passport_data.get("critical_allergies")
        or passport_data.get("allergies")
        or structured_data.get("allergies")
        or []
    )
    merged["medications"] = (
        passport_data.get("current_medications")
        or passport_data.get("medications")
        or structured_data.get("medications")
        or []
    )
    merged["conditions"] = (
        passport_data.get("chronic_conditions")
        or passport_data.get("conditions")
        or structured_data.get("conditions")
        or []
    )
    merged["vaccinations"] = (
        passport_data.get("vaccinations")
        or structured_data.get("vaccinations")
        or []
    )
    merged["risk_flags"] = (
        risk_report.get("risk_flags")
        or risk_report.get("flags")
        or passport_data.get("risk_flags")
        or []
    )
    merged["timeline"] = (
        timeline_data.get("events")
        or timeline_data.get("timeline")
        or passport_data.get("timeline")
        or []
    )
    merged["multilingual_summary"] = (
        passport_data.get("multilingual_summary")
        or passport_data.get("translations")
        or {}
    )
    merged["emergency_notes"] = (
        passport_data.get("emergency_notes")
        or passport_data.get("emergency_instructions")
        or ""
    )
    merged["blood_type"] = (
        passport_data.get("blood_type")
        or structured_data.get("blood_type")
        or ""
    )
    merged["summary"] = (
        passport_data.get("summary")
        or passport_data.get("clinical_summary")
        or ""
    )

    return merged


@router.get("/patient/{patient_id}/latest")
async def get_latest_passport(patient_id: str):
    """Get the most recent completed passport for a patient."""
    with db_conn() as conn:
        run = conn.execute(
            "SELECT id FROM pipeline_runs WHERE patient_id = ? AND status = 'completed' "
            "ORDER BY completed_at DESC LIMIT 1",
            (patient_id,),
        ).fetchone()

    if not run:
        raise HTTPException(status_code=404, detail="No completed passport found for this patient")

    return await get_passport(run["id"])


@router.post("/{run_id}/verify")
async def submit_verification(run_id: str, verification: VerificationUpdate):
    """Submit doctor verification for a passport."""
    with db_conn() as conn:
        run = conn.execute(
            "SELECT id, status FROM pipeline_runs WHERE id = ?", (run_id,)
        ).fetchone()

    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    verification_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with db_conn() as conn:
        # Upsert: delete old verification for this run, insert new
        conn.execute("DELETE FROM verifications WHERE run_id = ?", (run_id,))
        conn.execute(
            "INSERT INTO verifications (id, run_id, doctor_name, verification_data, "
            "overall_status, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                verification_id, run_id,
                verification.doctor_name,
                json.dumps(verification.verification_data) if verification.verification_data else None,
                verification.overall_status,
                verification.notes,
                now,
            ),
        )

    return {
        "verification_id": verification_id,
        "run_id": run_id,
        "overall_status": verification.overall_status,
        "created_at": now,
        "message": "Verification submitted successfully",
    }


@router.get("/{run_id}/verification")
async def get_verification(run_id: str):
    """Get verification status for a passport."""
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM verifications WHERE run_id = ? ORDER BY created_at DESC LIMIT 1",
            (run_id,),
        ).fetchone()

    if not row:
        return {"run_id": run_id, "overall_status": "pending", "message": "Not yet verified"}

    data = dict(row)
    data["verification_data"] = _parse_json_field(data.get("verification_data"))
    return data


@router.get("/{run_id}/checklist")
async def get_checklist(run_id: str):
    """Return the doctor verification checklist for a passport."""
    with db_conn() as conn:
        run = conn.execute(
            "SELECT verification_checklist, status FROM pipeline_runs WHERE id = ?",
            (run_id,),
        ).fetchone()

    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    checklist = _parse_json_field(run["verification_checklist"]) or {}
    # normalise: checklist may be { sections: [...] } or a plain list
    if isinstance(checklist, list):
        sections = checklist
    elif isinstance(checklist, dict):
        sections = checklist.get("sections") or checklist.get("items") or []
    else:
        sections = []

    return {"run_id": run_id, "sections": sections, "status": run["status"]}

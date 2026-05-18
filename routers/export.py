"""
Export router — PDF and QR code generation for Emergency Medical Passport.
"""

from __future__ import annotations

import io
import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

from database.init_db import db_conn
from services.export_service import generate_passport_pdf, generate_qr_code

router = APIRouter()


def _parse_json_field(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


@router.get("/{run_id}/pdf")
async def download_pdf(run_id: str):
    """Generate and download a PDF Emergency Medical Passport."""
    with db_conn() as conn:
        run = conn.execute(
            "SELECT pr.*, p.name as patient_name, p.language "
            "FROM pipeline_runs pr JOIN patients p ON pr.patient_id = p.id "
            "WHERE pr.id = ? AND pr.status = 'completed'",
            (run_id,),
        ).fetchone()

    if not run:
        raise HTTPException(status_code=404, detail="Completed passport not found")

    passport_data = _parse_json_field(run["passport_data"]) or {}
    risk_report = _parse_json_field(run["risk_report"]) or {}

    pdf_bytes = generate_passport_pdf(
        passport_data=passport_data,
        patient_name=run["patient_name"],
        run_id=run_id,
        risk_report=risk_report,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="MedBridge_Passport_{run_id[:8]}.pdf"'
        },
    )


@router.get("/{run_id}/qr")
async def get_qr_code(run_id: str):
    """Generate QR code image with critical medical data."""
    with db_conn() as conn:
        run = conn.execute(
            "SELECT passport_data, patient_id FROM pipeline_runs WHERE id = ? AND status = 'completed'",
            (run_id,),
        ).fetchone()

    if not run:
        raise HTTPException(status_code=404, detail="Completed passport not found")

    passport_data = _parse_json_field(run["passport_data"]) or {}
    qr_data = passport_data.get("qr_data", "")
    if not qr_data:
        # Fallback: compact critical info
        allergies = passport_data.get("critical_allergies", [])
        medications = passport_data.get("current_medications", [])
        qr_data = json.dumps({
            "p": passport_data.get("patient", {}).get("name", "Unknown"),
            "a": [a.get("substance", "") for a in allergies[:3]],
            "m": [m.get("name", "") for m in medications[:5]],
            "id": run_id[:8],
        })

    qr_bytes = generate_qr_code(qr_data)

    return Response(
        content=qr_bytes,
        media_type="image/png",
        headers={"Cache-Control": "max-age=3600"},
    )

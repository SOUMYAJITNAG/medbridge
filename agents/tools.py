"""
Agent tools for MedBridge Ukraine pipeline.

All tools are plain Python functions with rich docstrings.
ADK introspects signatures and exposes them to LLM agents as callable tools.

Tool categories:
  1. Gemma 4 content generation (text + multimodal)
  2. Patient & evidence data access
  3. Pipeline state persistence
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from database.init_db import db_conn
from services.ai_service import call_gemma as _call_gemma, call_gemma_json as _call_gemma_json

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")


# ── Gemma 4 content tools ─────────────────────────────────────────────

def gemma_generate(prompt: str, purpose: str = "medical_summary") -> dict[str, Any]:
    """Call Gemma 4 to generate clinical text (summaries, translations, analyses).

    Use whenever you need to produce patient-facing or clinician-facing text.
    Gemma 4 is the trusted clinical brain with multilingual understanding.

    Args:
        prompt: A precise, self-contained instruction for Gemma 4.
                Include all patient context needed.
        purpose: Short tag describing intent (e.g. 'timeline', 'translation').

    Returns:
        Dict with 'text' containing the generated content.
    """
    try:
        text = _call_gemma(prompt, max_tokens=2000)
    except Exception as exc:
        return {"status": "error", "error": str(exc), "purpose": purpose}
    return {"status": "ok", "purpose": purpose, "text": text}


def gemma_generate_json(prompt: str, purpose: str = "structured_data") -> dict[str, Any]:
    """Call Gemma 4 and parse its response as JSON.

    Use when you need structured output (medication lists, timelines, etc.).

    Args:
        prompt: Instruction asking Gemma to reply with a JSON object.
                Spell out the exact keys you expect.
        purpose: Short tag for logging.

    Returns:
        Dict with 'data' containing the parsed JSON object.
    """
    try:
        data = _call_gemma_json(prompt, max_tokens=3000)
    except Exception as exc:
        return {"status": "error", "error": str(exc), "purpose": purpose}
    return {"status": "ok", "purpose": purpose, "data": data}


def gemma_multimodal_analyze(patient_id: str, category_filter: str = "all") -> dict[str, Any]:
    """Process all uploaded evidence files for a patient using Gemma 4 multimodal.

    Gemma 4 natively handles: images (prescriptions, medicine strips, lab reports,
    vaccination cards), audio (voice notes in any language), PDFs, and handwritten
    documents. No OCR or speech-to-text library required.

    Args:
        patient_id: The patient UUID to process evidence for.
        category_filter: Filter by category ('prescription', 'medicine_strip',
                         'lab_report', 'vaccination', 'voice_note', 'other', 'all').

    Returns:
        Dict with 'extractions' list — one entry per file with extracted medical data.
    """
    with db_conn() as conn:
        if category_filter == "all":
            rows = conn.execute(
                "SELECT id, original_name, file_path, file_type, evidence_category "
                "FROM evidence_files WHERE patient_id = ?",
                (patient_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, original_name, file_path, file_type, evidence_category "
                "FROM evidence_files WHERE patient_id = ? AND evidence_category = ?",
                (patient_id, category_filter),
            ).fetchall()

    if not rows:
        return {"status": "no_files", "extractions": []}

    extractions = []
    for row in rows:
        file_path = row["file_path"]
        category = row["evidence_category"]
        original_name = row["original_name"]

        # Build category-specific prompt for Gemma 4
        prompt = _build_extraction_prompt(category, original_name)

        try:
            if Path(file_path).exists():
                data = _call_gemma_json(prompt, file_paths=[file_path], max_tokens=2000)
            else:
                data = {"error": "file_not_found", "file": file_path}
        except Exception as exc:
            data = {"error": str(exc)}

        extraction = {
            "file_id": row["id"],
            "original_name": original_name,
            "category": category,
            "extracted_data": data,
        }
        extractions.append(extraction)

        # Cache extraction in DB
        try:
            with db_conn() as conn:
                conn.execute(
                    "UPDATE evidence_files SET gemma_extraction = ? WHERE id = ?",
                    (json.dumps(data), row["id"]),
                )
        except Exception:
            pass

    return {"status": "ok", "patient_id": patient_id, "extractions": extractions}


def _build_extraction_prompt(category: str, filename: str) -> str:
    """Build a Gemma 4 multimodal prompt based on evidence category."""
    base = (
        "You are a medical AI assistant helping reconstruct medical history for a "
        "displaced refugee or migrant patient. The source documents may be in ANY "
        "language or script (Ukrainian, Russian, Arabic, Pashto, Dari, Farsi, Urdu, "
        "Tigrinya, Amharic, Somali, Swahili, Burmese, Rohingya, Karen, Kurdish, "
        "Hindi, Bengali, Spanish, Haitian Creole, English, or a tribal/indigenous "
        "language). Read whatever script is present and extract the medical content. "
        "Always include `language_detected` so downstream agents know what they got.\n\n"
    )

    category_prompts = {
        "prescription": (
            "This is a medical prescription (possibly handwritten, damaged, or in any "
            "language/script). Extract ALL information you can find:\n"
            "Return JSON with keys: {medicines: [{name, dosage, frequency, duration, "
            "prescribing_doctor, date_prescribed}], patient_name, diagnosis_hints, "
            "language_detected, confidence_score (0-1), notes}"
        ),
        "medicine_strip": (
            "This is a medicine strip or packaging photo. Identify the medicine:\n"
            "Return JSON with keys: {medicine_name, generic_name, strength, "
            "manufacturer, active_ingredients, possible_conditions, confidence_score (0-1), notes}"
        ),
        "lab_report": (
            "This is a laboratory or diagnostic report (possibly in any language). Extract:\n"
            "Return JSON with keys: {test_date, tests: [{test_name, result, unit, "
            "reference_range, abnormal}], lab_name, doctor_name, diagnosis_hints, "
            "language_detected, confidence_score (0-1)}"
        ),
        "vaccination": (
            "This is a vaccination card or immunization record. Extract:\n"
            "Return JSON with keys: {patient_name, vaccines: [{name, date, "
            "dose_number, batch_number, facility}], language_detected, confidence_score (0-1)}"
        ),
        "voice_note": (
            "This is an audio recording of a patient describing their medical history. "
            "Transcribe and analyze the content. The speaker may use any language, "
            "dialect, or tribal/indigenous tongue \u2014 transcribe in the original script "
            "AND provide an English gloss for downstream clinical use:\n"
            "Return JSON with keys: {transcription, transcription_english, "
            "language_detected, medicines_mentioned, conditions_mentioned, "
            "allergies_mentioned, key_medical_events, patient_emotional_state, "
            "confidence_score (0-1)}"
        ),
        "other": (
            f"This is a medical document ('{filename}'). Extract all medically relevant information:\n"
            "Return JSON with keys: {document_type, medicines_found, conditions_found, "
            "dates_found, doctor_names, medical_events, language_detected, "
            "confidence_score (0-1), raw_text_summary}"
        ),
    }

    specific = category_prompts.get(category, category_prompts["other"])
    return base + specific


# ── Patient & evidence data tools ─────────────────────────────────────

def get_patient_info(patient_id: str) -> dict[str, Any]:
    """Retrieve patient demographics and notes.

    Args:
        patient_id: The patient UUID.

    Returns:
        Dict with patient name, language, age, notes, and evidence file count.
    """
    with db_conn() as conn:
        patient = conn.execute(
            "SELECT * FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        if not patient:
            return {"status": "not_found", "patient_id": patient_id}
        file_count = conn.execute(
            "SELECT COUNT(*) FROM evidence_files WHERE patient_id = ?", (patient_id,)
        ).fetchone()[0]

    # Robust against older DBs that may not have language_other yet.
    try:
        language_other = patient["language_other"]
    except (IndexError, KeyError):
        language_other = None

    return {
        "status": "ok",
        "patient_id": patient_id,
        "name": patient["name"],
        "language": patient["language"],
        "language_other": language_other,
        "age": patient["age"],
        "additional_notes": patient["additional_notes"],
        "voice_note_text": patient["voice_note_text"],
        "evidence_file_count": file_count,
    }


def get_evidence_list(patient_id: str) -> dict[str, Any]:
    """List all uploaded evidence files for a patient.

    Args:
        patient_id: The patient UUID.

    Returns:
        Dict with list of evidence files and their metadata.
    """
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id, original_name, file_type, evidence_category, created_at "
            "FROM evidence_files WHERE patient_id = ? ORDER BY created_at",
            (patient_id,),
        ).fetchall()

    return {
        "status": "ok",
        "patient_id": patient_id,
        "files": [dict(r) for r in rows],
        "total": len(rows),
    }


# ── Pipeline state persistence tools ──────────────────────────────────

def save_raw_extractions(run_id: str, extractions_json: str) -> dict[str, Any]:
    """Persist raw multimodal extraction results to the pipeline run.

    Args:
        run_id: Pipeline run UUID.
        extractions_json: JSON string of extracted data from all files.

    Returns:
        Confirmation dict.
    """
    with db_conn() as conn:
        conn.execute(
            "UPDATE pipeline_runs SET raw_extractions = ? WHERE id = ?",
            (extractions_json, run_id),
        )
    return {"status": "ok", "run_id": run_id, "saved": "raw_extractions"}


def save_structured_data(run_id: str, structured_json: str) -> dict[str, Any]:
    """Persist structured medical data (medications, conditions, allergies, etc.).

    Args:
        run_id: Pipeline run UUID.
        structured_json: JSON string of structured medical data.

    Returns:
        Confirmation dict.
    """
    with db_conn() as conn:
        conn.execute(
            "UPDATE pipeline_runs SET structured_data = ? WHERE id = ?",
            (structured_json, run_id),
        )
    return {"status": "ok", "run_id": run_id, "saved": "structured_data"}


def save_timeline(run_id: str, timeline_json: str) -> dict[str, Any]:
    """Persist reconstructed medical timeline.

    Args:
        run_id: Pipeline run UUID.
        timeline_json: JSON string of chronological medical events.

    Returns:
        Confirmation dict.
    """
    with db_conn() as conn:
        conn.execute(
            "UPDATE pipeline_runs SET timeline_data = ? WHERE id = ?",
            (timeline_json, run_id),
        )
    return {"status": "ok", "run_id": run_id, "saved": "timeline"}


def save_risk_report(run_id: str, risk_json: str) -> dict[str, Any]:
    """Persist risk and uncertainty analysis report.

    Args:
        run_id: Pipeline run UUID.
        risk_json: JSON string of risk flags, confidence scores, uncertainties.

    Returns:
        Confirmation dict.
    """
    with db_conn() as conn:
        conn.execute(
            "UPDATE pipeline_runs SET risk_report = ? WHERE id = ?",
            (risk_json, run_id),
        )
    return {"status": "ok", "run_id": run_id, "saved": "risk_report"}


def save_verification_checklist(run_id: str, checklist_json: str) -> dict[str, Any]:
    """Persist human verification checklist for doctor review.

    Args:
        run_id: Pipeline run UUID.
        checklist_json: JSON string of field-by-field verification items.

    Returns:
        Confirmation dict.
    """
    with db_conn() as conn:
        conn.execute(
            "UPDATE pipeline_runs SET verification_checklist = ? WHERE id = ?",
            (checklist_json, run_id),
        )
    return {"status": "ok", "run_id": run_id, "saved": "verification_checklist"}


def save_passport(run_id: str, passport_json: str) -> dict[str, Any]:
    """Persist the final Emergency Medical Passport data.

    Args:
        run_id: Pipeline run UUID.
        passport_json: JSON string of the complete emergency passport.

    Returns:
        Confirmation dict.
    """
    with db_conn() as conn:
        conn.execute(
            "UPDATE pipeline_runs SET passport_data = ?, status = 'completed', "
            "completed_at = ? WHERE id = ?",
            (passport_json, datetime.now(timezone.utc).isoformat(), run_id),
        )
    return {"status": "ok", "run_id": run_id, "saved": "passport", "pipeline": "completed"}


def get_pipeline_state(run_id: str) -> dict[str, Any]:
    """Retrieve the full current state of a pipeline run.

    Args:
        run_id: Pipeline run UUID.

    Returns:
        Dict with all pipeline state fields (raw extractions, structured data, etc.).
    """
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM pipeline_runs WHERE id = ?", (run_id,)
        ).fetchone()
    if not row:
        return {"status": "not_found", "run_id": run_id}

    state = dict(row)
    # Parse JSON fields
    for field in ["raw_extractions", "structured_data", "timeline_data",
                  "risk_report", "verification_checklist", "passport_data"]:
        if state.get(field):
            try:
                state[field] = json.loads(state[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return {"status": "ok", **state}

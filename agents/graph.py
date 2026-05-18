"""
MedBridge Ukraine — LangGraph Workflow State Machine

Implements the stateful pipeline graph as specified in the MedBridge
architecture document (MedBridge_Ukraine.docx, Sections 9, 11, 13):

  raw_inputs → multimodal_understanding → structured_medical_data
  → timeline_data → confidence_scores → [Human Approval Node]
  → verification_status → final_summary

LangGraph manages all state transitions and the critical human-in-the-loop
approval checkpoint between AI processing and final passport export.

Key design decisions (per docx):
- MedBridgeState(TypedDict)  — exact state fields from the architecture doc
- StateGraph with 7 nodes    — one per pipeline stage
- human_approval_node        — "VERY important" per docx; conditional routing
  based on doctor verification status before final passport generation
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from agents.events import bus
from agents.tools import (
    gemma_generate_json,
    gemma_multimodal_analyze,
    get_evidence_list,
    get_patient_info,
    save_passport,
    save_raw_extractions,
    save_risk_report,
    save_structured_data,
    save_timeline,
    save_verification_checklist,
)
from database.init_db import db_conn
from utils.languages import resolve_language


# ══════════════════════════════════════════════════════════════════════
# STATE DEFINITION  (from MedBridge_Ukraine.docx Section 13)
# ══════════════════════════════════════════════════════════════════════

class MedBridgeState(TypedDict):
    """
    LangGraph state for the full MedBridge pipeline.

    Fields directly match the architecture specification in Section 13
    of MedBridge_Ukraine.docx:

        raw_inputs              → multimodal_understanding
        → structured_medical_data → timeline_data → confidence_scores
        → verification_status   → final_summary
    """
    # ── Core identifiers ──────────────────────────────────────────────
    patient_id: str
    run_id: str

    # ── Stage outputs (docx State fields, exact names) ────────────────
    raw_inputs: dict                # patient profile + evidence file list
    multimodal_understanding: dict  # Gemma 4 raw extractions from all files
    structured_medical_data: dict   # medications, conditions, allergies, vaccinations
    timeline_data: dict             # chronological treatment events
    confidence_scores: dict         # risk report — overall confidence score + flags

    # ── Human-in-the-loop checkpoint ─────────────────────────────────
    verification_checklist: dict    # field-by-field items for doctor/pharmacist review
    verification_status: str        # "pending" | "approved" | "rejected"

    # ── Final output ──────────────────────────────────────────────────
    final_summary: dict             # Emergency Medical Passport

    # ── Metadata ──────────────────────────────────────────────────────
    errors: list
    current_step: int


# ══════════════════════════════════════════════════════════════════════
# HELPER — SSE event publisher
# ══════════════════════════════════════════════════════════════════════

_AGENT_META = {
    0: ("InputCollector",         "Collecting Patient Evidence",         "Loading patient profile and uploaded evidence files"),
    1: ("MultimodalAnalysis",     "Multimodal Evidence Analysis",        "Gemma 4 processing images, voice notes & documents"),
    2: ("MedicalStructuring",     "Medical Data Structuring",            "Organising medications, conditions, allergies & vaccinations"),
    3: ("TimelineReconstruction", "Timeline Reconstruction",             "Rebuilding chronological treatment history"),
    4: ("RiskAnalysis",           "Risk & Uncertainty Analysis",         "Flagging conflicts, missing data & confidence scores"),
    5: ("VerificationPrep",       "Verification Checklist",              "Preparing doctor review items"),
    6: ("HumanApproval",          "Human Approval Checkpoint",           "Checking doctor verification status"),
    7: ("PassportGeneration",     "Passport Generation",                 "Creating Emergency Medical Passport"),
}


def _pub(run_id: str, step: int, event_type: str, extra: dict | None = None) -> None:
    agent_key, label, description = _AGENT_META[step]
    payload: dict[str, Any] = {
        "type": event_type,
        "agent": agent_key,
        "agent_label": label,
        "description": description,
        "step": step,
    }
    if extra:
        payload.update(extra)
    bus.publish(run_id, payload)


def _safe_json(data: Any, limit: int = 4000) -> str:
    """Dump data to JSON string, truncated for prompt injection safety."""
    try:
        s = json.dumps(data, default=str, ensure_ascii=False)
    except Exception:
        s = str(data)
    return s[:limit]


# ══════════════════════════════════════════════════════════════════════
# NODE 0 — collect_inputs
# ══════════════════════════════════════════════════════════════════════

def collect_inputs_node(state: MedBridgeState) -> dict:
    """Fetch patient profile and evidence file list into pipeline state."""
    patient_id = state["patient_id"]
    run_id = state["run_id"]

    _pub(run_id, 0, "agent_start")

    patient_info = get_patient_info(patient_id=patient_id)
    evidence_list = get_evidence_list(patient_id=patient_id)

    raw_inputs = {
        "patient": patient_info,
        "evidence_files": evidence_list.get("files", []),
        "total_files": evidence_list.get("total", 0),
    }

    _pub(run_id, 0, "agent_done", {
        "detail": f"Loaded {raw_inputs['total_files']} evidence file(s) for patient."
    })

    return {"raw_inputs": raw_inputs, "current_step": 1}


# ══════════════════════════════════════════════════════════════════════
# NODE 1 — multimodal_analysis
# ══════════════════════════════════════════════════════════════════════

def multimodal_analysis_node(state: MedBridgeState) -> dict:
    """Process all uploaded evidence via Gemma 4 multimodal intelligence."""
    patient_id = state["patient_id"]
    run_id = state["run_id"]

    _pub(run_id, 1, "agent_start")

    result = gemma_multimodal_analyze(patient_id=patient_id, category_filter="all")

    extractions = result.get("extractions", [])
    save_raw_extractions(run_id=run_id, extractions_json=json.dumps(extractions))

    _pub(run_id, 1, "agent_done", {
        "detail": f"Processed {len(extractions)} file(s) with Gemma 4 multimodal."
    })

    return {
        "multimodal_understanding": {
            "extractions": extractions,
            "total_files_processed": len(extractions),
            "status": result.get("status", "ok"),
        },
        "current_step": 2,
    }


# ══════════════════════════════════════════════════════════════════════
# NODE 2 — medical_structuring
# ══════════════════════════════════════════════════════════════════════

def medical_structuring_node(state: MedBridgeState) -> dict:
    """Convert raw Gemma 4 extractions into a structured medical profile."""
    run_id = state["run_id"]
    raw = state.get("multimodal_understanding", {})
    patient = state.get("raw_inputs", {}).get("patient", {})
    lang = resolve_language(patient.get("language"), patient.get("language_other"))

    _pub(run_id, 2, "agent_start")

    extractions_summary = _safe_json(raw.get("extractions", []))
    patient_context = (
        f"Patient: {patient.get('name', 'Unknown')}, "
        f"Primary language: {lang['display_name']} (code: {lang['code']}"
        f"{', RTL script' if lang['rtl'] else ''}), "
        f"Notes: {patient.get('additional_notes', 'None')}"
    )

    prompt = f"""You are the Medical Data Structuring Agent for MedBridge.
Convert raw multimodal evidence extractions into a clean, structured medical profile.

PATIENT CONTEXT: {patient_context}

RAW EVIDENCE EXTRACTIONS:
{extractions_summary}

Instructions:
- Merge duplicate medicines (same drug found in multiple files → one entry)
- Preserve confidence scores from each extraction
- Mark uncertain items clearly
- Source documents may be in ANY language or script. Normalise medication names
  to their international (English/Latin-script) form when possible, but keep the
  original-script name in a `name_native` field if it appears in the evidence.
- Do NOT diagnose — only structure what is explicitly found in evidence

Return ONLY a valid JSON object with this exact schema:
{{
  "medications": [
    {{"name": "...", "generic_name": "...", "dosage": "...", "frequency": "...",
      "route": "oral|iv|other", "start_date": "...", "end_date": "...",
      "prescribing_doctor": "...", "confidence": 0.0}}
  ],
  "chronic_conditions": [
    {{"condition": "...", "icd_code_hint": "...", "since_date": "...", "confidence": 0.0}}
  ],
  "allergies": [
    {{"substance": "...", "reaction_type": "...", "severity": "mild|moderate|severe", "confidence": 0.0}}
  ],
  "surgeries": [
    {{"procedure": "...", "date": "...", "hospital": "...", "confidence": 0.0}}
  ],
  "vaccinations": [
    {{"vaccine": "...", "dates": [], "dose_count": 0, "confidence": 0.0}}
  ],
  "blood_type": {{"type": "...", "confidence": 0.0}},
  "overall_data_quality": "poor|fair|good",
  "languages_detected": [],
  "completeness_score": 0.0
}}"""

    result = gemma_generate_json(prompt=prompt, purpose="medical_structuring")
    structured = result.get("data", {}) if result.get("status") == "ok" else {}

    save_structured_data(run_id=run_id, structured_json=json.dumps(structured))

    _pub(run_id, 2, "agent_done", {
        "detail": f"Structured {len(structured.get('medications', []))} medication(s), "
                  f"{len(structured.get('chronic_conditions', []))} condition(s), "
                  f"{len(structured.get('allergies', []))} allerg(y/ies)."
    })

    return {"structured_medical_data": structured, "current_step": 3}


# ══════════════════════════════════════════════════════════════════════
# NODE 3 — timeline_reconstruction
# ══════════════════════════════════════════════════════════════════════

def timeline_reconstruction_node(state: MedBridgeState) -> dict:
    """Rebuild the patient's chronological treatment history."""
    run_id = state["run_id"]
    structured = state.get("structured_medical_data", {})

    _pub(run_id, 3, "agent_start")

    prompt = f"""You are the Medical Timeline Reconstruction Agent for MedBridge Ukraine.
Build a chronological treatment history from structured medical data.

STRUCTURED MEDICAL DATA:
{_safe_json(structured)}

Instructions:
- When dates are uncertain, use date_confidence: "approximate" or "inferred"
- Identify clear gaps in treatment history
- Note where evidence is strongest vs weakest
- Reconstruct probable treatment continuity even from incomplete data

Return ONLY a valid JSON object:
{{
  "timeline_events": [
    {{
      "date": "YYYY-MM or approximate description",
      "date_confidence": "exact|approximate|inferred",
      "event_type": "hospitalization|medication_start|medication_change|diagnosis|surgery|vaccination|other",
      "description": "...",
      "medicines_involved": [],
      "source_evidence": "file name or evidence description",
      "confidence": 0.0
    }}
  ],
  "treatment_continuity_assessment": "narrative paragraph",
  "identified_gaps": ["gap description 1", "gap description 2"],
  "earliest_known_date": "...",
  "latest_known_date": "...",
  "total_events": 0
}}"""

    result = gemma_generate_json(prompt=prompt, purpose="timeline_reconstruction")
    timeline = result.get("data", {}) if result.get("status") == "ok" else {}

    save_timeline(run_id=run_id, timeline_json=json.dumps(timeline))

    event_count = len(timeline.get("timeline_events", []))
    _pub(run_id, 3, "agent_done", {
        "detail": f"Reconstructed {event_count} timeline event(s). "
                  f"Gaps: {len(timeline.get('identified_gaps', []))}."
    })

    return {"timeline_data": timeline, "current_step": 4}


# ══════════════════════════════════════════════════════════════════════
# NODE 4 — risk_analysis
# ══════════════════════════════════════════════════════════════════════

def risk_analysis_node(state: MedBridgeState) -> dict:
    """Detect risks, conflicts, and generate confidence scores. Flag everything."""
    run_id = state["run_id"]
    structured = state.get("structured_medical_data", {})
    timeline = state.get("timeline_data", {})

    _pub(run_id, 4, "agent_start")

    prompt = f"""You are the Risk & Uncertainty Analysis Agent for MedBridge Ukraine.
NOTHING should be assumed as medical truth — flag ALL uncertainties conservatively.

STRUCTURED MEDICAL DATA:
{_safe_json(structured, 2000)}

TIMELINE DATA:
{_safe_json(timeline, 1500)}

Instructions:
- Never minimise risks — err on the side of caution
- Flag ALL drug interactions as requiring pharmacist verification
- Any missing allergy information is CRITICAL severity
- This system assists continuity; it does NOT replace medical judgment

Return ONLY a valid JSON object:
{{
  "overall_confidence_score": 0.0,
  "data_quality_grade": "A|B|C|D|F",
  "critical_flags": [
    {{
      "type": "missing_allergy_info|drug_conflict|unclear_dosage|incomplete_history|other",
      "severity": "critical|high|medium|low",
      "description": "...",
      "affected_item": "...",
      "requires_verification": true
    }}
  ],
  "drug_interactions_to_check": [
    {{"drug1": "...", "drug2": "...", "concern": "..."}}
  ],
  "missing_information": ["missing item 1", "missing item 2"],
  "low_confidence_items": [
    {{"item": "...", "reason": "...", "confidence": 0.0}}
  ],
  "language_barriers_noted": [],
  "recommendation_for_doctor": "...",
  "safe_to_use_for_emergency": true,
  "emergency_caveat": "Always verify with treating clinician before any treatment decision."
}}"""

    result = gemma_generate_json(prompt=prompt, purpose="risk_analysis")
    risk_report = result.get("data", {}) if result.get("status") == "ok" else {}

    save_risk_report(run_id=run_id, risk_json=json.dumps(risk_report))

    score = risk_report.get("overall_confidence_score", 0)
    flags = len(risk_report.get("critical_flags", []))
    _pub(run_id, 4, "agent_done", {
        "detail": f"Confidence score: {score:.0%}. Critical flags: {flags}."
    })

    return {"confidence_scores": risk_report, "current_step": 5}


# ══════════════════════════════════════════════════════════════════════
# NODE 5 — verification_prep
# ══════════════════════════════════════════════════════════════════════

def verification_prep_node(state: MedBridgeState) -> dict:
    """Prepare the doctor/pharmacist verification checklist."""
    run_id = state["run_id"]
    structured = state.get("structured_medical_data", {})
    risk = state.get("confidence_scores", {})

    _pub(run_id, 5, "agent_start")

    prompt = f"""You are the Human Verification Preparation Agent for MedBridge Ukraine.
Create a comprehensive checklist for doctors/pharmacists to review.
This is the MOST IMPORTANT ethical pillar — humans must stay in control.

STRUCTURED MEDICAL DATA:
{_safe_json(structured, 2000)}

RISK REPORT:
{_safe_json(risk, 1500)}

Instructions:
- All critical risk items MUST appear in mandatory_verifications
- Include clear guidance for each item on HOW to verify
- Mark items needing specialist review
- Every item starts with verification_status: "pending"

Return ONLY a valid JSON object:
{{
  "checklist_version": "1.0",
  "total_items": 0,
  "sections": [
    {{
      "section_name": "Medications|Allergies|Conditions|Timeline|Other",
      "priority": "critical|high|medium|low",
      "items": [
        {{
          "id": "unique_id",
          "field_name": "...",
          "ai_extracted_value": "...",
          "confidence": 0.0,
          "verification_status": "pending",
          "requires_specialist": false,
          "doctor_note_placeholder": "Click to add verification note",
          "source_evidence": "...",
          "verification_guidance": "Specific guidance on how to verify this item"
        }}
      ]
    }}
  ],
  "mandatory_verifications": ["id1", "id2"],
  "overall_guidance": "Instructions for the reviewing clinician"
}}"""

    result = gemma_generate_json(prompt=prompt, purpose="verification_prep")
    checklist = result.get("data", {}) if result.get("status") == "ok" else {}

    save_verification_checklist(run_id=run_id, checklist_json=json.dumps(checklist))

    total = checklist.get("total_items", len(checklist.get("mandatory_verifications", [])))
    _pub(run_id, 5, "agent_done", {
        "detail": f"Checklist ready: {total} item(s) for doctor review."
    })

    return {"verification_checklist": checklist, "current_step": 6}


# ══════════════════════════════════════════════════════════════════════
# NODE 6 — human_approval_node  (THE KEY INNOVATION — docx Section 13)
# ══════════════════════════════════════════════════════════════════════

def human_approval_node(state: MedBridgeState) -> dict:
    """
    Human-in-the-loop approval checkpoint.

    Per MedBridge_Ukraine.docx Section 13 (LangGraph Workflow Design):
      'This is VERY important.'
      'AI Processing → Human Approval Node → Final Export'
      'This becomes a major innovation point in the architecture.'

    Checks the database for a doctor's verification decision:
    - "approved"  → passport generation proceeds with full confidence
    - "rejected"  → pipeline halts with rejection notice
    - "pending"   → passport generated with strong AI-only disclaimers

    The conditional edge routes to either:
      'approved_path' or 'pending_path'
    Both lead to passport_generation_node (with different confidence contexts).
    """
    run_id = state["run_id"]

    _pub(run_id, 6, "agent_start", {
        "detail": "Checking doctor verification status before final export."
    })

    # Check DB for doctor verification
    verification_status = "pending"
    try:
        with db_conn() as conn:
            row = conn.execute(
                "SELECT overall_status FROM verifications WHERE run_id = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (run_id,),
            ).fetchone()
            if row:
                verification_status = row["overall_status"] or "pending"
    except Exception:
        verification_status = "pending"

    status_label = {
        "approved": "Doctor has approved the AI extractions. Generating high-confidence passport.",
        "rejected": "Doctor has rejected. Passport will include rejection notice.",
        "pending":  "Awaiting doctor review. Generating preliminary passport with disclaimers.",
    }.get(verification_status, "pending")

    _pub(run_id, 6, "agent_done", {"detail": status_label})

    return {"verification_status": verification_status, "current_step": 7}


def _route_after_approval(state: MedBridgeState) -> str:
    """Conditional edge: route based on verification status."""
    status = state.get("verification_status", "pending")
    if status == "approved":
        return "approved_path"
    elif status == "rejected":
        return "rejected_path"
    return "pending_path"   # default: generate preliminary passport


# ══════════════════════════════════════════════════════════════════════
# NODE 7a — passport_generation (approved or pending)
# ══════════════════════════════════════════════════════════════════════

def passport_generation_node(state: MedBridgeState) -> dict:
    """Generate the Emergency Medical Passport — final pipeline output."""
    run_id = state["run_id"]
    patient = state.get("raw_inputs", {}).get("patient", {})
    structured = state.get("structured_medical_data", {})
    timeline = state.get("timeline_data", {})
    risk = state.get("confidence_scores", {})
    checklist = state.get("verification_checklist", {})
    verification_status = state.get("verification_status", "pending")
    lang = resolve_language(patient.get("language"), patient.get("language_other"))

    _pub(run_id, 7, "agent_start")

    doctor_approved = verification_status == "approved"
    approval_note = (
        "This passport has been reviewed and approved by a licensed clinician."
        if doctor_approved
        else "PRELIMINARY: AI-assisted only. Clinician verification required before any treatment decision."
    )

    # Always produce English (clinical lingua franca) + the patient's own
    # language so the patient can read and confirm their own record.
    patient_lang_code = lang["code"]
    patient_lang_name = lang["display_name"]
    summary_languages: list[tuple[str, str]] = [("en", "English")]
    if patient_lang_code and patient_lang_code != "en":
        summary_languages.append((patient_lang_code, patient_lang_name))
    summary_schema_lines = ",\n    ".join(
        f'"{code}": "{name} summary (2-3 sentences, written natively in {name})"'
        for code, name in summary_languages
    )

    prompt = f"""You are the Emergency Medical Passport Generation Agent for MedBridge.
Create the final Emergency Medical Passport for a displaced refugee or migrant patient.
This document will be used by doctors, border healthcare workers, and emergency responders.

PATIENT: {patient.get('name', 'Unknown')}
PATIENT PRIMARY LANGUAGE: {patient_lang_name} (code: {patient_lang_code}{', right-to-left script' if lang['rtl'] else ''})
VERIFICATION STATUS: {verification_status.upper()}

STRUCTURED MEDICAL DATA:
{_safe_json(structured, 1800)}

TIMELINE SUMMARY:
{_safe_json(timeline.get('treatment_continuity_assessment', 'Not available'), 400)}

RISK REPORT (confidence score: {risk.get('overall_confidence_score', 0):.0%}):
{_safe_json(risk, 1000)}

APPROVAL NOTE: {approval_note}

LANGUAGE RULES (CRITICAL):
- Clinical fields (medication names, conditions, allergies) MUST be written in
  English / Latin script so any clinician anywhere can read them.
- `multilingual_summary` MUST contain one entry per language listed in the
  schema below. Write each summary natively in that language's own script —
  do NOT transliterate.
- If the patient's language is a tribal or indigenous language without a
  standard written form, write the patient-language summary in the closest
  major regional language and add a "(spoken: <language name>)" suffix.
- `patient_facing_instructions` must be in the patient's own language so the
  patient can read and confirm their own record.

Generate a complete, life-saving Emergency Medical Passport.
Return ONLY a valid JSON object:
{{
  "passport_id": "auto",
  "generation_timestamp": "{datetime.now(timezone.utc).isoformat()}",
  "verification_status": "{verification_status}",
  "patient": {{
    "name": "...", "age": null,
    "language": "{patient_lang_name}",
    "language_code": "{patient_lang_code}",
    "emergency_contact": "Unknown - not provided"
  }},
  "critical_allergies": [
    {{"substance": "...", "reaction": "...", "severity": "mild|moderate|severe|unknown"}}
  ],
  "current_medications": [
    {{"name": "...", "dosage": "...", "frequency": "...", "confidence_note": "..."}}
  ],
  "chronic_conditions": [
    {{"condition": "...", "since": "...", "management": "..."}}
  ],
  "blood_type": {{"type": "...", "confidence": 0.0}},
  "recent_hospitalizations": [
    {{"date": "...", "reason": "...", "hospital": "...", "confidence": 0.0}}
  ],
  "vaccination_status": [
    {{"vaccine": "...", "last_dose": "...", "confidence": 0.0}}
  ],
  "medical_timeline_summary": "Narrative paragraph of treatment history (in English)",
  "risk_flags": [
    {{"flag": "...", "severity": "critical|high|medium|low", "action_required": "..."}}
  ],
  "multilingual_summary": {{
    {summary_schema_lines}
  }},
  "patient_facing_instructions": "Plain-language guidance for the patient, written in {patient_lang_name} so the patient can read and confirm their own record.",
  "data_confidence": {{
    "overall_score": 0.0,
    "grade": "A|B|C|D|F",
    "caveat": "Reconstructed from fragmented evidence. Human verification required."
  }},
  "verification_disclaimer": "{approval_note}",
  "qr_data": "Compact JSON string: critical allergies + current medications only"
}}"""

    result = gemma_generate_json(prompt=prompt, purpose="passport_generation")
    passport = result.get("data", {}) if result.get("status") == "ok" else {
        "error": "Passport generation failed",
        "verification_status": verification_status,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    save_passport(run_id=run_id, passport_json=json.dumps(passport))

    _pub(run_id, 7, "agent_done", {
        "detail": "Emergency Medical Passport created. Ready for clinician review and export."
    })

    return {"final_summary": passport, "current_step": 8}


# ══════════════════════════════════════════════════════════════════════
# NODE 7b — rejected_path  (doctor rejected — skip passport generation)
# ══════════════════════════════════════════════════════════════════════

def rejection_node(state: MedBridgeState) -> dict:
    """Handle pipeline rejection by doctor — create a minimal rejection notice."""
    run_id = state["run_id"]

    rejection_passport = {
        "passport_id": "rejected",
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "verification_status": "rejected",
        "verification_disclaimer": (
            "A licensed clinician has reviewed and rejected the AI-generated data. "
            "Manual medical history collection is required."
        ),
        "multilingual_summary": {
            "en": "Data rejected by clinician. Manual review required.",
            "uk": "Дані відхилені лікарем. Необхідний ручний огляд.",
        },
        "data_confidence": {
            "overall_score": 0.0,
            "grade": "F",
            "caveat": "Rejected by clinician. Do not use for treatment.",
        },
    }

    save_passport(run_id=run_id, passport_json=json.dumps(rejection_passport))

    bus.publish(run_id, {
        "type": "pipeline_rejected",
        "run_id": run_id,
        "message": "Pipeline output rejected by clinician. Manual intake required.",
    })

    return {"final_summary": rejection_passport, "current_step": 8}


# ══════════════════════════════════════════════════════════════════════
# GRAPH CONSTRUCTION
# ══════════════════════════════════════════════════════════════════════

def build_graph() -> StateGraph:
    """
    Build and compile the MedBridge LangGraph StateGraph.

    Graph topology (per MedBridge_Ukraine.docx Section 11 — Agentic Architecture Flow):

        START
          ↓
        collect_inputs          (Node 0: load patient + evidence list)
          ↓
        multimodal_analysis     (Node 1: Gemma 4 processes all files)
          ↓
        medical_structuring     (Node 2: organise into medications/conditions/etc.)
          ↓
        timeline_reconstruction (Node 3: build chronological history)
          ↓
        risk_analysis           (Node 4: flag risks, score confidence)
          ↓
        verification_prep       (Node 5: prepare doctor checklist)
          ↓
        human_approval          (Node 6: CHECK human verification status ← INNOVATION)
          ↓ conditional
        ┌──────────────────────────────────────────────────┐
        │ approved_path          pending_path   rejected_path │
        └──────────────────────────────────────────────────┘
          ↓                      ↓                ↓
        passport_generation   passport_generation  rejection
          ↓                      ↓                ↓
                               END
    """
    graph = StateGraph(MedBridgeState)

    # ── Add nodes ─────────────────────────────────────────────────────
    graph.add_node("collect_inputs",          collect_inputs_node)
    graph.add_node("multimodal_analysis",     multimodal_analysis_node)
    graph.add_node("medical_structuring",     medical_structuring_node)
    graph.add_node("timeline_reconstruction", timeline_reconstruction_node)
    graph.add_node("risk_analysis",           risk_analysis_node)
    graph.add_node("verification_prep",       verification_prep_node)
    graph.add_node("human_approval",          human_approval_node)
    graph.add_node("passport_generation",     passport_generation_node)
    graph.add_node("rejection",               rejection_node)

    # ── Sequential edges ──────────────────────────────────────────────
    graph.add_edge(START,                    "collect_inputs")
    graph.add_edge("collect_inputs",         "multimodal_analysis")
    graph.add_edge("multimodal_analysis",    "medical_structuring")
    graph.add_edge("medical_structuring",    "timeline_reconstruction")
    graph.add_edge("timeline_reconstruction","risk_analysis")
    graph.add_edge("risk_analysis",          "verification_prep")
    graph.add_edge("verification_prep",      "human_approval")

    # ── Conditional edge at Human Approval Node ───────────────────────
    graph.add_conditional_edges(
        "human_approval",
        _route_after_approval,
        {
            "approved_path": "passport_generation",
            "pending_path":  "passport_generation",
            "rejected_path": "rejection",
        },
    )

    # ── Terminal edges ────────────────────────────────────────────────
    graph.add_edge("passport_generation", END)
    graph.add_edge("rejection",           END)

    return graph.compile()


# ── Module-level compiled graph ───────────────────────────────────────
MEDBRIDGE_GRAPH = build_graph()

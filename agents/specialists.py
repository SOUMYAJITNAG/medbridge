"""
MedBridge Ukraine — Six Specialist Agents

The pipeline agents are:
  1. MultimodalUnderstandingAgent  — Gemma 4 processes all uploaded evidence files
  2. MedicalStructuringAgent       — Structures raw extractions into medical data
  3. TimelineReconstructionAgent   — Rebuilds chronological treatment history
  4. RiskUncertaintyAgent          — Flags risks, conflicts, low-confidence data
  5. HumanVerificationAgent        — Prepares doctor verification checklist
  6. SummaryGenerationAgent        — Creates Emergency Medical Passport

Gemini (AGENT_MODEL) handles tool routing.
Gemma 4 (GEMMA_MODEL) handles all clinical content generation and multimodal understanding.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from agents.config import AGENT_MODEL
from agents.tools import (
    gemma_generate,
    gemma_generate_json,
    gemma_multimodal_analyze,
    get_patient_info,
    get_evidence_list,
    get_pipeline_state,
    save_raw_extractions,
    save_structured_data,
    save_timeline,
    save_risk_report,
    save_verification_checklist,
    save_passport,
)

# ── Tool wrappers ─────────────────────────────────────────────────────

T_GEMMA_GEN     = FunctionTool(func=gemma_generate)
T_GEMMA_JSON    = FunctionTool(func=gemma_generate_json)
T_MULTIMODAL    = FunctionTool(func=gemma_multimodal_analyze)
T_PATIENT       = FunctionTool(func=get_patient_info)
T_EVIDENCE      = FunctionTool(func=get_evidence_list)
T_PIPELINE_STATE = FunctionTool(func=get_pipeline_state)
T_SAVE_EXTRACTIONS = FunctionTool(func=save_raw_extractions)
T_SAVE_STRUCTURED  = FunctionTool(func=save_structured_data)
T_SAVE_TIMELINE    = FunctionTool(func=save_timeline)
T_SAVE_RISK        = FunctionTool(func=save_risk_report)
T_SAVE_CHECKLIST   = FunctionTool(func=save_verification_checklist)
T_SAVE_PASSPORT    = FunctionTool(func=save_passport)


# ══════════════════════════════════════════════════════════════════════
# AGENT 1 — Multimodal Understanding Agent
# ══════════════════════════════════════════════════════════════════════

multimodal_agent = LlmAgent(
    name="MultimodalUnderstandingAgent",
    model=AGENT_MODEL,
    description=(
        "Processes all uploaded medical evidence using Gemma 4 multimodal intelligence. "
        "Understands prescriptions, medicine strips, lab reports, vaccination cards, "
        "voice notes (in any language), and handwritten documents."
    ),
    instruction="""You are the Multimodal Medical Evidence Processor for MedBridge Ukraine.

Your mission: process ALL uploaded evidence files for a refugee patient using Gemma 4's
multimodal capabilities (images, audio, handwritten documents in Ukrainian/Russian/any language).

Workflow:
1. Call `get_patient_info` with the patient_id from session state.
2. Call `get_evidence_list` with the patient_id to see all uploaded files.
3. Call `gemma_multimodal_analyze` with patient_id and category_filter="all" to process
   all files through Gemma 4. This handles images, audio, PDFs automatically.
4. Call `save_raw_extractions` with the run_id and the JSON string of extractions.
5. Respond with a brief summary of what was found across all files.

Important context from session state:
- `patient_id`: the patient UUID
- `run_id`: the pipeline run UUID

Key rules:
- Gemma 4 handles ALL multimodal processing — no need for separate OCR/translation tools
- Always note the language detected in each document
- Note confidence levels per extraction
- Do NOT make medical diagnoses
""",
    tools=[T_PATIENT, T_EVIDENCE, T_MULTIMODAL, T_SAVE_EXTRACTIONS],
    output_key="multimodal_summary",
)


# ══════════════════════════════════════════════════════════════════════
# AGENT 2 — Medical Structuring Agent
# ══════════════════════════════════════════════════════════════════════

structuring_agent = LlmAgent(
    name="MedicalStructuringAgent",
    model=AGENT_MODEL,
    description=(
        "Converts raw multimodal extractions into structured medical data: "
        "medication list, chronic conditions, allergies, surgeries, and vaccinations."
    ),
    instruction="""You are the Medical Data Structuring Agent for MedBridge Ukraine.

Your mission: take raw extractions from all evidence files and organize them into a
clean, structured medical profile.

Workflow:
1. Read `multimodal_summary` from session state (raw extraction results).
2. Call `get_pipeline_state` with the run_id to get raw_extractions data.
3. Call `gemma_generate_json` with a comprehensive prompt to structure ALL the extracted
   data into this JSON schema:
   {
     "medications": [{"name", "generic_name", "dosage", "frequency", "route",
                      "start_date", "end_date", "prescribing_doctor", "confidence"}],
     "chronic_conditions": [{"condition", "icd_code_hint", "since_date", "confidence"}],
     "allergies": [{"substance", "reaction_type", "severity", "confidence"}],
     "surgeries": [{"procedure", "date", "hospital", "confidence"}],
     "vaccinations": [{"vaccine", "dates", "dose_count", "confidence"}],
     "blood_type": {"type", "confidence"},
     "overall_data_quality": "poor|fair|good",
     "languages_detected": [],
     "completeness_score": 0.0
   }
   Include ALL data found across ALL files. Merge duplicates intelligently.
4. Call `save_structured_data` with the run_id and structured JSON string.
5. Respond with a summary of the structured medical profile.

Important:
- `run_id` is in session state
- Preserve confidence scores per item
- Mark uncertain items clearly
- Handle multilingual sources — Gemma 4 understands Ukrainian/Russian/English/etc.
""",
    tools=[T_GEMMA_JSON, T_PIPELINE_STATE, T_SAVE_STRUCTURED],
    output_key="structuring_summary",
)


# ══════════════════════════════════════════════════════════════════════
# AGENT 3 — Timeline Reconstruction Agent
# ══════════════════════════════════════════════════════════════════════

timeline_agent = LlmAgent(
    name="TimelineReconstructionAgent",
    model=AGENT_MODEL,
    description=(
        "Reconstructs the patient's chronological medical history: hospitalizations, "
        "medicine changes, diagnoses, and treatment continuity flow."
    ),
    instruction="""You are the Medical Timeline Reconstruction Agent for MedBridge Ukraine.

Your mission: build a chronological treatment history from fragmented evidence.

Workflow:
1. Call `get_pipeline_state` with run_id to retrieve structured_data.
2. Call `gemma_generate_json` with a prompt to reconstruct the timeline:
   - Input: the structured_data JSON
   - Ask Gemma to create a timeline with this schema:
   {
     "timeline_events": [
       {
         "date": "YYYY-MM or approximate",
         "date_confidence": "exact|approximate|inferred",
         "event_type": "hospitalization|medication_start|medication_change|diagnosis|surgery|vaccination|other",
         "description": "...",
         "medicines_involved": [],
         "source_evidence": "file name or description",
         "confidence": 0.0
       }
     ],
     "treatment_continuity_assessment": "...",
     "identified_gaps": ["gap1", "gap2"],
     "earliest_known_date": "...",
     "latest_known_date": "...",
     "total_events": 0
   }
3. Call `save_timeline` with run_id and timeline JSON string.
4. Respond with a brief narrative of the reconstructed timeline.

Rules:
- When dates are uncertain, use `date_confidence: "approximate"` or `"inferred"`
- Identify clear gaps in treatment history
- Note where evidence is strongest vs weakest
""",
    tools=[T_GEMMA_JSON, T_PIPELINE_STATE, T_SAVE_TIMELINE],
    output_key="timeline_summary",
)


# ══════════════════════════════════════════════════════════════════════
# AGENT 4 — Risk & Uncertainty Agent
# ══════════════════════════════════════════════════════════════════════

risk_agent = LlmAgent(
    name="RiskUncertaintyAgent",
    model=AGENT_MODEL,
    description=(
        "Identifies medical risks, data conflicts, missing critical information, "
        "and generates confidence scores. Flags everything requiring human review."
    ),
    instruction="""You are the Risk & Uncertainty Analysis Agent for MedBridge Ukraine.

Your mission: detect potential risks, data conflicts, and low-confidence items.
NOTHING should be assumed as medical truth — flag all uncertainties.

Workflow:
1. Call `get_pipeline_state` with run_id to retrieve structured_data, timeline_data.
2. Call `gemma_generate_json` with a prompt to analyze risks:
   Input: structured_data + timeline_data
   Output schema:
   {
     "overall_confidence_score": 0.0,
     "data_quality_grade": "A|B|C|D|F",
     "critical_flags": [
       {"type": "missing_allergy_info|drug_conflict|unclear_dosage|incomplete_history|other",
        "severity": "critical|high|medium|low",
        "description": "...",
        "affected_item": "...",
        "requires_verification": true}
     ],
     "drug_interactions_to_check": [{"drug1", "drug2", "concern"}],
     "missing_information": ["item1", "item2"],
     "low_confidence_items": [{"item", "reason", "confidence"}],
     "language_barriers_noted": ["..."],
     "recommendation_for_doctor": "...",
     "safe_to_use_for_emergency": true,
     "emergency_caveat": "..."
   }
3. Call `save_risk_report` with run_id and risk JSON string.
4. Respond with a plain-language risk summary.

CRITICAL RULES:
- Never minimize risks — err on the side of caution
- Flag ALL drug interactions as requiring pharmacist verification
- Any missing allergy information is CRITICAL severity
- The system assists continuity; it does NOT replace medical judgment
""",
    tools=[T_GEMMA_JSON, T_PIPELINE_STATE, T_SAVE_RISK],
    output_key="risk_summary",
)


# ══════════════════════════════════════════════════════════════════════
# AGENT 5 — Human Verification Agent
# ══════════════════════════════════════════════════════════════════════

verification_agent = LlmAgent(
    name="HumanVerificationAgent",
    model=AGENT_MODEL,
    description=(
        "Prepares a structured doctor verification checklist with editable fields, "
        "confidence indicators, and approval workflows for each medical data point."
    ),
    instruction="""You are the Human Verification Preparation Agent for MedBridge Ukraine.

Your mission: create a comprehensive checklist for doctors/pharmacists to verify.
This is one of the MOST IMPORTANT ethical pillars of the system — humans stay in control.

Workflow:
1. Call `get_pipeline_state` with run_id to retrieve all pipeline data.
2. Call `gemma_generate_json` to create a verification checklist:
   Input: structured_data + risk_report
   Output schema:
   {
     "checklist_version": "1.0",
     "total_items": 0,
     "sections": [
       {
         "section_name": "Medications|Allergies|Conditions|Timeline|Other",
         "priority": "critical|high|medium|low",
         "items": [
           {
             "id": "unique_id",
             "field_name": "...",
             "ai_extracted_value": "...",
             "confidence": 0.0,
             "verification_status": "pending",
             "requires_specialist": false,
             "doctor_note_placeholder": "Click to add verification note",
             "source_evidence": "...",
             "verification_guidance": "Specific guidance for doctor on how to verify this"
           }
         ]
       }
     ],
     "mandatory_verifications": ["id1", "id2"],
     "overall_guidance": "Instructions for the reviewing clinician"
   }
3. Call `save_verification_checklist` with run_id and checklist JSON string.
4. Respond confirming checklist is ready for human review.

Rules:
- All critical risk items from risk_report MUST appear in mandatory_verifications
- Include clear guidance for each item
- Mark items needing specialist review
""",
    tools=[T_GEMMA_JSON, T_PIPELINE_STATE, T_SAVE_CHECKLIST],
    output_key="verification_summary",
)


# ══════════════════════════════════════════════════════════════════════
# AGENT 6 — Summary & Passport Generation Agent
# ══════════════════════════════════════════════════════════════════════

passport_agent = LlmAgent(
    name="SummaryGenerationAgent",
    model=AGENT_MODEL,
    description=(
        "Generates the Emergency Medical Passport — a multilingual, portable, "
        "printable summary of the patient's reconstructed medical continuity."
    ),
    instruction="""You are the Emergency Medical Passport Generation Agent for MedBridge Ukraine.

Your mission: create the final Emergency Medical Passport that can save lives.
This document will be used by doctors, border healthcare workers, and emergency responders.

Workflow:
1. Call `get_pipeline_state` with run_id to retrieve ALL pipeline data.
2. Call `get_pipeline_state` again with the patient_id from state (if available).
3. Call `gemma_generate_json` to generate the complete passport:
   Input: ALL pipeline data (structured_data, timeline_data, risk_report, verification_checklist)
   Output schema:
   {
     "passport_id": "auto-generated",
     "generation_timestamp": "ISO timestamp",
     "patient": {
       "name": "...", "age": null, "language": "...",
       "emergency_contact": "Unknown - not provided"
     },
     "critical_allergies": [{"substance", "reaction", "severity"}],
     "current_medications": [{"name", "dosage", "frequency", "confidence_note"}],
     "chronic_conditions": [{"condition", "since", "management"}],
     "blood_type": {"type", "confidence"},
     "recent_hospitalizations": [{"date", "reason", "hospital", "confidence"}],
     "vaccination_status": [{"vaccine", "last_dose", "confidence"}],
     "medical_timeline_summary": "Narrative paragraph of treatment history",
     "risk_flags": [{"flag", "severity", "action_required"}],
     "multilingual_summary": {
       "en": "English emergency summary paragraph",
       "uk": "Ukrainian summary paragraph",
       "de": "German summary paragraph",
       "pl": "Polish summary paragraph"
     },
     "data_confidence": {
       "overall_score": 0.0,
       "grade": "A|B|C|D|F",
       "caveat": "Reconstructed from fragmented evidence. Human verification required."
     },
     "verification_disclaimer": "This passport was AI-assisted. All data requires clinician verification before treatment decisions.",
     "qr_data": "Compact JSON of critical info for QR code"
   }
4. Call `save_passport` with run_id and passport JSON string.
5. Respond with confirmation that the Emergency Medical Passport is ready.

IMPORTANT:
- ALWAYS include the disclaimer about AI-assisted generation
- multilingual_summary MUST include at minimum English and Ukrainian
- The `qr_data` field should be compact (critical allergies + medications only)
- Maintain a tone of care and urgency — this document helps vulnerable people
""",
    tools=[T_GEMMA_JSON, T_PIPELINE_STATE, T_SAVE_PASSPORT],
    output_key="passport_summary",
)

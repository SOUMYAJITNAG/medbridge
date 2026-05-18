# 🌍 MedBridge — Medical Continuity for Displaced People Worldwide

> *An open-source, AI-powered platform leveraging Google Gemma 4 to bridge the language gap and reconstruct vital medical histories for refugees globally.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_Pipeline-7c3aed)](https://langchain-ai.github.io/langgraph/)
[![Gemma 4](https://img.shields.io/badge/Gemma_4-31B_Multimodal-4285F4?logo=google)](https://ai.google.dev/gemma)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Key Features](#key-features)
4. [System Architecture](#system-architecture)
5. [Tech Stack](#tech-stack)
6. [Project Structure](#project-structure)
7. [Installation & Setup](#installation--setup)
8. [Running the App](#running-the-app)
9. [API Reference](#api-reference)
10. [Supported Languages](#supported-languages)
11. [How the Pipeline Works](#how-the-pipeline-works)
12. [Sample Input](#sample-input)
13. [Configuration](#configuration)
14. [Disclaimer](#disclaimer)

---

## Overview

When refugees flee war, conflict, or disaster, they lose everything — including their medical history. Arriving in a host country with a half-empty blister pack, a crumpled handwritten prescription in Pashto, or a voice note in Ukrainian, patients and doctors face a dangerous information vacuum.

**MedBridge** solves this by reconstructing medical continuity. It uses the multimodal intelligence of **Google Gemma 4** to extract, translate, and structure fragmented medical evidence from any language or medium into a standardised, bilingual **Emergency Medical Passport** — serving both the host-country doctor (clinical data in English) and the patient (care instructions in their own native script).

---

## Problem Statement

| Challenge | Impact |
|---|---|
| Medical documents in foreign scripts (Arabic, Pashto, Cyrillic, Tigrinya…) | Host-country doctors cannot interpret prescriptions or diagnoses |
| Partial evidence — blurry medicine strips, torn packaging | Active ingredients and dosages are unknown |
| No medical history after displacement | Dangerous drug interactions or duplicate treatments |
| Language barrier at point of care | Patients cannot understand their own care instructions |
| 120M+ displaced people globally (UNHCR 2024) | Systemic, not isolated problem |

---

## Key Features

- **Multimodal Evidence Processing** — Accepts photos of medicine strips, handwritten prescriptions, typed notes, and voice note transcripts
- **60+ Language Support** — Full coverage across 7 regional groups including RTL scripts (Arabic, Pashto, Farsi, Kurdish), Cyrillic (Ukrainian, Russian), Sub-Saharan African languages (Tigrinya, Amharic, Somali, Swahili), Southeast Asian scripts (Burmese, Rohingya, Karen), and a custom tribal/indigenous language entry
- **AI-Powered Extraction** — Gemma 4 Vision reads heavily damaged and foreign-language pharmaceutical packaging with zero manual transcription
- **Clinical Standardisation** — Medication names normalised to English/Latin generic names (INN); dosages, frequencies, and routes preserved
- **Bilingual Emergency Medical Passport** — Downloadable PDF with:
  - Doctor section: structured English clinical data
  - Patient section: native-script care instructions in the patient's own language
- **Human-in-the-Loop Approval** — Critical safety gate: AI-generated passports require doctor verification before finalisation (LangGraph checkpoint)
- **Offline-Capable Database** — SQLite with WAL mode for high-concurrency in field deployments with intermittent connectivity
- **Graceful Tribal Language Fallback** — Falls back to closest regional trade language with a spoken-language note when a rare dialect has no digital resources

---

## System Architecture

The platform is structured in four layers: **Presentation**, **API/Service**, **Agentic AI Pipeline**, and **Persistence/Export**. Google Gemma 4 is the cognitive engine across every reasoning step.

![MedBridge System Architecture](https://mermaid.ink/img/Zmxvd2NoYXJ0IFRCCiAgICBzdWJncmFwaCBDbGllbnRbUHJlc2VudGF0aW9uIExheWVyXQogICAgICAgIFVJW0FscGluZS5qcyArIEppbmphMiBVSSAtIExvdy1iYW5kd2lkdGggUlRMLWF3YXJlXQogICAgICAgIFVwbG9hZFtNdWx0aS1ldmlkZW5jZSBVcGxvYWRlciAtIFBob3RvcyBQcmVzY3JpcHRpb25zIFZvaWNlIE5vdGVzXQogICAgICAgIFBhc3Nwb3J0W0JpbGluZ3VhbCBQYXNzcG9ydCBWaWV3ZXJdCiAgICBlbmQKICAgIHN1YmdyYXBoIEFQSVtBUEkgYW5kIFNlcnZpY2UgTGF5ZXIgRmFzdEFQSV0KICAgICAgICBSX1BhZ2VzW3JvdXRlcnMvcGFnZXMucHldCiAgICAgICAgUl9VcGxvYWRbcm91dGVycy91cGxvYWQucHldCiAgICAgICAgUl9QaXBlW3JvdXRlcnMvcGlwZWxpbmUucHldCiAgICAgICAgUl9QYXNzW3JvdXRlcnMvcGFzc3BvcnQucHldCiAgICAgICAgUl9FeHBvcnRbcm91dGVycy9leHBvcnQucHldCiAgICAgICAgU1ZDX0FJW3NlcnZpY2VzL2FpX3NlcnZpY2UucHkgLSBHZW1tYSA0IGNsaWVudF0KICAgICAgICBTVkNfRXhwW3NlcnZpY2VzL2V4cG9ydF9zZXJ2aWNlLnB5IC0gUmVwb3J0TGFiIFBERl0KICAgICAgICBMYW5nW3V0aWxzL2xhbmd1YWdlcy5weSAtIDYwKyBsYW5ndWFnZSByZWdpc3RyeV0KICAgIGVuZAogICAgc3ViZ3JhcGggQWdlbnRzW0FnZW50aWMgQUkgUGlwZWxpbmUgTGFuZ0dyYXBoXQogICAgICAgIE9yY2hbT3JjaGVzdHJhdG9yIC0gYWdlbnRzL2dyYXBoLnB5XQogICAgICAgIE4xW0V4dHJhY3Rpb24gTm9kZSAtIFZpc2lvbiArIE9DUl0KICAgICAgICBOMltNZWRpY2FsIFN0cnVjdHVyaW5nIE5vZGUgLSBDbGluaWNhbCB0ZXJtcyB0byBFbmdsaXNoL0xhdGluXQogICAgICAgIE4zW1Bhc3Nwb3J0IEdlbmVyYXRpb24gTm9kZSAtIE5hdGl2ZS1zY3JpcHQgcGF0aWVudCBzdW1tYXJ5XQogICAgICAgIEdlbW1he3tHb29nbGUgR2VtbWEgNCAtIE11bHRpbW9kYWwgYW5kIE11bHRpbGluZ3VhbH19CiAgICBlbmQKICAgIHN1YmdyYXBoIERhdGFbUGVyc2lzdGVuY2UgYW5kIEV4cG9ydF0KICAgICAgICBEQlsoU1FMaXRlIFdBTCAtIGRhdGEvbWVkYnJpZGdlLmRiKV0KICAgICAgICBGaWxlc1sodXBsb2Fkcy8gcmF3IGV2aWRlbmNlKV0KICAgICAgICBQREZbRW1lcmdlbmN5IE1lZGljYWwgUGFzc3BvcnQgLSBCaWxpbmd1YWwgUERGXQogICAgZW5kCiAgICBVSSAtLT4gUl9QYWdlcwogICAgVXBsb2FkIC0tPiBSX1VwbG9hZAogICAgVUkgLS0-IFJfUGlwZQogICAgVUkgLS0-IFJfUGFzcwogICAgVUkgLS0-IFJfRXhwb3J0CiAgICBSX1VwbG9hZCAtLT4gREIKICAgIFJfVXBsb2FkIC0tPiBGaWxlcwogICAgUl9VcGxvYWQgLS0-IExhbmcKICAgIFJfUGlwZSAtLT4gT3JjaAogICAgUl9QYXNzIC0tPiBEQgogICAgUl9FeHBvcnQgLS0-IFNWQ19FeHAKICAgIE9yY2ggLS0-IE4xIC0tPiBOMiAtLT4gTjMKICAgIE4xIC0tPiBTVkNfQUkKICAgIE4yIC0tPiBTVkNfQUkKICAgIE4zIC0tPiBTVkNfQUkKICAgIFNWQ19BSSA8LS0-IEdlbW1hCiAgICBOMyAtLT4gREIKICAgIExhbmcgLS0-IE4yCiAgICBMYW5nIC0tPiBOMwogICAgU1ZDX0V4cCAtLT4gREIKICAgIFNWQ19FeHAgLS0-IExhbmcKICAgIFNWQ19FeHAgLS0-IFBERgogICAgUERGIC0tPiBQYXNzcG9ydAogICAgY2xhc3NEZWYgZ2VtbWEgZmlsbDojNDI4NUY0LHN0cm9rZTojMWE3M2U4LGNvbG9yOiNmZmYsc3Ryb2tlLXdpZHRoOjJweAogICAgY2xhc3NEZWYgc3RvcmUgZmlsbDojZmVmM2M3LHN0cm9rZTojZDk3NzA2LGNvbG9yOiM3ODM1MGYKICAgIGNsYXNzRGVmIGFnZW50IGZpbGw6I2RkZDZmZSxzdHJva2U6IzdjM2FlZCxjb2xvcjojM2IwNzY0CiAgICBjbGFzcyBHZW1tYSBnZW1tYQogICAgY2xhc3MgREIsRmlsZXMsUERGIHN0b3JlCiAgICBjbGFzcyBOMSxOMixOMyxPcmNoIGFnZW50?bgColor=white)

### Pipeline State Machine (LangGraph nodes)

```
START
  │
  ▼
[1] multimodal_extraction_node      ← Gemma 4 Vision reads all uploaded evidence
  │
  ▼
[2] medical_structuring_node        ← Normalises to clinical English/Latin; preserves native script
  │
  ▼
[3] timeline_builder_node           ← Reconstructs chronological medical history
  │
  ▼
[4] risk_assessment_node            ← Flags allergies, dangerous interactions, missing data
  │
  ▼
[5] verification_checklist_node     ← Produces confidence scores per data field
  │
  ▼
[6] human_approval_node             ← ⚠️ REQUIRED: doctor must verify before export
  │
  ▼
[7] passport_generation_node        ← Generates bilingual JSON + patient-facing native instructions
  │
  ▼
END → PDF Export
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| AI Model | **Google Gemma 4** (`gemma-4-31b-it`) | Multimodal extraction, multilingual reasoning, structured generation |
| Agent Routing | **Google ADK** (`gemini-2.0-flash-exp`) | Fast tool-calling orchestration |
| Workflow | **LangGraph** | Stateful agent pipeline with human-in-the-loop checkpoint |
| Web Framework | **FastAPI 0.115.0** | REST API + HTML page serving |
| Server | **Uvicorn 0.30.6** | ASGI server with auto-reload |
| Database | **SQLite (WAL mode)** | Offline-capable, high-concurrency field storage |
| Templating | **Jinja2 + Alpine.js** | Server-rendered HTML; lightweight reactive UI |
| PDF Export | **ReportLab 4.2.0** | Bilingual Emergency Medical Passport generation |
| Validation | **Pydantic v2** | Schema validation for all API payloads |
| Image Handling | **Pillow** | Pre-processing uploaded evidence images |
| QR Code | **qrcode[pil]** | Passport QR linking to digital record |

---

## Project Structure

```
MedBridge_Ukraine/
│
├── main.py                        # FastAPI app entry point, router registration
├── requirements.txt               # All Python dependencies
│
├── agents/                        # Agentic AI pipeline (LangGraph)
│   ├── config.py                  # Model config: GEMMA_MODEL, AGENT_MODEL
│   ├── events.py                  # SSE event bus for real-time pipeline progress
│   ├── graph.py                   # LangGraph StateGraph — 7-node pipeline
│   ├── orchestrator.py            # Pipeline entry point called by router
│   ├── specialists.py             # Google ADK specialist agent definitions
│   └── tools.py                   # Gemma 4 API wrappers + DB read/write tools
│
├── database/
│   └── init_db.py                 # SQLite schema + idempotent migrations
│
├── models/
│   └── schemas.py                 # Pydantic v2 schemas (PatientCreate, PassportResponse…)
│
├── routers/
│   ├── export.py                  # GET /api/export/{patient_id} → PDF
│   ├── pages.py                   # HTML page routes (/, /upload, /pipeline, /passport)
│   ├── passport.py                # GET /api/passport/{patient_id}
│   ├── pipeline.py                # POST /api/pipeline/run/{patient_id}
│   └── upload.py                  # POST /api/upload/patient, POST /api/upload/evidence
│
├── services/
│   ├── ai_service.py              # Gemma 4 GenAI SDK client + prompt helpers
│   └── export_service.py          # ReportLab PDF builder (bilingual)
│
├── utils/
│   └── languages.py               # 60+ language registry: codes, RTL flags, native names
│
├── templates/                     # Jinja2 HTML templates
│   ├── base.html                  # Shared navbar, footer, CSS/JS includes
│   ├── index.html                 # Home page + feature overview
│   ├── upload.html                # Patient intake + evidence uploader (Alpine.js)
│   ├── pipeline.html              # Real-time pipeline progress (SSE)
│   ├── passport.html              # Passport viewer + download
│   └── verify.html                # Doctor verification / human-approval page
│
├── static/
│   ├── css/main.css               # Full design system
│   └── js/
│       ├── app.js                 # Shared utilities
│       ├── pipeline.js            # SSE event listener + progress rendering
│       └── upload.js              # Multi-step intake form (Alpine.js)
│
├── data/                          # SQLite database (auto-created on first run)
├── uploads/                       # Uploaded evidence files (one folder per patient UUID)
├── sample_inputs/
│   └── voice_note_01.txt          # Sample Ukrainian voice note transcript for testing
└── docs/
    └── architecture.png           # Rendered architecture diagram (PNG)
```

---

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- A **Google AI Studio API key** with access to `gemma-4-31b-it`
  ([Get one free at ai.google.dev](https://ai.google.dev))

### 1. Clone the repository

```bash
git clone https://github.com/your-username/medbridge.git
cd medbridge
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** If `Pillow==10.3.0` fails on your Python version, install unpinned: `pip install Pillow`

### 4. Create environment file

Create a `.env` file in the project root:

```env
# Required: Google AI Studio API key
GOOGLE_API_KEY=your_google_api_key_here

# Optional overrides (defaults shown)
GEMMA_MODEL=gemma-4-31b-it
AGENT_MODEL=gemini-2.0-flash-exp
UPLOAD_DIR=./uploads
DATABASE_URL=./data/medbridge.db
```

---

## Running the App

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser at **http://127.0.0.1:8000**

Interactive API docs are available at **http://127.0.0.1:8000/api/docs**

---

## API Reference

### Patient Registration

```http
POST /api/upload/patient
Content-Type: application/json

{
  "name": "Olena Kovalenko",
  "age": 46,
  "language": "uk",
  "language_other": null
}
```

**Response `201`:**
```json
{
  "patient_id": "uuid-v4",
  "name": "Olena Kovalenko",
  "language": "uk",
  "created_at": "2026-05-18T10:00:00Z"
}
```

---

### Upload Evidence

```http
POST /api/upload/evidence/{patient_id}
Content-Type: multipart/form-data

file: <image or text file>
evidence_type: "prescription" | "medicine_strip" | "voice_note" | "other"
```

---

### Run AI Pipeline

```http
POST /api/pipeline/run/{patient_id}
```

Starts the 7-node LangGraph pipeline asynchronously. Subscribe to SSE events at `/api/pipeline/events/{patient_id}` for real-time progress.

---

### Get Passport

```http
GET /api/passport/{patient_id}
```

Returns the full structured passport JSON once the pipeline completes and the doctor approves.

---

### Export PDF

```http
GET /api/export/{patient_id}
```

Returns a downloadable bilingual PDF — clinical data in English for the doctor, native-script patient instructions.

---

### Health Check

```http
GET /api/health
```

```json
{ "status": "ok", "version": "1.0.0" }
```

---

## Supported Languages

Languages are grouped by region in `utils/languages.py`. Over 60 languages are supported.

| Region | Languages |
|---|---|
| 🇪🇺 Ukraine / Eastern Europe | Ukrainian, Russian, Polish, Romanian, Hungarian, Czech, Slovak |
| 🌙 Middle East / North Africa | Arabic (MSA), Levantine Arabic, Iraqi Arabic, Darija, Farsi/Persian, Pashto/Dari, Kurdish (Kurmanji), Kurdish (Sorani), Tigrinya, Somali |
| 🌿 Central / South Asia | Hindi, Urdu, Bengali, Nepali, Sinhala |
| 🌍 Sub-Saharan Africa | Amharic, Swahili, Hausa, Oromo, Tigrinya (Eritrea), Dinka, Nuer, French (African) |
| 🌏 Southeast Asia | Burmese, Rohingya, Karen (S'gaw), Thai, Vietnamese, Tagalog, Khmer, Indonesian |
| 🌎 Latin America | Spanish, Haitian Creole, Portuguese (BR) |
| 🏠 Host-country Languages | English, German, French, Dutch, Italian, Spanish (EU), Swedish, Norwegian |
| ✍️ Custom / Tribal | Any language — free text input (e.g. Wolof, Bambara, Mam, Hmong, Mixteco) |

For RTL languages (Arabic, Pashto, Farsi, Kurdish, Tigrinya), the AI is instructed to output native-script summaries with correct RTL directionality.

---

## How the Pipeline Works

### Step-by-step walkthrough

**1. Intake (`POST /api/upload/patient`)**
The aid worker or patient registers using the web form, selects their language from a grouped dropdown (or enters a custom tribal language name), and uploads one or more evidence files.

**2. Extraction Node**
Gemma 4's vision model is called for each uploaded file. It reads medicine strips, torn prescriptions, and handwritten notes even under poor image conditions. For voice note transcripts, it extracts both the `transcription` (in native script) and an `transcription_english` version.

**3. Medical Structuring Node**
The extracted raw data is normalised:
- Medication brand names → INN generic names (English/Latin)
- Dosage values, frequencies, and routes standardised
- `name_native` field preserved alongside English for patient recognition
- Language context (RTL, display name, script type) injected from `utils/languages.py`

**4. Timeline Builder Node**
All dated medical events (hospitalisations, prescription changes, diagnoses) are sorted chronologically and gaps flagged.

**5. Risk Assessment Node**
Gemma 4 scans for:
- Known drug allergies (cross-referenced with current medications)
- Dangerous drug interactions
- Incomplete or contradictory dosage information
- Missing follow-up care

**6. Human Approval Node (⚠️ Safety Gate)**
The pipeline **pauses**. A verification checklist is shown to the reviewing clinician at `/verify`. The doctor must explicitly approve the structured data before the passport is generated. This is enforced by LangGraph's `interrupt` mechanism and cannot be bypassed.

**7. Passport Generation Node**
Gemma 4 generates:
- A structured JSON passport with all clinical fields in English
- A `multilingual_summary` section with the summary translated into the patient's native language
- A `patient_facing_instructions` field written entirely in the patient's script (e.g., Arabic, Devanagari, Cyrillic)
- A `language_notes` field for tribal languages explaining the fallback used

**8. PDF Export**
ReportLab composes the bilingual PDF with two clearly separated sections — the medical summary for the doctor, and the care instructions for the patient.

---

## Sample Input

The file `sample_inputs/voice_note_01.txt` contains a real-world test case: a Ukrainian patient's voice note transcription covering:
- Type 2 Diabetes (Metformin 1000mg twice daily)
- Hypertension (Lisinopril 20mg, Amlodipine 10mg)
- Penicillin allergy (urticaria + angioedema)
- July 2024 hospitalisation in Kharkiv for hypertensive crisis
- Possible Atorvastatin (dose unknown)

This demonstrates how MedBridge handles mixed-language input, partial information, and critical allergy flagging.

---

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `GOOGLE_API_KEY` | *(required)* | Google AI Studio key for Gemma 4 access |
| `GEMMA_MODEL` | `gemma-4-31b-it` | Gemma model for all clinical reasoning |
| `AGENT_MODEL` | `gemini-2.0-flash-exp` | Fast Gemini model for ADK tool routing |
| `UPLOAD_DIR` | `./uploads` | Directory for patient evidence files |
| `GOOGLE_GENAI_USE_VERTEXAI` | `FALSE` | Set `TRUE` to use Vertex AI instead of AI Studio |

---

## Disclaimer

> **MedBridge is a decision-support tool only.** It does not make medical decisions, prescribe medications, or replace clinical judgment. All AI-generated outputs must be reviewed and approved by a qualified healthcare professional before being used in patient care. The Human Approval checkpoint is a mandatory part of the pipeline and cannot be skipped.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built for the Google Gemma 4 Good Hackathon · May 2026*

"""Pydantic schemas for MedBridge Ukraine."""

from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    language: str = Field(default="uk")
    # Free-text language label used when `language == "custom"` — for
    # tribal, indigenous, or otherwise unlisted refugee languages.
    language_other: Optional[str] = Field(default=None, max_length=120)
    age: Optional[int] = Field(default=None, ge=0, le=150)
    additional_notes: Optional[str] = None


class PatientResponse(BaseModel):
    id: str
    name: str
    language: str
    language_other: Optional[str] = None
    age: Optional[int]
    additional_notes: Optional[str]
    created_at: str


class EvidenceFileResponse(BaseModel):
    id: str
    patient_id: str
    original_name: str
    file_type: str
    evidence_category: str
    created_at: str


class PipelineRunCreate(BaseModel):
    patient_id: str


class PipelineRunResponse(BaseModel):
    id: str
    patient_id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None


class PassportResponse(BaseModel):
    run_id: str
    patient_id: str
    status: str
    passport_data: Optional[dict[str, Any]] = None
    verification_checklist: Optional[dict[str, Any]] = None
    risk_report: Optional[dict[str, Any]] = None
    timeline_data: Optional[dict[str, Any]] = None
    structured_data: Optional[dict[str, Any]] = None


class VerificationUpdate(BaseModel):
    doctor_name: Optional[str] = None
    verification_data: Optional[dict[str, Any]] = None
    overall_status: str = Field(default="pending")
    notes: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str = "1.0.0"
    model: str

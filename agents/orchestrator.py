"""
MedBridge Ukraine — Pipeline Orchestrator

Orchestration uses TWO complementary frameworks (as specified in MedBridge_Ukraine.docx):

  1. LangGraph StateGraph  — workflow state machine, state management, and
                             the Human Approval Node (critical innovation point).
     MedBridgeState tracks all 7 pipeline fields from the architecture doc.

  2. Google ADK LlmAgent   — specialist agent definitions (multimodal_agent,
                             structuring_agent, etc.) are kept in specialists.py
                             for agent-framework demonstration.

The active runtime execution uses the LangGraph graph (agents/graph.py).
ADK's SequentialAgent is retained for structural reference.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

# ── LangGraph — primary runtime orchestrator ──────────────────────────
from agents.graph import MEDBRIDGE_GRAPH, MedBridgeState

# ── Google ADK — specialist agent definitions ─────────────────────────
from google.adk.agents import SequentialAgent

from agents.events import bus
from agents.specialists import (
    multimodal_agent,
    structuring_agent,
    timeline_agent,
    risk_agent,
    verification_agent,
    passport_agent,
)


# ── ADK pipeline (kept for agent-framework reference) ─────────────────

MEDBRIDGE_PIPELINE = SequentialAgent(
    name="MedBridgePipeline",
    description=(
        "Google ADK SequentialAgent definition for the 6-specialist MedBridge pipeline. "
        "Runtime execution is managed by LangGraph StateGraph (see agents/graph.py)."
    ),
    sub_agents=[
        multimodal_agent,
        structuring_agent,
        timeline_agent,
        risk_agent,
        verification_agent,
        passport_agent,
    ],
)



# ── Public entry point ────────────────────────────────────────────────

async def run_pipeline(
    *,
    patient_id: str,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute the MedBridge pipeline via LangGraph StateGraph.

    Architecture (per MedBridge_Ukraine.docx Sections 9 & 13):
      LangGraph StateGraph manages the MedBridgeState workflow:
        collect_inputs → multimodal_analysis → medical_structuring
        → timeline_reconstruction → risk_analysis → verification_prep
        → human_approval [conditional] → passport_generation → END

      Google ADK LlmAgent specialists are defined in agents/specialists.py
      and exposed here via MEDBRIDGE_PIPELINE (SequentialAgent) for
      agent-framework demonstration.

    Args:
        patient_id: UUID of the patient to process.
        run_id: Pipeline run UUID (auto-generated if None).

    Returns:
        Dict with run_id, status, and final_summary (passport).
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    bus.publish(run_id, {
        "type": "pipeline_start",
        "run_id": run_id,
        "patient_id": patient_id,
        "total_steps": 8,
        "framework": "LangGraph StateGraph + Google ADK LlmAgents",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # ── Build initial LangGraph state (MedBridgeState fields) ─────────
    initial_state: MedBridgeState = {
        "patient_id": patient_id,
        "run_id": run_id,
        "raw_inputs": {},
        "multimodal_understanding": {},
        "structured_medical_data": {},
        "timeline_data": {},
        "confidence_scores": {},
        "verification_checklist": {},
        "verification_status": "pending",
        "final_summary": {},
        "errors": [],
        "current_step": 0,
    }

    try:
        # ── Run LangGraph graph in thread pool ─────────────────────────
        # (graph nodes are sync; bus.publish is thread-safe via call_soon_threadsafe)
        loop = asyncio.get_event_loop()
        final_state: MedBridgeState = await loop.run_in_executor(
            None,
            lambda: MEDBRIDGE_GRAPH.invoke(initial_state),
        )

        bus.publish(run_id, {
            "type": "pipeline_done",
            "run_id": run_id,
            "status": "completed",
            "verification_status": final_state.get("verification_status", "pending"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    except Exception as exc:
        bus.publish(run_id, {
            "type": "pipeline_error",
            "run_id": run_id,
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        bus.mark_done(run_id)
        return {"run_id": run_id, "status": "error", "error": str(exc)}

    bus.mark_done(run_id)
    return {
        "run_id": run_id,
        "status": "completed",
        "patient_id": patient_id,
    }

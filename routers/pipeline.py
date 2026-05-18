"""
Pipeline router — start the 6-agent pipeline and stream progress via SSE.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from agents.events import bus
from agents.orchestrator import run_pipeline
from database.init_db import db_conn

router = APIRouter()


async def _start_pipeline_task(patient_id: str, run_id: str) -> None:
    """Background task that executes the full pipeline."""
    try:
        await run_pipeline(patient_id=patient_id, run_id=run_id)
        # Safety: ensure status is set to completed even if save_passport wasn't called
        with db_conn() as conn:
            run_status = conn.execute(
                "SELECT status FROM pipeline_runs WHERE id=?", (run_id,)
            ).fetchone()
            if run_status and run_status["status"] == "running":
                conn.execute(
                    "UPDATE pipeline_runs SET status='completed', completed_at=? WHERE id=?",
                    (datetime.now(timezone.utc).isoformat(), run_id),
                )
    except Exception as exc:
        bus.publish(run_id, {
            "type": "pipeline_error",
            "run_id": run_id,
            "error": str(exc),
        })
        bus.mark_done(run_id)
        # Update DB status
        try:
            with db_conn() as conn:
                conn.execute(
                    "UPDATE pipeline_runs SET status='failed' WHERE id=?", (run_id,)
                )
        except Exception:
            pass


@router.post("/run/{patient_id}")
async def start_pipeline(patient_id: str, background_tasks: BackgroundTasks):
    """Start the 6-agent MedBridge pipeline for a patient.
    
    Returns immediately with a run_id. Use GET /stream/{run_id} for SSE progress.
    """
    # Verify patient exists and has files
    with db_conn() as conn:
        patient = conn.execute(
            "SELECT id, name FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        file_count = conn.execute(
            "SELECT COUNT(*) FROM evidence_files WHERE patient_id = ?", (patient_id,)
        ).fetchone()[0]

    if file_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No evidence files found. Please upload at least one medical document."
        )

    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with db_conn() as conn:
        conn.execute(
            "INSERT INTO pipeline_runs (id, patient_id, status, created_at) VALUES (?, ?, 'running', ?)",
            (run_id, patient_id, now),
        )

    background_tasks.add_task(_start_pipeline_task, patient_id, run_id)

    return {
        "run_id": run_id,
        "patient_id": patient_id,
        "patient_name": patient["name"],
        "status": "running",
        "file_count": file_count,
        "stream_url": f"/api/pipeline/stream/{run_id}",
        "started_at": now,
    }


@router.get("/stream/{run_id}")
async def stream_pipeline(run_id: str):
    """SSE endpoint — streams real-time agent progress events."""

    async def event_generator():
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'run_id': run_id})}\n\n"

        async for event in bus.consume(run_id):
            yield f"data: {json.dumps(event, default=str)}\n\n"
            await asyncio.sleep(0)  # Yield control

        yield f"data: {json.dumps({'type': 'stream_end', 'run_id': run_id})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/status/{run_id}")
async def get_pipeline_status(run_id: str):
    """Get the current status of a pipeline run."""
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id, patient_id, status, created_at, completed_at "
            "FROM pipeline_runs WHERE id = ?",
            (run_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    return dict(row)


@router.get("/runs/{patient_id}")
async def list_patient_runs(patient_id: str):
    """List all pipeline runs for a patient."""
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id, status, created_at, completed_at FROM pipeline_runs "
            "WHERE patient_id = ? ORDER BY created_at DESC LIMIT 10",
            (patient_id,),
        ).fetchall()
    return {"patient_id": patient_id, "runs": [dict(r) for r in rows]}


# ── Aliases used by the frontend ──────────────────────────────────────

@router.post("/start")
async def start_pipeline_by_run_id(payload: dict, background_tasks: BackgroundTasks):
    """
    Start the pipeline for a pre-allocated run_id (created during upload).
    Body: { "run_id": "<uuid>" }
    """
    run_id = payload.get("run_id")
    if not run_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="run_id is required")

    with db_conn() as conn:
        run = conn.execute(
            "SELECT pr.id, pr.patient_id, pr.status, p.name as patient_name "
            "FROM pipeline_runs pr JOIN patients p ON pr.patient_id = p.id "
            "WHERE pr.id = ?",
            (run_id,),
        ).fetchone()

    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Run not found. Upload files first.")

    if run["status"] == "running":
        return {"run_id": run_id, "status": "already_running",
                "stream_url": f"/api/pipeline/{run_id}/stream"}

    if run["status"] == "completed":
        return {"run_id": run_id, "status": "completed",
                "passport_url": f"/passport/{run_id}"}

    # Mark running
    with db_conn() as conn:
        conn.execute(
            "UPDATE pipeline_runs SET status='running' WHERE id=?", (run_id,)
        )

    background_tasks.add_task(_start_pipeline_task, run["patient_id"], run_id)

    return {
        "run_id": run_id,
        "patient_id": run["patient_id"],
        "patient_name": run["patient_name"],
        "status": "running",
        "stream_url": f"/api/pipeline/{run_id}/stream",
    }


@router.get("/{run_id}/stream")
async def stream_pipeline_alias(run_id: str):
    """SSE stream alias — frontend uses /api/pipeline/{run_id}/stream."""
    return await stream_pipeline(run_id)


@router.get("/{run_id}/status")
async def get_pipeline_status_alias(run_id: str):
    """Status alias — frontend uses /api/pipeline/{run_id}/status."""
    return await get_pipeline_status(run_id)

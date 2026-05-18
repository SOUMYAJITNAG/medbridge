"""
Page router — serves the HTML frontend pages via Jinja2 templates.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from utils.languages import grouped_for_ui

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "language_groups": grouped_for_ui()},
    )


@router.get("/pipeline/{run_id}", response_class=HTMLResponse)
async def pipeline_page(request: Request, run_id: str):
    return templates.TemplateResponse("pipeline.html", {"request": request, "run_id": run_id})


@router.get("/passport/{run_id}", response_class=HTMLResponse)
async def passport_page(request: Request, run_id: str):
    return templates.TemplateResponse("passport.html", {"request": request, "run_id": run_id})


@router.get("/verify/{run_id}", response_class=HTMLResponse)
async def verify_page(request: Request, run_id: str):
    return templates.TemplateResponse("verify.html", {"request": request, "run_id": run_id})

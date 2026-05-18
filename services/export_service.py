"""
Export service — PDF and QR code generation for Emergency Medical Passport.
"""

from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any

import qrcode
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
)

from utils.languages import language_name


# ── Color constants ────────────────────────────────────────────────────

UKRAINE_BLUE = colors.HexColor("#0057B7")
UKRAINE_YELLOW = colors.HexColor("#FFD700")
DARK_BG = colors.HexColor("#1A2035")
LIGHT_GRAY = colors.HexColor("#F0F4F8")
DANGER_RED = colors.HexColor("#DC2626")
WARNING_AMBER = colors.HexColor("#D97706")
SUCCESS_GREEN = colors.HexColor("#059669")
TEXT_DARK = colors.HexColor("#1E293B")
TEXT_MUTED = colors.HexColor("#64748B")


def generate_passport_pdf(
    passport_data: dict[str, Any],
    patient_name: str,
    run_id: str,
    risk_report: dict[str, Any] | None = None,
) -> bytes:
    """Generate a professional PDF Emergency Medical Passport."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Header ────────────────────────────────────────────────────────
    header_style = ParagraphStyle(
        "header",
        parent=styles["Normal"],
        fontSize=20,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=2 * mm,
    )
    sub_header_style = ParagraphStyle(
        "subheader",
        parent=styles["Normal"],
        fontSize=11,
        fontName="Helvetica",
        textColor=colors.HexColor("#CBD5E1"),
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    )

    # Header banner (table-based for color)
    header_data = [[
        Paragraph("🏥 MEDBRIDGE UKRAINE", header_style),
    ]]
    sub_data = [[
        Paragraph("Emergency Medical Passport — AI-Assisted Reconstruction", sub_header_style),
    ]]

    header_table = Table([[Paragraph("🏥 MEDBRIDGE UKRAINE", header_style)]], colWidths=[180 * mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), UKRAINE_BLUE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(header_table)

    sub_table = Table([[Paragraph("Emergency Medical Passport — AI-Assisted Reconstruction", sub_header_style)]], colWidths=[180 * mm])
    sub_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BG),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(sub_table)
    story.append(Spacer(1, 5 * mm))

    # ── Disclaimer banner ──────────────────────────────────────────────
    disclaimer_style = ParagraphStyle(
        "disclaimer",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica-BoldOblique",
        textColor=DANGER_RED,
        alignment=TA_CENTER,
    )
    disclaimer_table = Table([[
        Paragraph(
            "⚠️  AI-ASSISTED RECONSTRUCTION — ALL DATA REQUIRES CLINICIAN VERIFICATION BEFORE TREATMENT DECISIONS  ⚠️",
            disclaimer_style
        )
    ]], colWidths=[180 * mm])
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
        ("BOX", (0, 0), (-1, -1), 1, WARNING_AMBER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(disclaimer_table)
    story.append(Spacer(1, 5 * mm))

    # ── Patient Info ───────────────────────────────────────────────────
    section_title_style = ParagraphStyle(
        "section_title",
        parent=styles["Normal"],
        fontSize=12,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        spaceAfter=3 * mm,
    )
    field_label = ParagraphStyle(
        "field_label",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=TEXT_MUTED,
    )
    field_value = ParagraphStyle(
        "field_value",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica",
        textColor=TEXT_DARK,
    )

    patient_info = passport_data.get("patient", {})
    confidence_data = passport_data.get("data_confidence", {})
    score = confidence_data.get("overall_score", 0)
    grade = confidence_data.get("grade", "?")
    score_color = SUCCESS_GREEN if score >= 0.7 else (WARNING_AMBER if score >= 0.4 else DANGER_RED)

    patient_rows = [
        [
            _label_val("Patient Name", patient_info.get("name", patient_name), styles),
            _label_val("Age", str(patient_info.get("age", "Unknown")), styles),
            _label_val("Language", patient_info.get("language", "Unknown"), styles),
        ],
        [
            _label_val("Passport ID", run_id[:16], styles),
            _label_val("Generated", datetime.now().strftime("%Y-%m-%d %H:%M UTC"), styles),
            _label_val("Confidence", f"{int(score * 100)}% (Grade {grade})", styles),
        ],
    ]
    pt = Table(patient_rows, colWidths=[60 * mm, 60 * mm, 60 * mm])
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(_section_header("PATIENT INFORMATION", styles))
    story.append(pt)
    story.append(Spacer(1, 5 * mm))

    # ── Critical Allergies ─────────────────────────────────────────────
    allergies = passport_data.get("critical_allergies", [])
    story.append(_section_header("⚠️  CRITICAL ALLERGIES", styles, bg=DANGER_RED))

    if allergies:
        allergy_rows = [[
            Paragraph("Substance", _bold_style(styles)),
            Paragraph("Reaction", _bold_style(styles)),
            Paragraph("Severity", _bold_style(styles)),
        ]]
        for a in allergies:
            allergy_rows.append([
                Paragraph(str(a.get("substance", "-")), _normal_style(styles)),
                Paragraph(str(a.get("reaction", a.get("reaction_type", "-"))), _normal_style(styles)),
                Paragraph(str(a.get("severity", "-")).upper(), _normal_style(styles)),
            ])
        at = Table(allergy_rows, colWidths=[70 * mm, 70 * mm, 40 * mm])
        at.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FEE2E2")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFF5F5")),
            ("BOX", (0, 0), (-1, -1), 1, DANGER_RED),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FECACA")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(at)
    else:
        story.append(Paragraph("No allergies recorded (verify with patient)", _italic_style(styles)))

    story.append(Spacer(1, 5 * mm))

    # ── Current Medications ────────────────────────────────────────────
    medications = passport_data.get("current_medications", [])
    story.append(_section_header("💊  CURRENT MEDICATIONS", styles, bg=UKRAINE_BLUE))

    if medications:
        med_rows = [[
            Paragraph("Medication", _bold_style(styles)),
            Paragraph("Dosage", _bold_style(styles)),
            Paragraph("Frequency", _bold_style(styles)),
            Paragraph("Confidence", _bold_style(styles)),
        ]]
        for m in medications:
            med_rows.append([
                Paragraph(str(m.get("name", "-")), _normal_style(styles)),
                Paragraph(str(m.get("dosage", "-")), _normal_style(styles)),
                Paragraph(str(m.get("frequency", "-")), _normal_style(styles)),
                Paragraph(_confidence_label(m.get("confidence", m.get("confidence_note", ""))), _normal_style(styles)),
            ])
        mt = Table(med_rows, colWidths=[55 * mm, 40 * mm, 45 * mm, 40 * mm])
        mt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DBEAFE")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#93C5FD")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(mt)
    else:
        story.append(Paragraph("No medications recorded", _italic_style(styles)))

    story.append(Spacer(1, 5 * mm))

    # ── Chronic Conditions ─────────────────────────────────────────────
    conditions = passport_data.get("chronic_conditions", [])
    story.append(_section_header("🏥  CHRONIC CONDITIONS", styles, bg=colors.HexColor("#7C3AED")))

    if conditions:
        cond_text = ", ".join([c.get("condition", str(c)) if isinstance(c, dict) else str(c) for c in conditions])
        story.append(Paragraph(cond_text, _normal_style(styles)))
    else:
        story.append(Paragraph("No chronic conditions recorded", _italic_style(styles)))

    story.append(Spacer(1, 5 * mm))

    # ── Timeline Summary ───────────────────────────────────────────────
    timeline_summary = passport_data.get("medical_timeline_summary", "")
    if timeline_summary:
        story.append(_section_header("📅  MEDICAL HISTORY SUMMARY", styles, bg=colors.HexColor("#0891B2")))
        story.append(Paragraph(str(timeline_summary), _normal_style(styles)))
        story.append(Spacer(1, 5 * mm))

    # ── Multilingual Summary ───────────────────────────────────────────
    ml_summary = passport_data.get("multilingual_summary", {})
    if ml_summary:
        story.append(_section_header("🌍  MULTILINGUAL EMERGENCY SUMMARY", styles, bg=colors.HexColor("#065F46")))
        for lang_code, text in ml_summary.items():
            # Resolve through the central language registry so the PDF can
            # show friendly names for ANY supported refugee language, not
            # just the original 6 hard-coded ones.
            lang_label = language_name(lang_code) or lang_code.upper()
            story.append(Paragraph(f"<b>{lang_label}:</b> {text}", _normal_style(styles)))
            story.append(Spacer(1, 2 * mm))
        story.append(Spacer(1, 3 * mm))

    # ── Patient-facing instructions (in the patient's own language) ────
    patient_instructions = passport_data.get("patient_facing_instructions")
    if patient_instructions:
        story.append(_section_header("🗣️  PATIENT-FACING INSTRUCTIONS", styles, bg=colors.HexColor("#9333EA")))
        story.append(Paragraph(str(patient_instructions), _normal_style(styles)))
        story.append(Spacer(1, 5 * mm))

    # ── Footer ─────────────────────────────────────────────────────────
    footer_text = (
        "This Emergency Medical Passport was generated by MedBridge Ukraine AI platform. "
        "Data reconstructed from fragmented evidence. ALWAYS verify with patient. "
        f"Passport ID: {run_id} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
    )
    footer_style = ParagraphStyle(
        "footer", parent=styles["Normal"],
        fontSize=7, fontName="Helvetica-Oblique",
        textColor=TEXT_MUTED, alignment=TA_CENTER,
    )
    story.append(HRFlowable(width="100%", thickness=0.5, color=TEXT_MUTED))
    story.append(Paragraph(footer_text, footer_style))

    doc.build(story)
    return buf.getvalue()


def _section_header(title: str, styles, bg=UKRAINE_BLUE) -> Table:
    style = ParagraphStyle(
        "sh", parent=styles["Normal"],
        fontSize=10, fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    t = Table([[Paragraph(title, style)]], colWidths=[180 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def _label_val(label: str, value: str, styles) -> Table:
    ls = ParagraphStyle("lbl", parent=styles["Normal"], fontSize=8,
                        fontName="Helvetica-Bold", textColor=TEXT_MUTED)
    vs = ParagraphStyle("val", parent=styles["Normal"], fontSize=10,
                        fontName="Helvetica", textColor=TEXT_DARK)
    return Table([[Paragraph(label, ls)], [Paragraph(value or "-", vs)]])


def _bold_style(styles) -> ParagraphStyle:
    return ParagraphStyle("bs", parent=styles["Normal"], fontSize=9,
                          fontName="Helvetica-Bold", textColor=TEXT_DARK)


def _normal_style(styles) -> ParagraphStyle:
    return ParagraphStyle("ns", parent=styles["Normal"], fontSize=9,
                          fontName="Helvetica", textColor=TEXT_DARK)


def _italic_style(styles) -> ParagraphStyle:
    return ParagraphStyle("is", parent=styles["Normal"], fontSize=9,
                          fontName="Helvetica-Oblique", textColor=TEXT_MUTED)


def _confidence_label(value) -> str:
    if isinstance(value, (int, float)):
        pct = int(value * 100) if value <= 1 else int(value)
        if pct >= 80:
            return f"High ({pct}%)"
        elif pct >= 50:
            return f"Medium ({pct}%)"
        return f"Low ({pct}%)"
    return str(value) if value else "Unknown"


def generate_qr_code(data: str) -> bytes:
    """Generate a QR code PNG from the given data string."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color="#0057B7",   # Ukrainian blue
        back_color="white",
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

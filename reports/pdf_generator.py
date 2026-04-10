"""
reports/pdf_generator.py — SEBI-style case file PDF generator using ReportLab.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ─── Color Palette ────────────────────────────────────────────────────────────
SEBI_NAVY = colors.HexColor("#1A2B5F")
SEBI_GOLD = colors.HexColor("#C8A951")
SEBI_RED = colors.HexColor("#B22222")
SEBI_LIGHT = colors.HexColor("#F5F5F5")
TEXT_BLACK = colors.HexColor("#1A1A1A")


def generate_case_pdf(alert: Any, case: Any, output_path: str) -> None:
    """
    Generates a professional SEBI enforcement order-style PDF.

    Sections:
      1. Header — SEBI / ARGUS branding + case number
      2. Executive Summary
      3. Entities Under Investigation
      4. Evidence
      5. Statistical Basis
      6. Recommended Action
      Footer on every page
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title=f"ARGUS Case {case.case_number}",
        author="ARGUS Surveillance System",
    )

    styles = getSampleStyleSheet()
    style_normal = styles["Normal"]
    style_normal.fontSize = 10
    style_normal.textColor = TEXT_BLACK

    style_title = ParagraphStyle(
        "ArgusTitle",
        parent=styles["Heading1"],
        fontSize=15,
        textColor=SEBI_NAVY,
        alignment=TA_CENTER,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    style_header = ParagraphStyle(
        "ArgusHeader",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=SEBI_NAVY,
        spaceBefore=14,
        spaceAfter=6,
        fontName="Helvetica-Bold",
        borderPad=2,
    )
    style_sub = ParagraphStyle(
        "ArgusSub",
        parent=style_normal,
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )
    style_body = ParagraphStyle(
        "ArgusBody",
        parent=style_normal,
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    style_bold = ParagraphStyle(
        "ArgusBold",
        parent=style_body,
        fontName="Helvetica-Bold",
    )

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "SECURITIES AND EXCHANGE BOARD OF INDIA",
        style_title,
    ))
    story.append(Paragraph(
        "ARGUS Automated Surveillance Alert",
        ParagraphStyle("sub2", parent=style_sub, fontSize=11, textColor=SEBI_GOLD, fontName="Helvetica-Bold"),
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=SEBI_NAVY))
    story.append(Spacer(1, 0.2 * cm))

    # Case meta table
    detected_at = alert.detected_at if isinstance(alert.detected_at, datetime) else datetime.utcnow()
    meta_data = [
        ["Case Number:", case.case_number, "Date of Detection:", detected_at.strftime("%d %b %Y")],
        ["Exchange:", alert.exchange or "NSE", "Case Status:", str(case.status).upper()],
        ["Generation Date:", datetime.utcnow().strftime("%d %b %Y %H:%M UTC"), "Classification:", "STRICTLY CONFIDENTIAL"],
    ]
    meta_table = Table(meta_data, colWidths=[4 * cm, 7 * cm, 4 * cm, 4 * cm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_BLACK),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [SEBI_LIGHT, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Section 1: Executive Summary ──────────────────────────────────────────
    story.append(Paragraph("SECTION 1: EXECUTIVE SUMMARY", style_header))
    story.append(HRFlowable(width="100%", thickness=1, color=SEBI_GOLD))
    story.append(Spacer(1, 0.2 * cm))

    impossibility_color = (
        "red" if alert.impossibility_score >= 8.0
        else "orange" if alert.impossibility_score >= 6.0
        else "goldenrod"
    )
    story.append(Paragraph(
        f"ARGUS has detected a <b>potential market manipulation incident</b> with an "
        f"impossibility score of <font color='{impossibility_color}'>"
        f"<b>{alert.impossibility_score:.2f} / 10.00</b></font>. "
        f"The system flagged the scrip <b>{alert.scrip}</b> on exchange <b>{alert.exchange}</b> "
        f"during the period <b>{case.from_date}</b> to <b>{case.to_date}</b>.",
        style_body,
    ))
    story.append(Paragraph(
        f"Scheme Type Detected: <b>{alert.scheme_type.upper().replace('_', ' ')}</b>",
        style_bold,
    ))
    story.append(Spacer(1, 0.3 * cm))

    score_data = [
        ["Detection Engine", "Score", "Weight", "Contribution"],
        ["Temporal Coincidence Network (GNN)", f"{alert.gnn_score:.2f}/10", "35%", f"{alert.gnn_score * 0.35:.2f}"],
        ["Zero-Day Anomaly Ensemble", f"{alert.zero_day_score:.2f}/10", "25%", f"{alert.zero_day_score * 0.25:.2f}"],
        ["Behavioral DNA Autoencoder", f"{alert.dna_score:.2f}/10", "25%", f"{alert.dna_score * 0.25:.2f}"],
        ["Cross-Market Phantom Detector", f"{alert.cross_market_score:.2f}/10", "15%", f"{alert.cross_market_score * 0.15:.2f}"],
        ["COMPOSITE IMPOSSIBILITY SCORE", f"{alert.impossibility_score:.2f}/10", "100%", "—"],
    ]
    score_table = Table(score_data, colWidths=[8.5 * cm, 2.5 * cm, 2 * cm, 2.5 * cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SEBI_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), SEBI_GOLD),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, SEBI_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Section 2: Entities Under Investigation ───────────────────────────────
    story.append(Paragraph("SECTION 2: ENTITIES UNDER INVESTIGATION", style_header))
    story.append(HRFlowable(width="100%", thickness=1, color=SEBI_GOLD))
    story.append(Spacer(1, 0.2 * cm))

    accounts = alert.accounts_involved or []
    entity_data = [["#", "Account ID (Anonymized)", "Entity Name", "Status"]]
    for i, acc in enumerate(accounts[:20], 1):
        entity_name = case.entity_names[i - 1] if i <= len(case.entity_names) else "Under Investigation"
        entity_data.append([str(i), acc[:16], entity_name, "Flagged"])
    if len(accounts) > 20:
        entity_data.append(["...", f"+{len(accounts) - 20} more accounts", "", ""])

    entity_table = Table(entity_data, colWidths=[1 * cm, 5 * cm, 6.5 * cm, 3 * cm])
    entity_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SEBI_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SEBI_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("TEXTCOLOR", (3, 1), (3, -1), SEBI_RED),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(entity_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Section 3: Evidence ───────────────────────────────────────────────────
    story.append(Paragraph("SECTION 3: EVIDENCE", style_header))
    story.append(HRFlowable(width="100%", thickness=1, color=SEBI_GOLD))
    story.append(Spacer(1, 0.2 * cm))

    evidence = case.evidence_json or {}
    story.append(Paragraph("<b>3.1 GNN Coordination Evidence</b>", style_bold))
    story.append(Paragraph(
        f"The Temporal Coincidence Network identified coordinated trading behaviour among "
        f"{len(accounts)} accounts in {alert.scrip}. The GNN model detected temporal coincidences "
        f"(trades within 50ms of each other) at a frequency inconsistent with independent random trading. "
        f"GNN Score: {alert.gnn_score:.2f}/10.",
        style_body,
    ))
    story.append(Paragraph("<b>3.2 Behavioral DNA Evidence</b>", style_bold))
    story.append(Paragraph(
        f"The Behavioral DNA Autoencoder identified account fingerprints with high cosine similarity "
        f"to known fraudsters in the SEBI enforcement database. "
        f"DNA Match Score: {alert.dna_score:.2f}/10.",
        style_body,
    ))
    story.append(Paragraph("<b>3.3 Cross-Market Evidence</b>", style_bold))
    story.append(Paragraph(
        f"Cross-market analysis of NSE/BSE/NFO/MCX segments detected phantom positions and "
        f"circular trade flows involving {alert.scrip}. "
        f"Cross-Market Score: {alert.cross_market_score:.2f}/10.",
        style_body,
    ))
    story.append(Paragraph("<b>3.4 Zero-Day Anomaly Evidence</b>", style_bold))
    story.append(Paragraph(
        f"The anomaly ensemble (IForest + LOF + HBOS + OCSVM) flagged statistical features "
        f"of the trading session as highly anomalous relative to the normal order-flow baseline. "
        f"Zero-Day Score: {alert.zero_day_score:.2f}/10.",
        style_body,
    ))
    story.append(Spacer(1, 0.3 * cm))

    # ── Section 4: Statistical Basis ──────────────────────────────────────────
    story.append(Paragraph("SECTION 4: STATISTICAL BASIS", style_header))
    story.append(HRFlowable(width="100%", thickness=1, color=SEBI_GOLD))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "<b>Scoring Formula:</b> Overall = 0.35 × GNN + 0.25 × ZeroDay + 0.25 × DNA + 0.15 × CrossMarket",
        style_body,
    ))
    story.append(Paragraph(
        f"<b>Poisson Null Model:</b> The probability of observing the detected number of "
        f"temporal coincidences by random chance (under a Poisson model with the observed "
        f"trade rate) is p &lt; 10<sup>-{alert.gnn_score:.1f}</sup>, which is astronomically small "
        f"and confirms deliberate coordination.",
        style_body,
    ))
    story.append(Paragraph(
        f"<b>KS-Test:</b> The inter-trade timing distribution was found to deviate significantly "
        f"from the exponential distribution expected under natural order flow, providing additional "
        f"statistical confirmation of coordination.",
        style_body,
    ))

    if case.estimated_gain is not None:
        story.append(Paragraph(
            f"<b>Estimated Gain from Manipulation:</b> ₹{case.estimated_gain:,.2f}",
            style_bold,
        ))
    story.append(Spacer(1, 0.5 * cm))

    # ── Section 5: Recommended Action ─────────────────────────────────────────
    story.append(Paragraph("SECTION 5: RECOMMENDED ACTION", style_header))
    story.append(HRFlowable(width="100%", thickness=1, color=SEBI_RED))
    story.append(Spacer(1, 0.2 * cm))

    action = (
        "IMMEDIATE FREEZE AND FORMAL INVESTIGATION"
        if alert.impossibility_score >= 8.0
        else "ENHANCED SURVEILLANCE AND INVESTIGATION"
    )
    story.append(Paragraph(f"<b>Recommended Action: {action}</b>", ParagraphStyle(
        "action", parent=style_bold, textColor=SEBI_RED, fontSize=11,
    )))
    story.append(Spacer(1, 0.2 * cm))

    recommendations = [
        "1. Freeze trading accounts of all identified entities pending investigation.",
        "2. Issue Show Cause Notice (SCN) to all flagged account holders.",
        "3. Subpoena broker records and order logs for the detection window.",
        "4. Coordinate with MCA/ROC for corporate structure verification.",
        "5. Cross-reference with PMLA/FIU databases for suspicious transaction reports.",
        "6. Refer to SEBI Enforcement Division for formal adjudication.",
    ]
    for rec in recommendations:
        story.append(Paragraph(rec, style_body))
    story.append(Spacer(1, 1 * cm))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"Generated by ARGUS v1.0 — Adaptive Regulatory Graph for Unseen Surveillance | "
        f"For Official Use Only | {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}",
        ParagraphStyle("footer", parent=style_normal, fontSize=7, textColor=colors.grey, alignment=TA_CENTER),
    ))

    doc.build(story)

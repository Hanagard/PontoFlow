"""Espelho de ponto as a printable/signable PDF (§26) — generated on the backend.

Layout: company header, employee block, the daily grid, period totals and a signature
area for employee + employer, so the sheet can be printed and filed as-is.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from lib.timeutil import hhmm

INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#cbd5e1")
BAND = colors.HexColor("#f1f5f9")
GOOD = colors.HexColor("#047857")
BAD = colors.HexColor("#b91c1c")

STATUS_LABELS = {
    "completa": "Completa",
    "incompleta": "Incompleta",
    "falta": "Falta",
    "justificada": "Justificada",
    "folga": "Folga",
    "feriado": "Feriado",
}


def _br(iso: str) -> str:
    return "/".join(reversed(iso.split("-")))


def timesheet_pdf(
    *,
    company: dict,
    employee: dict,
    schedule_name: str | None,
    days: list[dict],
    summary: dict,
    start: str,
    end: str,
    cpf_masked: str,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Espelho de Ponto — {employee.get('name', '')}",
        author=company.get("name", "PontoFlow"),
    )

    base = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=14, textColor=INK, leading=17)
    small = ParagraphStyle("small", parent=base["Normal"], fontName="Helvetica", fontSize=8, textColor=MUTED, leading=10)
    cell = ParagraphStyle("cell", parent=base["Normal"], fontName="Helvetica", fontSize=7.5, textColor=INK, leading=9)
    sign = ParagraphStyle("sign", parent=base["Normal"], fontName="Helvetica", fontSize=8, textColor=INK, alignment=TA_CENTER, leading=10)

    flow: list = []

    # --- cabeçalho da empresa ---
    header = Table(
        [[
            Paragraph(f"<b>{company.get('name', '')}</b>", h1),
            Paragraph("ESPELHO DE PONTO ELETRÔNICO", ParagraphStyle("t", parent=h1, alignment=2)),
        ],
        [
            Paragraph(
                f"CNPJ: {company.get('cnpj') or '—'} &nbsp;&nbsp;|&nbsp;&nbsp; Fuso horário: {company.get('timezone', 'America/Belem')}",
                small,
            ),
            Paragraph(f"Período: {_br(start)} a {_br(end)}", ParagraphStyle("p", parent=small, alignment=2)),
        ]],
        colWidths=[150 * mm, 115 * mm],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 1), (-1, 1), 1, INK),
    ]))
    flow += [header, Spacer(1, 5 * mm)]

    # --- identificação do funcionário ---
    ident = Table(
        [[
            Paragraph(f"<b>Funcionário:</b> {employee.get('name', '')}", cell),
            Paragraph(f"<b>Matrícula:</b> {employee.get('matricula') or '—'}", cell),
            Paragraph(f"<b>CPF:</b> {cpf_masked}", cell),
            Paragraph(f"<b>Cargo:</b> {employee.get('cargo') or '—'}", cell),
            Paragraph(f"<b>Departamento:</b> {employee.get('department') or '—'}", cell),
            Paragraph(f"<b>Jornada:</b> {schedule_name or '—'}", cell),
        ]],
        colWidths=[62 * mm, 28 * mm, 32 * mm, 50 * mm, 46 * mm, 47 * mm],
    )
    ident.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BAND),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    flow += [ident, Spacer(1, 4 * mm)]

    # --- grade diária ---
    head = ["Data", "Dia", "Entrada", "Saída Int.", "Retorno", "Saída", "Trabalhado", "Previsto", "Atraso", "Extras", "Saldo", "Status / Observação"]
    rows: list[list] = [head]
    balance_rows: list[tuple[int, int]] = []  # (row index, sign)

    for index, day in enumerate(days, start=1):
        note = STATUS_LABELS.get(day["status"], day["status"])
        if day.get("holiday_name"):
            note = f"{note} — {day['holiday_name']}"
        rows.append([
            _br(day["date"]),
            day["weekday"][:3],
            day["entrada"]["hhmm"] or "—",
            day["inicio_intervalo"]["hhmm"] or "—",
            day["fim_intervalo"]["hhmm"] or "—",
            day["saida"]["hhmm"] or "—",
            day["worked_hhmm"] or "—",
            day["expected_hhmm"] or "—",
            day["delay_hhmm"] if day["delay_minutes"] else "—",
            day["overtime_hhmm"] or "—",
            day["balance_hhmm"] or "—",
            note,
        ])
        if day["balance_minutes"]:
            balance_rows.append((index, 1 if day["balance_minutes"] > 0 else -1))

    rows.append([
        "TOTAIS", "", "", "", "", "",
        hhmm(summary["total_worked_minutes"]) or "00:00",
        hhmm(summary["total_expected_minutes"]) or "00:00",
        hhmm(summary["total_delay_minutes"]) or "00:00",
        hhmm(summary["total_overtime_minutes"]) or "00:00",
        hhmm(summary["total_balance_minutes"]) or "00:00",
        f"Faltas: {summary['faltas']} · Incompletas: {summary['incompletas']} · Feriados: {summary.get('feriados', 0)}",
    ])

    widths = [19 * mm, 12 * mm, 19 * mm, 19 * mm, 19 * mm, 19 * mm, 22 * mm, 20 * mm, 18 * mm, 18 * mm, 18 * mm, 62 * mm]
    grid = Table(rows, colWidths=widths, repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.2),
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-2, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, BAND]),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), BAND),
        ("LINEABOVE", (0, -1), (-1, -1), 1, INK),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for row, direction in balance_rows:
        style.append(("TEXTCOLOR", (10, row), (10, row), GOOD if direction > 0 else BAD))
    total_balance = summary["total_balance_minutes"]
    if total_balance:
        style.append(("TEXTCOLOR", (10, -1), (10, -1), GOOD if total_balance > 0 else BAD))
    grid.setStyle(TableStyle(style))
    flow += [grid, Spacer(1, 6 * mm)]

    # --- declaração + assinaturas (mantidas juntas na mesma página) ---
    declaration = Paragraph(
        "Declaro que os horários registrados neste espelho correspondem à jornada efetivamente cumprida no período, "
        "conforme registros eletrônicos de ponto gerados pelo servidor.",
        small,
    )
    line = "_" * 46
    signatures = Table(
        [[
            Paragraph(f"{line}<br/><b>{employee.get('name', '')}</b><br/>Assinatura do funcionário", sign),
            Paragraph(f"{line}<br/><b>{company.get('name', '')}</b><br/>Assinatura do empregador", sign),
        ]],
        colWidths=[132 * mm, 133 * mm],
    )
    signatures.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    flow.append(KeepTogether([declaration, signatures]))

    doc.build(flow)
    return buffer.getvalue()

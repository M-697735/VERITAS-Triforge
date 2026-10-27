import io
import os
import xml.sax.saxutils
from typing import Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_NORMAL = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'

# Register Unicode TTF if available (DejaVuSans or Arial)
_font_candidates = [
    'C:/Windows/Fonts/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    'C:/Windows/Fonts/arial.ttf'
]

for fp in _font_candidates:
    if os.path.exists(fp):
        try:
            pdfmetrics.registerFont(TTFont('AppUnicode', fp))
            FONT_NORMAL = 'AppUnicode'
            bold_p = fp.replace('arial.ttf', 'arialbd.ttf').replace('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf')
            if os.path.exists(bold_p):
                pdfmetrics.registerFont(TTFont('AppUnicode-Bold', bold_p))
                FONT_BOLD = 'AppUnicode-Bold'
            else:
                FONT_BOLD = 'AppUnicode'
            break
        except Exception:
            pass

def clean_text(text: Any) -> str:
    """
    Escapes dynamic strings with xml.sax.saxutils.escape so ReportLab Paragraphs
    keep address tags like '<addr@domain.com>', and replaces unsupported characters
    with '?' when fallback font is active.
    """
    if text is None:
        return ""
    s = str(text)
    if FONT_NORMAL == 'Helvetica':
        s = "".join([c if ord(c) < 256 else "?" for c in s])
    return xml.sax.saxutils.escape(s)

def generate_forensic_pdf(analysis: Dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=24,
        bottomMargin=24
    )
    
    styles = getSampleStyleSheet()
    
    # Custom forensic styling with registered font
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=21,
        textColor=colors.HexColor('#0F172A'),
        fontName=FONT_BOLD
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#64748B'),
        fontName=FONT_NORMAL
    )
    
    notice_style = ParagraphStyle(
        'NoticeStyle',
        parent=styles['Normal'],
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#9A3412'),
        fontName=FONT_BOLD
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor('#1E293B'),
        fontName=FONT_BOLD,
        spaceBefore=5,
        spaceAfter=3
    )
    
    normal_text = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#334155'),
        fontName=FONT_NORMAL
    )
    
    bold_text = ParagraphStyle(
        'BoldText',
        parent=styles['Normal'],
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#0F172A'),
        fontName=FONT_BOLD
    )

    story = []
    
    # 1. Header
    story.append(Paragraph("VERITAS — Forensic Email Analysis Report", title_style))
    story.append(Paragraph("Multi-Layer Forensics & Cross-Layer Contradiction Verification Engine", subtitle_style))
    story.append(Spacer(1, 4))
    
    # Simulated Dataset Notice Banner
    notice_text = clean_text("NOTICE: Simulated demo dataset — GeoIP, ASN, and Domain Age values are illustrative, not authoritative.")
    notice_table = Table([[Paragraph(f"<b>{notice_text}</b>", notice_style)]], colWidths=[552])
    notice_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFBEB')),
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#FCD34D')),
        ('PADDING', (0,0), (-1,-1), 3),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(notice_table)
    story.append(Spacer(1, 5))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#3B82F6'), spaceAfter=6))
    
    # 2. Email & Case Metadata Table
    email_meta = analysis.get("email_meta", {})
    sha256 = analysis.get("sha256_hash", "")
    case_id = analysis.get("case_id", "CASE-NEW")
    timestamp = analysis.get("timestamp", "N/A")
    
    meta_data = [
        [Paragraph(f"<b>Case ID:</b> {clean_text(case_id)}", bold_text), Paragraph(f"<b>Analysis UTC:</b> {clean_text(timestamp)}", normal_text)],
        [Paragraph("<b>Subject:</b>", bold_text), Paragraph(clean_text(email_meta.get("subject", "(No Subject)")), bold_text)],
        [Paragraph("<b>From:</b>", bold_text), Paragraph(clean_text(email_meta.get("from_header", "")), normal_text)],
        [Paragraph("<b>Reply-To:</b>", bold_text), Paragraph(clean_text(email_meta.get("reply_to_header", "")), normal_text)],
        [Paragraph("<b>Date:</b>", bold_text), Paragraph(clean_text(email_meta.get("date", "")), normal_text)],
        [Paragraph("<b>SHA-256 Hash:</b>", bold_text), Paragraph(f"<font face='Courier' size='7'>{clean_text(sha256)}</font>", normal_text)]
    ]
    
    meta_table = Table(meta_data, colWidths=[90, 462])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0,0), (-1,-1), 2.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))
    
    # 3. Verdict Banner
    verdict = analysis.get("verdict", {})
    verdict_label = verdict.get("verdict", "Needs Review")
    confidence = verdict.get("confidence", "HIGH")
    rule_ids = verdict.get("driving_rule_ids", [])
    
    bg_color = colors.HexColor('#FEF2F2') if verdict_label == "Likely Fraudulent" else (
        colors.HexColor('#FFFBEB') if verdict_label == "Needs Review" else colors.HexColor('#F0FDF4')
    )
    border_color = colors.HexColor('#EF4444') if verdict_label == "Likely Fraudulent" else (
        colors.HexColor('#F59E0B') if verdict_label == "Needs Review" else colors.HexColor('#10B981')
    )
    
    v_title = clean_text(f"VERDICT: {verdict_label.upper()}")
    v_conf = clean_text(f"Confidence: {confidence} | Driving Rules: {', '.join(rule_ids) if rule_ids else 'None'}")
    v_summary = clean_text(verdict.get("summary", ""))
    
    verdict_content = [
        [Paragraph(f"<b>{v_title}</b>", ParagraphStyle('V', parent=bold_text, fontSize=11, fontName=FONT_BOLD, textColor=border_color)),
         Paragraph(f"<b>{v_conf}</b>", normal_text)],
        [Paragraph(v_summary, normal_text), ""]
    ]
    verdict_table = Table(verdict_content, colWidths=[240, 312])
    verdict_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_color),
        ('BOX', (0,0), (-1,-1), 1.2, border_color),
        ('SPAN', (0,1), (1,1)),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(verdict_table)
    story.append(Spacer(1, 6))
    
    # 4. Contradictions Section
    story.append(Paragraph("Cross-Layer Contradictions Panel", section_heading))
    contradictions = analysis.get("contradictions", [])
    
    if not contradictions:
        no_c_p = Paragraph("<b>No Cross-Layer Contradictions Detected:</b> All evidence layers corroborate the claimed sender identity and infrastructure.", normal_text)
        no_c_table = Table([[no_c_p]], colWidths=[552])
        no_c_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0FDF4')),
            ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#10B981')),
            ('PADDING', (0,0), (-1,-1), 4)
        ]))
        story.append(no_c_table)
    else:
        for c in contradictions:
            c_rule = clean_text(c.get("rule_id", "RULE"))
            c_title = clean_text(c.get("title", "Contradiction"))
            c_desc = clean_text(c.get("description", ""))
            c_layers = clean_text(", ".join(c.get("layers_compared", [])))
            
            c_row = [
                [Paragraph(f"<b>[{c_rule}] {c_title}</b>", ParagraphStyle('C', parent=bold_text, fontName=FONT_BOLD, textColor=colors.HexColor('#991B1B'))),
                 Paragraph(f"<b>Layers:</b> {c_layers}", subtitle_style)],
                [Paragraph(c_desc, normal_text), ""]
            ]
            c_table = Table(c_row, colWidths=[280, 272])
            c_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF2F2')),
                ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#FCA5A5')),
                ('SPAN', (0,1), (1,1)),
                ('PADDING', (0,0), (-1,-1), 3.5),
            ]))
            story.append(c_table)
            story.append(Spacer(1, 3))
            
    story.append(Spacer(1, 5))
    
    # 5. 5-Layer Forensic Evidence Breakdown
    story.append(Paragraph("5-Layer Forensic Evidence Summary", section_heading))
    
    layers_data = [
        ("Layer 1: Claimed Identity", analysis.get("layer1", {})),
        ("Layer 2: Technical Identity", analysis.get("layer2", {})),
        ("Layer 3: Content & Intent", analysis.get("layer3", {})),
        ("Layer 4: Infrastructure", analysis.get("layer4", {})),
        ("Layer 5: Historical Pattern", analysis.get("layer5", {}))
    ]
    
    table_rows = [["Layer", "Status", "Forensic Findings Summary"]]
    for name, data in layers_data:
        status = data.get("status", "UNCERTAIN")
        summary = clean_text(data.get("summary", ""))
        
        status_p = Paragraph(f"<b>{clean_text(status)}</b>", ParagraphStyle(
            'S', parent=bold_text, fontName=FONT_BOLD,
            textColor=colors.HexColor('#166534') if status == "VERIFIED" else (
                colors.HexColor('#9A3412') if status == "PROBABLE" else colors.HexColor('#991B1B')
            )
        ))
        
        table_rows.append([
            Paragraph(f"<b>{clean_text(name)}</b>", normal_text),
            status_p,
            Paragraph(summary, normal_text)
        ])
        
    l_table = Table(table_rows, colWidths=[140, 80, 332])
    l_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(l_table)
    story.append(Spacer(1, 8))
    
    # 6. Chain of Custody & Legal Disclaimer Footer
    story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor('#94A3B8'), spaceAfter=4))
    story.append(Paragraph("<b>SHA-256 of the submitted file is shown above; this report does not verify external records.</b>", subtitle_style))
    
    doc.build(story)
    return buffer.getvalue()

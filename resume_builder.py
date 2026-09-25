"""
Builds an ATS-friendly .docx resume from the tailored JSON that ai_tailor.py
produces. ATS-friendly here means:
  - single column, no text boxes, no tables, no headers/footers, no images
  - standard fonts, standard section headings, reverse-chronological order
  - real bullet-list styles (not typed bullet characters)
"""
import re
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

FONT_NAME = "Calibri"


def _set_font(run, size=11, bold=False):
    run.font.name = FONT_NAME
    run.font.size = Pt(size)
    run.font.bold = bold


def _heading(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text.upper())
    _set_font(run, size=12, bold=True)
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    # simple bottom border for a clean section divider, ATS-safe (no text box)
    pPr = p._p.get_or_add_pPr()
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "444444")
    pBdr.append(bottom)
    pPr.append(pBdr)


def build_resume_docx(candidate_name: str, contact_line: str, tailored: dict, out_path: str):
    doc = Document()
    for section in doc.sections:
        section.top_margin = Pt(36)
        section.bottom_margin = Pt(36)
        section.left_margin = Pt(54)
        section.right_margin = Pt(54)

    # Name
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(candidate_name)
    _set_font(run, size=18, bold=True)

    # Headline
    if tailored.get("tailored_headline"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(tailored["tailored_headline"])
        _set_font(run, size=12, bold=False)

    # Contact
    if contact_line:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(contact_line)
        _set_font(run, size=10)

    # Summary
    if tailored.get("tailored_summary"):
        _heading(doc, "Summary")
        p = doc.add_paragraph()
        run = p.add_run(tailored["tailored_summary"])
        _set_font(run, size=11)

    # Skills
    skills = tailored.get("key_skills") or []
    if skills:
        _heading(doc, "Key Skills")
        p = doc.add_paragraph()
        run = p.add_run(" • ".join(skills))
        _set_font(run, size=11)

    # Experience
    exp = tailored.get("experience_bullets") or []
    if exp:
        _heading(doc, "Experience")
        for role in exp:
            p = doc.add_paragraph()
            run = p.add_run(f"{role.get('role', '')} — {role.get('company', '')}")
            _set_font(run, size=11, bold=True)
            if role.get("dates"):
                p2 = doc.add_paragraph()
                run2 = p2.add_run(role["dates"])
                _set_font(run2, size=10)
                p2.paragraph_format.space_after = Pt(2)
            for bullet in role.get("bullets", []):
                bp = doc.add_paragraph(style="List Bullet")
                brun = bp.add_run(bullet)
                _set_font(brun, size=11)

    # Education
    edu = tailored.get("education") or []
    if edu:
        _heading(doc, "Education")
        for line in edu:
            p = doc.add_paragraph()
            run = p.add_run(line)
            _set_font(run, size=11)

    doc.save(out_path)
    return out_path


def build_cover_letter_docx(candidate_name: str, contact_line: str, cover_letter_text: str, out_path: str):
    doc = Document()
    p = doc.add_paragraph()
    run = p.add_run(candidate_name)
    _set_font(run, size=14, bold=True)
    if contact_line:
        p = doc.add_paragraph()
        run = p.add_run(contact_line)
        _set_font(run, size=10)
    doc.add_paragraph()
    for para in re.split(r"\n\s*\n", cover_letter_text.strip()):
        p = doc.add_paragraph()
        run = p.add_run(para.strip())
        _set_font(run, size=11)
    doc.save(out_path)
    return out_path

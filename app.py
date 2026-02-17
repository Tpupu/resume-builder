from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field
from typing import Any, List

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Templates you *intend* to support
TEMPLATES = ["classic", "modern", "compact", "executive", "minimal", "bold"]

FONT_MAP = {
    "sans": ("Helvetica", "Helvetica-Bold"),
    "serif": ("Times-Roman", "Times-Bold"),
    "mono": ("Courier", "Courier-Bold"),
}


@dataclass
class Job:
    title: str = ""
    company: str = ""
    location: str = ""
    dates: str = ""
    bullets: List[str] = field(default_factory=list)


@dataclass
class ResumeData:
    full_name: str = ""
    email: str = ""
    phone: str = ""

    target_title: str = ""
    years_experience: str = ""
    strengths: str = ""
    wins: str = ""
    summary: str = ""
    skills: str = ""

    certs: str = ""
    awards: str = ""
    include_references: bool = False

    template: str = "classic"
    font_family: str = "sans"   # sans | serif | mono
    page_limit: int = 1         # 1 or 2

    jobs: List[Job] = field(default_factory=list)
    jobs_json: str = "[]"


ACTION_VERBS = [
    "Led", "Managed", "Coached", "Improved", "Streamlined", "Built", "Owned",
    "Delivered", "Reduced", "Increased", "Trained", "Implemented", "Coordinated",
    "Optimized", "Supported", "Resolved", "Launched", "Standardized"
]


# ----------------------------
# Helpers
# ----------------------------
def _clean(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _title_name(name: str) -> str:
    name = _clean(name)
    if not name:
        return ""
    return " ".join([w[:1].upper() + w[1:].lower() if w else "" for w in name.split()])


def _split_csv(s: str) -> List[str]:
    s = _clean(s)
    if not s:
        return []
    parts = [p.strip() for p in s.split(",")]
    return [p for p in parts if p]


def _clamp_template(t: str) -> str:
    t = (t or "").strip().lower()
    return t if t in TEMPLATES else "classic"


def _clamp_font(f: str) -> str:
    f = (f or "").strip().lower()
    return f if f in FONT_MAP else "sans"


def _clamp_page_limit(n: Any) -> int:
    try:
        v = int(n)
    except Exception:
        return 1
    return 2 if v == 2 else 1


def _truthy(v: Any) -> bool:
    """
    Handles checkbox + querystring cases:
    on/true/1/yes/y -> True
    """
    s = str(v or "").strip().lower()
    return s in {"on", "true", "1", "yes", "y"}


def _sentenceize(s: str) -> str:
    s = _clean(s)
    if not s:
        return ""
    if s[-1] not in ".!?":
        s += "."
    return s[0].upper() + s[1:]


def _make_bullets(text: str, max_items: int = 6) -> List[str]:
    text = _clean(text)
    if not text:
        return []

    chunks = re.split(r"[•\n;]+", text)
    expanded: List[str] = []
    for c in chunks:
        c = c.strip()
        if not c:
            continue
        if "," in c and len(c) > 50:
            expanded.extend([x.strip() for x in c.split(",") if x.strip()])
        else:
            expanded.append(c)

    bullets: List[str] = []
    for i, raw in enumerate(expanded):
        txt = re.sub(r"^\-+\s*", "", raw).strip()
        txt = re.sub(r"^(i\s+)?(was\s+)?(did\s+)?", "", txt, flags=re.I).strip()
        txt = _sentenceize(txt)
        if not txt:
            continue

        verb = ACTION_VERBS[i % len(ACTION_VERBS)]
        if re.match(
            r"^(led|managed|coached|improved|streamlined|built|owned|delivered|reduced|increased|trained|implemented|coordinated|optimized|supported|resolved|launched|standardized)\b",
            txt, re.I
        ):
            bullets.append(txt)
        else:
            bullets.append(f"{verb} {txt[0].lower() + txt[1:]}")
    return bullets[:max_items]


def _normalize_skills(skills: str, strengths: str) -> List[str]:
    items = _split_csv(skills) or _split_csv(strengths)
    out: List[str] = []
    for it in items:
        it = it.strip()
        if not it:
            continue
        clean = it if it.isupper() else it[:1].upper() + it[1:]
        if clean.lower() not in [x.lower() for x in out]:
            out.append(clean)
    return out[:18]


def _parse_jobs_json(jobs_json: str) -> List[Job]:
    jobs_json = (jobs_json or "").strip()
    if not jobs_json:
        return []
    try:
        raw = json.loads(jobs_json)
    except Exception:
        return []
    if not isinstance(raw, list):
        return []

    jobs: List[Job] = []
    for item in raw[:6]:
        if not isinstance(item, dict):
            continue

        # support both keys: bullets (list) OR bullets_text (string)
        bullets_val = item.get("bullets", None)
        if bullets_val is None:
            bullets_val = item.get("bullets_text", "")

        if isinstance(bullets_val, str):
            bullets_list = _make_bullets(bullets_val, max_items=6)
        elif isinstance(bullets_val, list):
            bullets_list = [_sentenceize(str(b)) for b in bullets_val if str(b).strip()]
        else:
            bullets_list = []

        jobs.append(
            Job(
                title=_clean(str(item.get("title", ""))),
                company=_clean(str(item.get("company", ""))),
                location=_clean(str(item.get("location", ""))),
                dates=_clean(str(item.get("dates", ""))),
                bullets=bullets_list[:6],
            )
        )
    return jobs


def _generate_summary(data: ResumeData, highlights: List[str], skills_list: List[str]) -> str:
    if _clean(data.summary):
        return _sentenceize(data.summary)

    years = _clean(data.years_experience) or "several"
    title = _clean(data.target_title) or "leader"

    core = _split_csv(data.strengths)[:5]
    core_str = ", ".join(core) if core else "operations, team leadership, and problem solving"

    line1 = f"{years}+ years as a {title}, focused on {core_str}."
    if highlights:
        h = re.sub(r"\.$", "", highlights[0])
        line2 = f"Known for results like: {h}."
    else:
        line2 = "Known for clear communication, steady leadership, and practical execution."

    if skills_list:
        line3 = f"Strengths include {', '.join(skills_list[:6])}."
    else:
        line3 = "Strengths include leadership, coaching, and continuous improvement."

    return " ".join([line1, line2, line3])


def _polish_text(payload: dict) -> dict:
    summary = _clean(str(payload.get("summary", "")))
    wins = _clean(str(payload.get("wins", "")))
    strengths = _clean(str(payload.get("strengths", "")))
    title = _clean(str(payload.get("target_title", ""))) or "leader"
    years = _clean(str(payload.get("years_experience", ""))) or "10+"

    bullets = _make_bullets(wins, max_items=7)

    if summary:
        s = _sentenceize(summary)
        s = re.sub(r"\bvery\b", "", s, flags=re.I)
        s = re.sub(r"\breally\b", "", s, flags=re.I)
        s = re.sub(r"\s{2,}", " ", s).strip()
        polished_summary = s
    else:
        core = _split_csv(strengths)[:5]
        core_str = ", ".join(core) if core else "operations, people leadership, and problem solving"
        polished_summary = (
            f"{years}+ years as a {title}, known for {core_str}. "
            f"Delivers consistent results through clear direction, calm execution, and strong follow-through."
        )

    skill_suggestions = _normalize_skills(str(payload.get("skills", "")), strengths)
    if not skill_suggestions:
        skill_suggestions = _normalize_skills("", "Leadership, Coaching, Process Improvement, Communication")

    return {
        "polished_summary": polished_summary,
        "bullets": bullets,
        "skills_suggested": skill_suggestions[:12],
    }


# ----------------------------
# PDF helpers
# ----------------------------
def _pdf_wrap(c: canvas.Canvas, text: str, x: float, y: float, maxw: float,
              font_name: str, font_size: int, leading: float) -> float:
    text = _clean(text)
    if not text:
        return y
    c.setFont(font_name, font_size)
    words = text.split(" ")
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if c.stringWidth(test, font_name, font_size) <= maxw:
            line = test
        else:
            c.drawString(x, y, line)
            y -= leading
            line = w
    if line:
        c.drawString(x, y, line)
        y -= leading
    return y


def _pdf_section_title(c: canvas.Canvas, title: str, x: float, y: float, maxw: float, font_bold: str) -> float:
    c.setFont(font_bold, 11)
    c.drawString(x, y, title.upper())
    y -= 6
    c.setLineWidth(0.6)
    c.line(x, y, x + maxw, y)
    y -= 14
    return y


def _pdf_bullets(c: canvas.Canvas, bullets: List[str], x: float, y: float, maxw: float,
                 font_name: str, font_size: int, leading: float) -> float:
    if not bullets:
        return y
    c.setFont(font_name, font_size)
    indent = 10
    for b in bullets:
        b = _clean(b).rstrip(".")
        if not b:
            continue

        words = b.split(" ")
        line = ""
        first_line = True
        for w in words:
            test = (line + " " + w).strip()
            limit = maxw - indent
            if c.stringWidth(test, font_name, font_size) <= limit:
                line = test
            else:
                if first_line:
                    c.drawString(x, y, "•")
                    c.drawString(x + indent, y, line)
                    first_line = False
                else:
                    c.drawString(x + indent, y, line)
                y -= leading
                line = w

        if line:
            if first_line:
                c.drawString(x, y, "•")
                c.drawString(x + indent, y, line)
            else:
                c.drawString(x + indent, y, line)
            y -= leading
    return y


def _build_pdf_bytes(data: ResumeData, polished_summary: str, highlights: List[str], skills_list: List[str]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    font_name, font_bold = FONT_MAP.get(data.font_family, FONT_MAP["sans"])

    left = 0.85 * inch
    right = width - 0.85 * inch
    top = height - 0.85 * inch
    maxw = right - left

    # Header
    c.setFont(font_bold, 18)
    c.drawString(left, top, data.full_name or "Your Name")

    c.setFont(font_name, 10.5)
    subtitle_parts = []
    if data.target_title:
        subtitle_parts.append(data.target_title)
    if data.years_experience:
        subtitle_parts.append(f"{data.years_experience} yrs")
    subtitle = " • ".join([p for p in subtitle_parts if p])
    if subtitle:
        c.drawString(left, top - 22, subtitle)

    contact = " • ".join([x for x in [data.email, data.phone] if x])
    if contact:
        c.setFont(font_name, 10)
        c.drawString(left, top - 38, contact)

    c.setLineWidth(0.7)
    c.line(left, top - 48, right, top - 48)

    y = top - 70

    # Summary
    y = _pdf_section_title(c, "Professional Summary", left, y, maxw, font_bold)
    y = _pdf_wrap(c, polished_summary, left, y, maxw, font_name, 11, 14)
    y -= 6

    # Skills (2 columns)
    if skills_list:
        y = _pdf_section_title(c, "Skills", left, y, maxw, font_bold)
        c.setFont(font_name, 10.5)
        col_gap = 18
        col_w = (maxw - col_gap) / 2
        x1 = left
        x2 = left + col_w + col_gap

        skills = skills_list[:18]
        mid = (len(skills) + 1) // 2
        left_col = skills[:mid]
        right_col = skills[mid:]

        yy = y
        for s in left_col:
            if yy < 1.25 * inch:
                if data.page_limit == 1:
                    break
                c.showPage()
                yy = height - 0.85 * inch
                c.setFont(font_name, 10.5)
            c.drawString(x1, yy, f"• {s}")
            yy -= 13

        yy2 = y
        for s in right_col:
            if yy2 < 1.25 * inch:
                if data.page_limit == 1:
                    break
                c.showPage()
                yy2 = height - 0.85 * inch
                c.setFont(font_name, 10.5)
            c.drawString(x2, yy2, f"• {s}")
            yy2 -= 13

        y = min(yy, yy2) - 6

    # Experience
    if data.jobs:
        y = _pdf_section_title(c, "Experience", left, y, maxw, font_bold)
        for job in data.jobs[:4]:
            if y < 1.45 * inch:
                if data.page_limit == 1:
                    break
                c.showPage()
                y = height - 0.85 * inch
                y = _pdf_section_title(c, "Experience", left, y, maxw, font_bold)

            header_left = " — ".join([p for p in [job.title, job.company] if p])
            header_right = job.dates or ""
            c.setFont(font_bold, 11)
            c.drawString(left, y, header_left[:120])
            if header_right:
                c.setFont(font_name, 10)
                c.drawRightString(right, y + 1, header_right[:40])
            y -= 14

            if job.location:
                c.setFont(font_name, 10)
                c.drawString(left, y, job.location[:90])
                y -= 12

            y = _pdf_bullets(c, job.bullets[:5], left, y, maxw, font_name, 10.5, 13)
            y -= 6

    # Highlights
    if highlights:
        if y < 1.55 * inch:
            if data.page_limit == 2:
                c.showPage()
                y = height - 0.85 * inch
            else:
                highlights = []
        if highlights:
            y = _pdf_section_title(c, "Highlights", left, y, maxw, font_bold)
            y = _pdf_bullets(c, highlights[:6], left, y, maxw, font_name, 10.5, 13)
            y -= 6

    # Additional (Certs/Awards/References)
    footer_blocks: List[str] = []
    if _clean(data.certs):
        footer_blocks.append("Certifications: " + ", ".join(_split_csv(data.certs)[:10]))
    if _clean(data.awards):
        footer_blocks.append("Awards: " + ", ".join(_split_csv(data.awards)[:10]))
    if data.include_references:
        footer_blocks.append("References available upon request.")

    if footer_blocks:
        if y < 1.35 * inch and data.page_limit == 2:
            c.showPage()
            y = height - 0.85 * inch
        if y >= 1.10 * inch:
            y = _pdf_section_title(c, "Additional", left, y, maxw, font_bold)
            for block in footer_blocks:
                if y < 1.10 * inch:
                    break
                y = _pdf_wrap(c, block, left, y, maxw, font_name, 10.5, 13)

    # IMPORTANT: do NOT call showPage() again here
    c.save()
    return buf.getvalue()


def _safe_template_exists(name: str) -> bool:
    env = templates.env
    try:
        env.get_template(name)
        return True
    except Exception:
        return False


# ----------------------------
# Pages
# ----------------------------
@app.get("/", response_class=HTMLResponse)
def page_builder(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "active_tab": "builder", "templates": TEMPLATES, "selected_template": "classic"},
    )


@app.get("/templates", response_class=HTMLResponse)
def page_templates(request: Request):
    # If you don't have this yet, it won't crash; it will fall back to index.html
    tpl = "templates_page.html" if _safe_template_exists("templates_page.html") else "index.html"
    return templates.TemplateResponse(
        tpl,
        {"request": request, "active_tab": "templates", "templates": TEMPLATES, "selected_template": "classic"},
    )


@app.get("/guided", response_class=HTMLResponse)
def page_guided(request: Request):
    tpl = "guided_page.html" if _safe_template_exists("guided_page.html") else "index.html"
    return templates.TemplateResponse(
        tpl,
        {"request": request, "active_tab": "guided", "templates": TEMPLATES, "selected_template": "classic"},
    )


# ----------------------------
# Mini AI polish endpoint
# ----------------------------
@app.post("/polish")
async def polish(request: Request):
    payload = await request.json()
    out = _polish_text(payload if isinstance(payload, dict) else {})
    return JSONResponse(out)


# ----------------------------
# Build -> Preview
# ----------------------------
@app.post("/build", response_class=HTMLResponse)
def build(
    request: Request,
    full_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    template: str = Form("classic"),
    font_family: str = Form("sans"),
    page_limit: int = Form(1),

    target_title: str = Form(""),
    years_experience: str = Form(""),
    strengths: str = Form(""),
    wins: str = Form(""),
    summary: str = Form(""),
    skills: str = Form(""),

    certs: str = Form(""),
    awards: str = Form(""),
    include_references: str = Form(""),

    jobs_json: str = Form("[]"),
):
    data = ResumeData(
        full_name=_title_name(full_name),
        email=_clean(email),
        phone=_clean(phone),

        template=_clamp_template(template),
        font_family=_clamp_font(font_family),
        page_limit=_clamp_page_limit(page_limit),

        target_title=_clean(target_title),
        years_experience=_clean(years_experience),
        strengths=_clean(strengths),
        wins=_clean(wins),
        summary=_clean(summary),
        skills=_clean(skills),

        certs=_clean(certs),
        awards=_clean(awards),
        include_references=_truthy(include_references),

        jobs_json=(jobs_json or "[]").strip() or "[]",
    )
    data.jobs = _parse_jobs_json(data.jobs_json)

    highlights = _make_bullets(data.wins, max_items=7)
    skills_list = _normalize_skills(data.skills, data.strengths)
    polished_summary = _generate_summary(data, highlights, skills_list)

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "active_tab": "builder",
            "templates": TEMPLATES,
            "selected_template": data.template,
            "data": data,
            "polished_summary": polished_summary,
            "highlights": highlights,
            "skills_list": skills_list,
        },
    )


# Live swap endpoint used by JS (returns template partial; falls back if missing)
@app.get("/swap", response_class=HTMLResponse)
def swap(
    request: Request,
    template: str = "classic",

    full_name: str = "",
    email: str = "",
    phone: str = "",

    target_title: str = "",
    years_experience: str = "",
    strengths: str = "",
    wins: str = "",
    summary: str = "",
    skills: str = "",

    certs: str = "",
    awards: str = "",
    include_references: str = "",

    jobs_json: str = "[]",

    font_family: str = "sans",
    page_limit: int = 1,
):
    data = ResumeData(
        full_name=_title_name(full_name),
        email=_clean(email),
        phone=_clean(phone),

        template=_clamp_template(template),
        font_family=_clamp_font(font_family),
        page_limit=_clamp_page_limit(page_limit),

        target_title=_clean(target_title),
        years_experience=_clean(years_experience),
        strengths=_clean(strengths),
        wins=_clean(wins),
        summary=_clean(summary),
        skills=_clean(skills),

        certs=_clean(certs),
        awards=_clean(awards),
        include_references=_truthy(include_references),

        jobs_json=(jobs_json or "[]").strip() or "[]",
    )
    data.jobs = _parse_jobs_json(data.jobs_json)

    highlights = _make_bullets(data.wins, max_items=7)
    skills_list = _normalize_skills(data.skills, data.strengths)
    polished_summary = _generate_summary(data, highlights, skills_list)

    candidate = f"result_{data.template}.html"
    tpl = candidate if _safe_template_exists(candidate) else "result_classic.html"

    return templates.TemplateResponse(
        tpl,
        {
            "request": request,
            "data": data,
            "polished_summary": polished_summary,
            "highlights": highlights,
            "skills_list": skills_list,
            "partial": True,
        },
    )


@app.post("/download_pdf")
def download_pdf(
    full_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    template: str = Form("classic"),
    font_family: str = Form("sans"),
    page_limit: int = Form(1),

    target_title: str = Form(""),
    years_experience: str = Form(""),
    strengths: str = Form(""),
    wins: str = Form(""),
    summary: str = Form(""),
    skills: str = Form(""),

    certs: str = Form(""),
    awards: str = Form(""),
    include_references: str = Form(""),

    jobs_json: str = Form("[]"),
):
    data = ResumeData(
        full_name=_title_name(full_name),
        email=_clean(email),
        phone=_clean(phone),

        template=_clamp_template(template),
        font_family=_clamp_font(font_family),
        page_limit=_clamp_page_limit(page_limit),

        target_title=_clean(target_title),
        years_experience=_clean(years_experience),
        strengths=_clean(strengths),
        wins=_clean(wins),
        summary=_clean(summary),
        skills=_clean(skills),

        certs=_clean(certs),
        awards=_clean(awards),
        include_references=_truthy(include_references),

        jobs_json=(jobs_json or "[]").strip() or "[]",
    )
    data.jobs = _parse_jobs_json(data.jobs_json)

    highlights = _make_bullets(data.wins, max_items=7)
    skills_list = _normalize_skills(data.skills, data.strengths)
    polished_summary = _generate_summary(data, highlights, skills_list)

    pdf_bytes = _build_pdf_bytes(data, polished_summary, highlights, skills_list)
    filename = f"{(data.full_name or 'resume').replace(' ', '_')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/health")
def health():
    return {"ok": True}









    





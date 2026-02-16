from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from io import BytesIO
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ----------------------------
# Helpers
# ----------------------------
def _split_csv(s: str) -> list[str]:
    if not s:
        return []
    items = []
    for part in s.split(","):
        p = part.strip()
        if p:
            items.append(p)
    return items


def _safe_template_name(t: str) -> str:
    t = (t or "classic").strip().lower()
    allowed = {"classic", "modern", "compact"}
    return t if t in allowed else "classic"


def _auto_summary(target_title: str, years: str, strengths_csv: str, wins_csv: str) -> str:
    title = (target_title or "").strip()
    yrs = (years or "").strip()
    strengths = _split_csv(strengths_csv)
    wins = _split_csv(wins_csv)

    parts = []
    if title:
        parts.append(f"{title}")
    if yrs:
        parts.append(f"with {yrs} years of experience")
    head = " ".join(parts).strip()
    if head:
        head += "."

    s2 = ""
    if strengths:
        s2 = f"Known for {', '.join(strengths[:4])}."
    s3 = ""
    if wins:
        s3 = f"Recent wins: {', '.join(wins[:3])}."
    out = " ".join([x for x in [head, s2, s3] if x]).strip()
    return out or "Reliable professional with a focus on results, teamwork, and continuous improvement."


def _make_pdf(name: str, email: str, phone: str, summary: str, skills: list[str], highlights: list[str]) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER

    x = 0.9 * inch
    y = height - 0.9 * inch

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x, y, name or "Resume")
    y -= 0.35 * inch

    c.setFont("Helvetica", 10)
    meta = " | ".join([p for p in [email, phone] if p])
    if meta:
        c.drawString(x, y, meta)
        y -= 0.35 * inch

    # Summary
    if summary:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "Professional Summary")
        y -= 0.2 * inch
        c.setFont("Helvetica", 10)

        # simple wrap
        max_width = width - (2 * x)
        words = summary.split()
        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if c.stringWidth(test, "Helvetica", 10) <= max_width:
                line = test
            else:
                c.drawString(x, y, line)
                y -= 0.18 * inch
                line = w
        if line:
            c.drawString(x, y, line)
            y -= 0.3 * inch

    # Skills
    if skills:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "Skills")
        y -= 0.2 * inch
        c.setFont("Helvetica", 10)

        for s in skills[:18]:
            c.drawString(x, y, f"• {s}")
            y -= 0.18 * inch
            if y < 1.0 * inch:
                c.showPage()
                y = height - 0.9 * inch
                c.setFont("Helvetica", 10)

        y -= 0.15 * inch

    # Highlights
    if highlights:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "Highlights")
        y -= 0.2 * inch
        c.setFont("Helvetica", 10)

        for h in highlights[:18]:
            c.drawString(x, y, f"• {h}")
            y -= 0.18 * inch
            if y < 1.0 * inch:
                c.showPage()
                y = height - 0.9 * inch
                c.setFont("Helvetica", 10)

    c.save()
    buf.seek(0)
    return buf.read()


# ----------------------------
# Routes
# ----------------------------
@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/build", response_class=HTMLResponse)
async def build_resume(request: Request):
    form = await request.form()

    name = (form.get("name") or "").strip()
    email = (form.get("email") or "").strip()
    phone = (form.get("phone") or "").strip()

    # IMPORTANT: this must match the <select name="template"> in index.html
    template_choice = _safe_template_name(form.get("template"))

    # Guided inputs (used to auto-generate summary if summary is blank)
    target_title = (form.get("target_title") or "").strip()
    years = (form.get("years") or "").strip()
    strengths_csv = (form.get("strengths_csv") or "").strip()
    wins_csv = (form.get("wins_csv") or "").strip()

    summary = (form.get("summary") or "").strip()
    if not summary:
        summary = _auto_summary(target_title, years, strengths_csv, wins_csv)

    skills_csv = (form.get("skills_csv") or "").strip()
    skills = _split_csv(skills_csv)

    # Optional highlights list (if you already collect it)
    highlights_csv = (form.get("highlights_csv") or "").strip()
    highlights = _split_csv(highlights_csv)

    # If highlights not provided, build them from wins (nice fallback)
    if not highlights:
        highlights = _split_csv(wins_csv)

    template_map = {
        "classic": "result_classic.html",
        "modern": "result_modern.html",
        "compact": "result_compact.html",
    }
    template_file = template_map.get(template_choice, "result_classic.html")

    return templates.TemplateResponse(
        template_file,
        {
            "request": request,
            "name": name,
            "email": email,
            "phone": phone,
            "template": template_choice.capitalize(),
            "summary": summary,
            "skills": skills,
            "highlights": highlights,
        },
    )


@app.post("/download-pdf")
async def download_pdf(request: Request):
    form = await request.form()

    name = (form.get("name") or "").strip()
    email = (form.get("email") or "").strip()
    phone = (form.get("phone") or "").strip()
    summary = (form.get("summary") or "").strip()

    skills = _split_csv((form.get("skills_csv") or "").strip())
    highlights = _split_csv((form.get("highlights_csv") or "").strip())

    # fallback: if highlights blank, try wins_csv
    if not highlights:
        highlights = _split_csv((form.get("wins_csv") or "").strip())

    pdf_bytes = _make_pdf(name, email, phone, summary, skills, highlights)

    filename = "resume.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

    )



    





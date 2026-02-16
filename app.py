FILE: app.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


def _split_wins(wins: str) -> list[str]:
    if not wins:
        return []
    raw = wins.replace("•", ",").replace(";", ",")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    # Keep it readable (avoid huge lists)
    return parts[:8]


def _clean_commas(s: str) -> str:
    if not s:
        return ""
    parts = [p.strip() for p in s.split(",") if p.strip()]
    # remove duplicates while preserving order
    seen = set()
    out = []
    for p in parts:
        key = p.lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return ", ".join(out)


def _fallback_skills(target_title: str, strengths: str) -> str:
    base = _clean_commas(strengths)
    common = []

    t = (target_title or "").lower()

    if "manager" in t or "area" in t or "supervisor" in t:
        common = [
            "Team Leadership",
            "Coaching & Development",
            "Process Improvement",
            "Performance Tracking",
            "Safety & Compliance",
            "Problem Solving",
            "Shift Planning",
            "Communication",
        ]
    elif "front desk" in t or "hotel" in t or "guest" in t:
        common = [
            "Customer Service",
            "Front Desk Operations",
            "Conflict Resolution",
            "Scheduling",
            "Cash Handling",
            "Communication",
            "Attention to Detail",
        ]
    elif "it" in t or "support" in t or "help desk" in t:
        common = [
            "Troubleshooting",
            "Customer Support",
            "Ticketing",
            "Documentation",
            "Windows",
            "Networking Basics",
            "Communication",
        ]
    else:
        common = [
            "Communication",
            "Problem Solving",
            "Time Management",
            "Teamwork",
            "Adaptability",
        ]

    if base:
        return _clean_commas(base + ", " + ", ".join(common))
    return _clean_commas(", ".join(common))


def _generate_summary(target_title: str, years_exp: str, strengths: str, wins: str) -> str:
    title = (target_title or "Professional").strip()
    yrs = (years_exp or "").strip()
    strg = _clean_commas(strengths)
    wins_list = _split_wins(wins)

    pieces = []

    if yrs:
        pieces.append(f"{title} with {yrs} years of experience.")
    else:
        pieces.append(f"{title} with proven experience.")

    if strg:
        pieces.append(f"Strengths include {strg}.")

    if wins_list:
        # turn first 1–2 wins into a sentence
        first_two = wins_list[:2]
        if len(first_two) == 1:
            pieces.append(f"Known for {first_two[0]}.")
        else:
            pieces.append(f"Known for {first_two[0]} and {first_two[1]}.")

    pieces.append("Focused on reliable execution, clear communication, and strong results.")
    return " ".join(pieces).strip()


def _pick_template(choice: str) -> str:
    c = (choice or "classic").lower().strip()
    if c not in {"classic", "modern", "compact"}:
        c = "classic"
    return c


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/build", response_class=HTMLResponse)
def build_resume(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    template_choice: str = Form("classic"),
    target_title: str = Form(""),
    years_exp: str = Form(""),
    strengths: str = Form(""),
    wins: str = Form(""),
    summary: str = Form(""),
    skills: str = Form(""),
):
    template_choice = _pick_template(template_choice)

    summary_clean = (summary or "").strip()
    if not summary_clean:
        summary_clean = _generate_summary(target_title, years_exp, strengths, wins)

    skills_clean = _clean_commas((skills or "").strip())
    if not skills_clean:
        skills_clean = _fallback_skills(target_title, strengths)

    wins_list = _split_wins(wins)
    wins_joined = "||".join(wins_list)

    data = {
        "full_name": full_name.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "template_choice": template_choice,
        "summary": summary_clean,
        "skills_line": skills_clean,
        "wins_list": wins_list,
        "wins_joined": wins_joined,
    }

    tmpl = {
        "classic": "result_classic.html",
        "modern": "result_modern.html",
        "compact": "result_compact.html",
    }[template_choice]

    return templates.TemplateResponse(tmpl, {"request": request, "data": data})


@app.post("/download/pdf")
def download_pdf(
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    summary: str = Form(...),
    skills_line: str = Form(...),
    wins_joined: str = Form(""),
    template_choice: str = Form("classic"),
):
    # Build a clean PDF (simple + professional)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    left = 0.9 * inch
    right = width - 0.9 * inch
    y = height - 0.9 * inch

    # Header
    c.setFont("Helvetica-Bold", 20)
    c.drawString(left, y, full_name)
    y -= 18

    c.setFont("Helvetica", 11)
    contact_line = email
    if phone.strip():
        contact_line += f" | {phone.strip()}"
    c.drawString(left, y, contact_line)
    y -= 18

    # Accent line (slight style change by template)
    c.setLineWidth(2)
    if (template_choice or "").lower().strip() == "modern":
        c.setStrokeColorRGB(0.145, 0.388, 0.922)  # blue-ish
    else:
        c.setStrokeColorRGB(0.07, 0.09, 0.13)     # near-black
    c.line(left, y, right, y)
    y -= 22

    def draw_section_title(title: str):
        nonlocal y
        c.setFont("Helvetica-Bold", 13)
        c.setFillColorRGB(0.07, 0.09, 0.13)
        c.drawString(left, y, title)
        y -= 12

    def draw_paragraph(text: str, font="Helvetica", size=11, leading=14):
        nonlocal y
        c.setFont(font, size)
        c.setFillColorRGB(0.07, 0.09, 0.13)

        # simple wrap
        words = (text or "").split()
        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if c.stringWidth(test, font, size) <= (right - left):
                line = test
            else:
                c.drawString(left, y, line)
                y -= leading
                line = w
                if y < 1.0 * inch:
                    c.showPage()
                    y = height - 0.9 * inch
                    c.setFont(font, size)
        if line:
            c.drawString(left, y, line)
            y -= leading

    def ensure_space(min_space: float = 1.0 * inch):
        nonlocal y
        if y < min_space:
            c.showPage()
            y = height - 0.9 * inch

    # Summary
    ensure_space()
    draw_section_title("Professional Summary")
    draw_paragraph(summary, size=11, leading=14)
    y -= 6

    # Skills
    ensure_space()
    draw_section_title("Skills")
    draw_paragraph(skills_line, size=11, leading=14)
    y -= 6

    # Highlights
    wins_list = [w for w in (wins_joined or "").split("||") if w.strip()]
    if wins_list:
        ensure_space()
        draw_section_title("Highlights")
        c.setFont("Helvetica", 11)
        bullet_indent = left + 12
        for w in wins_list[:10]:
            ensure_space()
            c.drawString(left, y, "•")
            # wrap bullet
            text = w.strip()
            words = text.split()
            line = ""
            first_line = True
            for word in words:
                test = (line + " " + word).strip()
                maxw = (right - bullet_indent)
                if c.stringWidth(test, "Helvetica", 11) <= maxw:
                    line = test
                else:
                    c.drawString(bullet_indent, y, line)
                    y -= 14
                    line = word
                    first_line = False
                    if y < 1.0 * inch:
                        c.showPage()
                        y = height - 0.9 * inch
                        c.setFont("Helvetica", 11)
            if line:
                c.drawString(bullet_indent, y, line)
                y -= 14
            y -= 2

    c.showPage()
    c.save()

    buffer.seek(0)
    filename = "resume_preview.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



    





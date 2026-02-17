document.addEventListener("DOMContentLoaded", () => {
  const dissolve = document.getElementById("dissolve");

  // ==========================================
  // Helpers
  // ==========================================
  function showDissolve(on) {
    if (!dissolve) return;
    if (on) dissolve.classList.add("on");
    else dissolve.classList.remove("on");
  }

  function showBox(box, on) {
    if (!box) return;
    box.style.display = on ? "block" : "none";
  }

  function setList(ul, items) {
    if (!ul) return;
    ul.innerHTML = "";
    (items || []).forEach((t) => {
      const li = document.createElement("li");
      li.textContent = t;
      ul.appendChild(li);
    });
  }

  function setHidden(form, name, value) {
    if (!form) return;
    const el = form.querySelector(`input[name="${name}"]`);
    if (el) el.value = value ?? "";
  }

  // ==========================================
  // Dissolve on internal nav clicks
  // ==========================================
  document.querySelectorAll('a[href^="/"]').forEach((a) => {
    a.addEventListener("click", (e) => {
      const href = a.getAttribute("href");
      if (!href || href.startsWith("#")) return;
      showDissolve(true);
      setTimeout(() => (window.location.href = href), 160);
      e.preventDefault();
    });
  });

  // ==========================================
  // Resume Builder (existing)
  // ==========================================
  const builderForm = document.getElementById("resumeForm");
  const jobsWrap = document.getElementById("jobsWrap");
  const addJobBtn = document.getElementById("addJobBtn");
  const jobsJsonField =
    document.getElementById("jobs_json") || document.getElementById("jobsJson");

  const summaryEl = document.getElementById("summary");
  const winsEl = document.getElementById("wins");
  const skillsEl = document.getElementById("skills");
  const strengthsEl = document.getElementById("strengths");
  const targetTitleEl = document.getElementById("target_title");
  const yearsEl = document.getElementById("years_experience");

  const sugSummaryBox = document.getElementById("sugSummaryBox");
  const sugSummaryText = document.getElementById("sugSummaryText");
  const sugSummaryApply = document.getElementById("sugSummaryApply");

  const sugWinsBox = document.getElementById("sugWinsBox");
  const sugWinsList = document.getElementById("sugWinsList");
  const sugWinsApply = document.getElementById("sugWinsApply");

  const sugSkillsBox = document.getElementById("sugSkillsBox");
  const sugSkillsText = document.getElementById("sugSkillsText");
  const sugSkillsApply = document.getElementById("sugSkillsApply");

  const sugHint = document.getElementById("sugHint");

  // IMPORTANT: match your index.html checkbox id
  const autoApplyEl =
    document.getElementById("autoApplyToggle") || document.getElementById("autoApply");

  function autoApplyOn() {
    // If checkbox exists, obey it.
    // If it does NOT exist, default OFF (so nothing surprises users).
    if (!autoApplyEl) return false;
    return !!autoApplyEl.checked;
  }

  function splitBullets(text) {
    const raw = (text || "")
      .split("\n")
      .map((x) => x.trim())
      .filter(Boolean);
    return raw.slice(0, 8);
  }

  function syncJobsJson() {
    if (!jobsJsonField) return;
    if (!jobsWrap) {
      jobsJsonField.value = "[]";
      return;
    }

    const cards = jobsWrap.querySelectorAll(".job-card");
    const jobs = [];
    cards.forEach((card) => {
      const title = card.querySelector('[data-field="title"]')?.value || "";
      const company = card.querySelector('[data-field="company"]')?.value || "";
      const location = card.querySelector('[data-field="location"]')?.value || "";
      const dates = card.querySelector('[data-field="dates"]')?.value || "";
      const bulletsText = card.querySelector('[data-field="bullets"]')?.value || "";
      const bullets = splitBullets(bulletsText);

      if ((title + company + location + dates + bulletsText).trim().length > 0) {
        jobs.push({ title, company, location, dates, bullets });
      }
    });

    jobsJsonField.value = JSON.stringify(jobs.slice(0, 6));
  }

  function collectJobs() {
    if (!jobsWrap) return [];
    const cards = jobsWrap.querySelectorAll(".job-card");
    const jobs = [];
    cards.forEach((card) => {
      const title = card.querySelector('[data-field="title"]')?.value || "";
      const company = card.querySelector('[data-field="company"]')?.value || "";
      const location = card.querySelector('[data-field="location"]')?.value || "";
      const dates = card.querySelector('[data-field="dates"]')?.value || "";
      const bulletsText = card.querySelector('[data-field="bullets"]')?.value || "";

      if ((title + company + location + dates + bulletsText).trim().length > 0) {
        jobs.push({ title, company, location, dates, bullets_text: bulletsText });
      }
    });
    return jobs.slice(0, 6);
  }

  function makeJobCard(prefill = {}) {
    const card = document.createElement("div");
    card.className = "job-card";
    card.innerHTML = `
      <div class="job-top">
        <div class="job-titleline">Work Experience</div>
        <button type="button" class="btn ghost job-remove" aria-label="Remove job">Remove</button>
      </div>

      <div class="row">
        <div>
          <label>Job title</label>
          <input data-field="title" placeholder="Area Manager" value="${(prefill.title || "")}">
        </div>
        <div>
          <label>Company</label>
          <input data-field="company" placeholder="Amazon" value="${(prefill.company || "")}">
        </div>
      </div>

      <div class="row">
        <div>
          <label>Location</label>
          <input data-field="location" placeholder="Colorado Springs, CO" value="${(prefill.location || "")}">
        </div>
        <div>
          <label>Dates</label>
          <input data-field="dates" placeholder="2021 – 2024" value="${(prefill.dates || "")}">
        </div>
      </div>

      <label>Bullets</label>
      <textarea data-field="bullets" placeholder="One bullet per line. Keep it simple.">${(prefill.bullets || []).join("\n")}</textarea>

      <div class="divider"></div>
    `;

    const removeBtn = card.querySelector(".job-remove");
    removeBtn.addEventListener("click", () => {
      card.remove();
      syncJobsJson();
      requestResumePolish();
    });

    card.querySelectorAll("input, textarea").forEach((el) => {
      el.addEventListener("input", () => {
        syncJobsJson();
        requestResumePolishDebounced();
      });
    });

    return card;
  }

  if (jobsWrap && addJobBtn) {
    addJobBtn.addEventListener("click", () => {
      if (jobsWrap.querySelectorAll(".job-card").length >= 3) return;
      jobsWrap.appendChild(makeJobCard({}));
      syncJobsJson();
      requestResumePolish();
    });

    if (jobsWrap.querySelectorAll(".job-card").length === 0) {
      jobsWrap.appendChild(makeJobCard({}));
      syncJobsJson();
    }
  }

  if (builderForm) {
    builderForm.addEventListener("submit", () => {
      syncJobsJson();
      showDissolve(true);
    });
  }

  // ---- Resume polish ----
  let resumePolishTimer = null;
  let resumeAutoApplyTimer = null;

  function collectResumePayload() {
    return {
      target_title: targetTitleEl?.value || "",
      years_experience: yearsEl?.value || "",
      strengths: strengthsEl?.value || "",
      wins: winsEl?.value || "",
      summary: summaryEl?.value || "",
      skills: skillsEl?.value || "",
      jobs: collectJobs(),
    };
  }

  function scheduleAutoApplySummary(text) {
    if (!summaryEl) return;
    if (!autoApplyOn()) return;

    clearTimeout(resumeAutoApplyTimer);
    resumeAutoApplyTimer = setTimeout(() => {
      if ((text || "").trim().length === 0) return;
      summaryEl.value = text;
    }, 700);
  }

  async function requestResumePolish() {
    // if no resume fields exist, skip
    if (!summaryEl && !winsEl && !skillsEl && !jobsWrap) return;

    const payload = collectResumePayload();

    try {
      const res = await fetch("/polish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) return;
      const data = await res.json();

      const summarySuggested = (data.polished_summary || "").trim();
      const bullets = Array.isArray(data.bullets) ? data.bullets : [];
      const skillsSuggestedList = Array.isArray(data.skills_suggested) ? data.skills_suggested : [];
      const skillsSuggested = skillsSuggestedList.join(", ");

      if (sugSummaryText) {
        sugSummaryText.textContent = summarySuggested;
        showBox(sugSummaryBox, summarySuggested.length > 0);
      }

      if (sugWinsList) {
        setList(sugWinsList, bullets);
        showBox(sugWinsBox, bullets.length > 0);
      }

      if (sugSkillsText) {
        sugSkillsText.textContent = skillsSuggested;
        showBox(sugSkillsBox, skillsSuggested.trim().length > 0);
      }

      if (sugHint) {
        const hints = Array.isArray(data.metric_hints) ? data.metric_hints : [];
        sugHint.textContent = hints.length ? hints[0] : "";
      }

      if (summarySuggested && summaryEl) {
        scheduleAutoApplySummary(summarySuggested);
      }

      if (sugSummaryApply && summaryEl) {
        sugSummaryApply.onclick = () => {
          summaryEl.value = summarySuggested;
          requestResumePolish();
        };
      }

      if (sugWinsApply && winsEl) {
        sugWinsApply.onclick = () => {
          winsEl.value = bullets.join("\n");
          requestResumePolish();
        };
      }

      if (sugSkillsApply && skillsEl) {
        sugSkillsApply.onclick = () => {
          skillsEl.value = skillsSuggested;
          requestResumePolish();
        };
      }
    } catch (e) {
      console.error(e);
    }
  }

  function requestResumePolishDebounced() {
    clearTimeout(resumePolishTimer);
    resumePolishTimer = setTimeout(requestResumePolish, 380);
  }

  // bind resume inputs
  const listen = (el, fn) => {
    if (!el) return;
    el.addEventListener("input", fn);
  };
  listen(summaryEl, requestResumePolishDebounced);
  listen(winsEl, requestResumePolishDebounced);
  listen(skillsEl, requestResumePolishDebounced);
  listen(strengthsEl, requestResumePolishDebounced);
  listen(targetTitleEl, requestResumePolishDebounced);
  listen(yearsEl, requestResumePolishDebounced);

  // initial resume polish (only if on resume page)
  requestResumePolish();

  // ==========================================
  // Cover Letter page: polish + auto-apply
  // ==========================================
  const coverForm = document.getElementById("coverForm");
  const clPolishBtn = document.getElementById("clPolishBtn");

  const clFull = document.getElementById("cl_full_name");
  const clEmail = document.getElementById("cl_email");
  const clPhone = document.getElementById("cl_phone");

  const clCompany = document.getElementById("cl_company");
  const clManager = document.getElementById("cl_manager");
  const clRole = document.getElementById("cl_role");
  const clSource = document.getElementById("cl_source");

  const clStrengths = document.getElementById("cl_strengths");
  const clAch = document.getElementById("cl_achievements");
  const clWhy = document.getElementById("cl_why");
  const clClose = document.getElementById("cl_close");

  const clTone = document.getElementById("cl_tone");
  const clLetter = document.getElementById("cl_letter");

  const clAutoApply = document.getElementById("clAutoApplyToggle");
  function clAutoOn() {
    if (!clAutoApply) return false; // OFF by default
    return !!clAutoApply.checked;
  }

  const clSugBox = document.getElementById("clSugBox");
  const clSugText = document.getElementById("clSugText");
  const clSugApply = document.getElementById("clSugApply");

  let clPolishTimer = null;
  let clAutoTimer = null;

  function collectCoverPayload() {
    return {
      tone: clTone?.value || "confident",
      full_name: clFull?.value || "",
      email: clEmail?.value || "",
      phone: clPhone?.value || "",
      company_name: clCompany?.value || "",
      hiring_manager: clManager?.value || "",
      target_role: clRole?.value || "",
      job_source: clSource?.value || "",
      strengths: clStrengths?.value || "",
      achievements: clAch?.value || "",
      why_company: clWhy?.value || "",
      closing_note: clClose?.value || "",
      cover_letter: clLetter?.value || "",
    };
  }

  function scheduleClAutoApply(text) {
    if (!clLetter) return;
    if (!clAutoOn()) return;

    clearTimeout(clAutoTimer);
    clAutoTimer = setTimeout(() => {
      if ((text || "").trim().length === 0) return;
      clLetter.value = text;
    }, 650);
  }

  async function requestCoverPolish() {
    if (!clLetter && !clCompany && !clRole) return;

    const payload = collectCoverPayload();

    try {
      const res = await fetch("/polish_cover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) return;
      const data = await res.json();

      const suggested = (data.cover_letter_suggested || "").trim();

      if (clSugText) {
        clSugText.textContent = suggested;
        showBox(clSugBox, suggested.length > 0);
      }

      if (suggested && clLetter) {
        scheduleClAutoApply(suggested);
      }

      if (clSugApply && clLetter) {
        clSugApply.onclick = () => {
          clLetter.value = suggested;
          requestCoverPolish();
        };
      }
    } catch (e) {
      console.error(e);
    }
  }

  function requestCoverPolishDebounced() {
    clearTimeout(clPolishTimer);
    clPolishTimer = setTimeout(requestCoverPolish, 360);
  }

  // bind cover inputs (only if on cover page)
  if (coverForm) {
    [
      clFull, clEmail, clPhone,
      clCompany, clManager, clRole, clSource,
      clStrengths, clAch, clWhy, clClose,
      clTone, clLetter
    ].forEach((el) => {
      if (!el) return;
      el.addEventListener("input", requestCoverPolishDebounced);
      if (el === clTone) el.addEventListener("change", requestCoverPolishDebounced);
    });

    if (clPolishBtn) {
      clPolishBtn.addEventListener("click", () => requestCoverPolish());
    }

    // initial on cover page
    requestCoverPolish();
  }

  // ==========================================
  // Preview swap (resume) - keep your existing logic if you already use it
  // (This block is safe even if the elements do not exist on a page.)
  // ==========================================
  const templateSelect = document.getElementById("templateSwap");
  const fontSelect = document.getElementById("fontSwap");
  const pageLimitSelect = document.getElementById("pageLimit");
  const resultWrap = document.getElementById("resultWrap");
  const payloadForm = document.getElementById("swapPayload");
  const downloadForm = document.getElementById("downloadForm");

  function syncPreviewSettingsIntoForms() {
    const tpl = templateSelect ? templateSelect.value : null;
    const font = fontSelect ? fontSelect.value : null;
    const pages = pageLimitSelect ? pageLimitSelect.value : null;

    if (tpl) {
      setHidden(payloadForm, "template", tpl);
      setHidden(downloadForm, "template", tpl);
    }
    if (font) {
      setHidden(payloadForm, "font_family", font);
      setHidden(downloadForm, "font_family", font);
      if (resultWrap) resultWrap.setAttribute("data-font", font);
    }
    if (pages) {
      setHidden(payloadForm, "page_limit", pages);
      setHidden(downloadForm, "page_limit", pages);
    }
  }

  async function doSwap() {
    if (!payloadForm || !resultWrap) return;

    syncPreviewSettingsIntoForms();

    const formData = new FormData(payloadForm);
    const params = new URLSearchParams(formData);

    try {
      showDissolve(true);
      const response = await fetch(`/swap?${params.toString()}`);
      if (!response.ok) return;
      const html = await response.text();

      setTimeout(() => {
        resultWrap.innerHTML = html;
        showDissolve(false);
      }, 140);
    } catch (err) {
      console.error(err);
      showDissolve(false);
    }
  }

  if (templateSelect && resultWrap && payloadForm) templateSelect.addEventListener("change", doSwap);
  if (fontSelect && resultWrap && payloadForm) fontSelect.addEventListener("change", doSwap);
  if (pageLimitSelect) pageLimitSelect.addEventListener("change", syncPreviewSettingsIntoForms);

  if (downloadForm) {
    downloadForm.addEventListener("submit", () => {
      syncPreviewSettingsIntoForms();
      showDissolve(true);
      setTimeout(() => showDissolve(false), 240);
    });
  }

  syncPreviewSettingsIntoForms();
});







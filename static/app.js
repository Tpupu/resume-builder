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
  // Builder + fields
  // ==========================================
  const builderForm = document.getElementById("resumeForm");
  const jobsWrap = document.getElementById("jobsWrap");
  const addJobBtn = document.getElementById("addJobBtn");
  const jobsJsonField =
    document.getElementById("jobs_json") || document.getElementById("jobsJson");

  // fields we "mini-ai" polish (MUST MATCH your HTML IDs)
  const summaryEl = document.getElementById("summary");
  const winsEl = document.getElementById("wins");
  const skillsEl = document.getElementById("skills");
  const strengthsEl = document.getElementById("strengths");
  const targetTitleEl = document.getElementById("target_title");
  const yearsEl = document.getElementById("years_experience");

  // suggestion UI
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

  // ==========================================
  // Auto-apply toggle (default OFF, remember choice)
  // Supports id="autoApplyToggle" or id="autoApply"
  // ==========================================
  const autoApplyEl =
    document.getElementById("autoApplyToggle") || document.getElementById("autoApply");

  const AUTO_KEY = "rb_auto_apply_summary"; // localStorage key

  if (autoApplyEl) {
    // If nothing saved yet => default OFF
    const saved = localStorage.getItem(AUTO_KEY);
    autoApplyEl.checked = saved === "1";

    autoApplyEl.addEventListener("change", () => {
      localStorage.setItem(AUTO_KEY, autoApplyEl.checked ? "1" : "0");
    });
  }

  function autoApplyOn() {
    // If checkbox exists, obey it. If missing, OFF.
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

      <div class="sugbox" data-sug="job">
        <div class="sughead">
          <div class="sugtitle">Suggested bullets</div>
          <button type="button" class="btn primary sugapply">Apply</button>
        </div>
        <ul class="suglist"></ul>
      </div>

      <div class="divider"></div>
    `;

    const removeBtn = card.querySelector(".job-remove");
    removeBtn.addEventListener("click", () => {
      card.remove();
      syncJobsJson();
      requestPolish();
    });

    card.querySelectorAll("input, textarea").forEach((el) => {
      el.addEventListener("input", () => {
        syncJobsJson();
        requestPolishDebounced();
      });
    });

    return card;
  }

  if (jobsWrap && addJobBtn) {
    addJobBtn.addEventListener("click", () => {
      if (jobsWrap.querySelectorAll(".job-card").length >= 3) return;
      jobsWrap.appendChild(makeJobCard({}));
      syncJobsJson();
      requestPolish();
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

  // ==========================================
  // Mini-AI: live suggestions + AUTO APPLY
  // Endpoint returns: polished_summary, bullets, skills_suggested
  // ==========================================
  let polishTimer = null;
  let autoApplyTimer = null;

  function collectPayload() {
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

    clearTimeout(autoApplyTimer);
    autoApplyTimer = setTimeout(() => {
      if ((text || "").trim().length === 0) return;
      summaryEl.value = text;
    }, 900);
  }

  async function requestPolish() {
    if (!summaryEl && !winsEl && !skillsEl && !jobsWrap) return;

    const payload = collectPayload();

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

      if (jobsWrap) {
        const cards = jobsWrap.querySelectorAll(".job-card");
        const all = Array.isArray(data.jobs_suggestions) ? data.jobs_suggestions : [];
        cards.forEach((card, idx) => {
          const sugBox = card.querySelector('[data-sug="job"]');
          const ul = card.querySelector(".suglist");
          const applyBtn = card.querySelector(".sugapply");
          const textarea = card.querySelector('[data-field="bullets"]');

          const suggestions = Array.isArray(all[idx]) ? all[idx] : [];
          if (!sugBox || !ul || !applyBtn || !textarea) return;

          setList(ul, suggestions);
          showBox(sugBox, suggestions.length > 0);

          applyBtn.onclick = () => {
            textarea.value = suggestions.join("\n");
            syncJobsJson();
            requestPolish();
          };
        });
      }

      if (sugSummaryApply && summaryEl) {
        sugSummaryApply.onclick = () => {
          summaryEl.value = summarySuggested;
          requestPolish();
        };
      }

      if (sugWinsApply && winsEl) {
        sugWinsApply.onclick = () => {
          winsEl.value = bullets.join("\n");
          requestPolish();
        };
      }

      if (sugSkillsApply && skillsEl) {
        sugSkillsApply.onclick = () => {
          skillsEl.value = skillsSuggested;
          requestPolish();
        };
      }
    } catch (e) {
      console.error(e);
    }
  }

  function requestPolishDebounced() {
    clearTimeout(polishTimer);
    polishTimer = setTimeout(requestPolish, 420);
  }

  const listen = (el) => {
    if (!el) return;
    el.addEventListener("input", requestPolishDebounced);
  };
  listen(summaryEl);
  listen(winsEl);
  listen(skillsEl);
  listen(strengthsEl);
  listen(targetTitleEl);
  listen(yearsEl);

  requestPolish();

  // ==========================================
  // Preview: live swap + hidden sync
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

  if (templateSelect && resultWrap && payloadForm) {
    templateSelect.addEventListener("change", doSwap);
  }
  if (fontSelect && resultWrap && payloadForm) {
    fontSelect.addEventListener("change", doSwap);
  }
  if (pageLimitSelect) {
    pageLimitSelect.addEventListener("change", syncPreviewSettingsIntoForms);
  }

  if (downloadForm) {
    downloadForm.addEventListener("submit", () => {
      syncPreviewSettingsIntoForms();
      showDissolve(true);
      setTimeout(() => showDissolve(false), 240);
    });
  }

  syncPreviewSettingsIntoForms();
});






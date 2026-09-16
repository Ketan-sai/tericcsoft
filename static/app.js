// Nimbus Software Sales Lead Qualification Assistant
document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const form = document.getElementById("lead-form");
  const companyInput = document.getElementById("company_name");
  const emailInput = document.getElementById("contact_email");
  const requirementInput = document.getElementById("requirement");
  const charCounter = document.getElementById("char-counter");
  const clientError = document.getElementById("client-error");
  const submitBtn = document.getElementById("submit-btn");
  const loadingState = document.getElementById("loading-state");
  const errorState = document.getElementById("error-state");
  const errorMessage = document.getElementById("error-message");
  const resultSection = document.getElementById("result-section");
  const recentLeadsList = document.getElementById("recent-leads-list");
  const refreshLeadsBtn = document.getElementById("refresh-leads-btn");
  const toggleKbBtn = document.getElementById("toggle-kb-btn");
  const kbPanel = document.getElementById("kb-panel");
  const kbGrid = document.getElementById("kb-grid");
  const kbCountLabel = document.getElementById("kb-count-label");
  const backendStatus = document.getElementById("backend-status");

  // Sample Requirements
  const EXAMPLES = {
    support: {
      company: "Apex Global Logistics",
      email: "it-director@apexlogistics.com",
      text: "We're a 200-person logistics company. Our support team is drowning in tickets and we have no visibility into response times. We also need SSO because our IT team requires it."
    },
    sales: {
      company: "Starlight SaaS",
      email: "cro@starlight.io",
      text: "Looking to modernize our B2B outbound pipeline. We need lead scoring, automated drip email sequences, and CRM pipeline sync with deal stages for a team of 30 SDRs."
    },
    billing: {
      company: "Vortex Digital",
      email: "finance@vortexdigital.com",
      text: "We run an e-commerce subscription platform and need to handle recurring billing, usage-based invoicing, and automated tax calculation across Europe with GDPR compliance."
    }
  };

  // 1. Initial Data Fetching
  checkHealth();
  loadRecentLeads();

  // 2. Event Listeners for Example Buttons
  document.querySelectorAll(".btn-chip").forEach((button) => {
    button.addEventListener("click", () => {
      const exampleKey = button.getAttribute("data-example");
      const data = EXAMPLES[exampleKey];
      if (data) {
        requirementInput.value = data.text;
        companyInput.value = data.company;
        emailInput.value = data.email;
        updateCharCounter();
        clearErrors();
        requirementInput.focus();
      }
    });
  });

  // 3. Live Character Counter
  requirementInput.addEventListener("input", updateCharCounter);

  function updateCharCounter() {
    const len = requirementInput.value.length;
    charCounter.textContent = `${len} / 2000 chars (min 15 required)`;
    if (len >= 15 && len <= 2000) {
      charCounter.className = "char-counter valid";
    } else if (len > 0) {
      charCounter.className = "char-counter limit-warn";
    } else {
      charCounter.className = "char-counter";
    }
  }

  // 4. Knowledge Base Toggle
  let kbLoaded = false;
  toggleKbBtn.addEventListener("click", () => {
    const isHidden = kbPanel.classList.contains("hidden");
    if (isHidden) {
      kbPanel.classList.remove("hidden");
      toggleKbBtn.textContent = "✖ Close Knowledge Base";
      if (!kbLoaded) {
        fetchKnowledgeBase();
      }
    } else {
      kbPanel.classList.add("hidden");
      toggleKbBtn.textContent = `📚 Browse Knowledge Base (${kbCountLabel.textContent})`;
    }
  });

  refreshLeadsBtn.addEventListener("click", () => {
    loadRecentLeads();
  });

  // 5. Form Submission
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearErrors();

    const requirement = requirementInput.value.trim();
    const company_name = companyInput.value.trim() || null;
    const contact_email = emailInput.value.trim() || null;

    // Inline Client-side Validation
    if (requirement.length < 15) {
      showInlineError("Customer requirement must be at least 15 characters long.");
      requirementInput.focus();
      return;
    }

    if (requirement.length > 2000) {
      showInlineError("Customer requirement cannot exceed 2000 characters.");
      requirementInput.focus();
      return;
    }

    if (contact_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact_email)) {
      showInlineError("Please provide a valid contact email address.");
      emailInput.focus();
      return;
    }

    // Set Loading State
    setLoading(true);

    try {
      const response = await fetch("/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requirement, company_name, contact_email })
      });

      const data = await response.json();

      if (!response.ok) {
        let msg = "Failed to analyze lead.";
        if (response.status === 422 && data.detail) {
          // Format validation errors
          if (Array.isArray(data.detail)) {
            msg = data.detail.map(d => `${d.loc.slice(-1)}: ${d.msg}`).join(" | ");
          } else {
            msg = JSON.stringify(data.detail);
          }
        } else if (data.detail) {
          msg = data.detail;
        }
        showErrorBox(msg);
        return;
      }

      // Success: render lead analysis
      renderLeadResult(data);
      // Refresh recent leads
      loadRecentLeads();
    } catch (err) {
      showErrorBox(`Network or server connection error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  });

  // 6. UI Render Helpers
  function renderLeadResult(lead) {
    resultSection.classList.remove("hidden");

    // Title & Meta
    const companyTitle = lead.company_name ? lead.company_name : "Inbound Lead";
    document.getElementById("result-company-title").textContent = companyTitle;
    const emailMeta = lead.contact_email ? ` • ${lead.contact_email}` : "";
    const createdStr = new Date(lead.created_at).toLocaleString();
    document.getElementById("result-meta").textContent = `Analyzed on ${createdStr}${emailMeta}`;

    // Score & Priority Pill
    const scoreVal = lead.lead_score != null ? lead.lead_score : 0;
    document.getElementById("result-score").textContent = scoreVal;

    const priorityPill = document.getElementById("result-priority-pill");
    const priority = (lead.priority || "Medium").toLowerCase();
    priorityPill.textContent = lead.priority || "Medium";
    priorityPill.className = `priority-pill priority-${priority}`;

    // Summary
    document.getElementById("result-summary").textContent = lead.lead_summary || "No summary provided.";

    // Relevant Products
    const productsContainer = document.getElementById("result-products");
    productsContainer.innerHTML = "";
    const products = parseJsonIfString(lead.relevant_products, []);
    if (products.length === 0) {
      productsContainer.innerHTML = `<p class="text-muted">No specific product matches identified.</p>`;
    } else {
      products.forEach((prod) => {
        const item = document.createElement("div");
        item.className = "product-item";
        item.innerHTML = `
          <div class="product-name">${escapeHtml(prod.name || "Product")}</div>
          <div class="product-why">${escapeHtml(prod.why || "")}</div>
        `;
        productsContainer.appendChild(item);
      });
    }

    // Customer Needs
    const needsContainer = document.getElementById("result-needs");
    needsContainer.innerHTML = "";
    const needs = parseJsonIfString(lead.customer_needs, []);
    needs.forEach((need) => {
      const li = document.createElement("li");
      li.textContent = need;
      needsContainer.appendChild(li);
    });

    // Next Step
    document.getElementById("result-next-step").textContent = lead.recommended_next_step || "Follow up with customer to explore requirements.";

    // Follow-up Questions
    const questionsContainer = document.getElementById("result-questions");
    questionsContainer.innerHTML = "";
    const questions = parseJsonIfString(lead.follow_up_questions, []);
    questions.forEach((q) => {
      const li = document.createElement("li");
      li.textContent = q;
      questionsContainer.appendChild(li);
    });

    // Retrieved KB Context
    const retrieved = parseJsonIfString(lead.retrieved_context, []);
    document.getElementById("retrieved-count").textContent = retrieved.length;
    const retrievedItems = document.getElementById("retrieved-items");
    retrievedItems.innerHTML = "";

    retrieved.forEach((item) => {
      const div = document.createElement("div");
      div.className = "retrieved-item";
      const score = item.relevance_score != null ? (item.relevance_score * 100).toFixed(1) + "% match" : "Retrieved";
      div.innerHTML = `
        <div class="retrieved-top">
          <span class="retrieved-title">${escapeHtml(item.name || "Product")} <small>(${escapeHtml(item.category || "")})</small></span>
          <span class="score-badge">${score}</span>
        </div>
        <div class="retrieved-desc">${escapeHtml(item.description || "")}</div>
      `;
      retrievedItems.appendChild(div);
    });

    // Scroll smoothly to results
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // 7. Recent Leads List
  async function loadRecentLeads() {
    try {
      const response = await fetch("/api/leads?limit=20");
      if (!response.ok) throw new Error("Failed to load leads");
      const leads = await response.json();

      if (leads.length === 0) {
        recentLeadsList.innerHTML = `<p class="empty-state">No leads qualified yet. Submit the form above to qualify your first lead.</p>`;
        return;
      }

      recentLeadsList.innerHTML = "";
      leads.forEach((lead) => {
        const row = document.createElement("div");
        row.className = "lead-row";

        const title = lead.company_name ? lead.company_name : "Unnamed Company";
        const priority = (lead.priority || "Medium").toLowerCase();
        const dateStr = new Date(lead.created_at).toLocaleDateString(undefined, {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit"
        });

        row.innerHTML = `
          <div class="lead-row-header" tabindex="0">
            <div class="lead-row-main">
              <span class="lead-row-title">${escapeHtml(title)} <small class="text-muted">(${dateStr})</small></span>
              <span class="lead-row-preview">${escapeHtml(lead.requirement)}</span>
            </div>
            <div class="lead-row-meta">
              <span class="lead-row-score">Score: ${lead.lead_score}</span>
              <span class="priority-pill priority-${priority}">${lead.priority}</span>
            </div>
          </div>
          <div class="lead-row-details hidden">
            <div><strong>Summary:</strong> ${escapeHtml(lead.lead_summary)}</div>
            <div><strong>Next Step:</strong> ${escapeHtml(lead.recommended_next_step)}</div>
            <button type="button" class="btn btn-secondary btn-sm load-full-lead-btn" style="margin-top: 6px;">View Full Analysis</button>
          </div>
        `;

        const header = row.querySelector(".lead-row-header");
        const details = row.querySelector(".lead-row-details");
        header.addEventListener("click", () => {
          details.classList.toggle("hidden");
        });

        const loadBtn = row.querySelector(".load-full-lead-btn");
        loadBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          renderLeadResult(lead);
        });

        recentLeadsList.appendChild(row);
      });
    } catch (err) {
      recentLeadsList.innerHTML = `<p class="empty-state">Unable to load recent leads (${err.message}).</p>`;
    }
  }

  // 8. Knowledge Base Fetching
  async function fetchKnowledgeBase() {
    try {
      kbGrid.innerHTML = "Loading knowledge base...";
      const res = await fetch("/api/knowledge-base");
      if (!res.ok) throw new Error("Could not load knowledge base");
      const products = await res.json();
      kbLoaded = true;

      kbCountLabel.textContent = `${products.length} Products`;
      kbGrid.innerHTML = "";

      products.forEach((prod) => {
        const card = document.createElement("div");
        card.className = "kb-card";
        const features = (prod.features || []).slice(0, 3).join(", ");
        card.innerHTML = `
          <div class="kb-card-header">
            <span class="kb-card-name">${escapeHtml(prod.name)}</span>
            <span class="kb-card-category">${escapeHtml(prod.category)}</span>
          </div>
          <div class="kb-card-desc">${escapeHtml(prod.description)}</div>
          <div class="kb-card-features"><strong>Features:</strong> ${escapeHtml(features)}</div>
        `;
        kbGrid.appendChild(card);
      });
    } catch (err) {
      kbGrid.innerHTML = `<p class="inline-error">Failed to load products: ${err.message}</p>`;
    }
  }

  // 9. Health Check
  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error("Health check failed");
      const data = await res.json();
      backendStatus.textContent = `● Online (${data.kb_entries} products indexed, ${data.model})`;
      backendStatus.style.color = "var(--success)";
      kbCountLabel.textContent = `${data.kb_entries} Products`;
    } catch (err) {
      backendStatus.textContent = "● Offline (check server)";
      backendStatus.style.color = "var(--danger)";
    }
  }

  // State Helpers
  function setLoading(isLoading) {
    if (isLoading) {
      submitBtn.disabled = true;
      submitBtn.querySelector(".btn-text").textContent = "Analyzing...";
      loadingState.classList.remove("hidden");
      errorState.classList.add("hidden");
    } else {
      submitBtn.disabled = false;
      submitBtn.querySelector(".btn-text").textContent = "Analyze Lead";
      loadingState.classList.add("hidden");
    }
  }

  function showInlineError(msg) {
    clientError.textContent = msg;
    clientError.classList.remove("hidden");
  }

  function showErrorBox(msg) {
    errorMessage.textContent = msg;
    errorState.classList.remove("hidden");
    errorState.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function clearErrors() {
    clientError.textContent = "";
    clientError.classList.add("hidden");
    errorState.classList.add("hidden");
    errorMessage.textContent = "";
  }

  function parseJsonIfString(val, fallback) {
    if (Array.isArray(val) || (typeof val === "object" && val !== null)) return val;
    if (!val) return fallback;
    try {
      return JSON.parse(val);
    } catch {
      return fallback;
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});

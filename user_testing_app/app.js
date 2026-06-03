/* ==========================================================================
   Dashboard Ranker Application Logic (Interactive Tier List & Realtime Stats)
   ========================================================================== */

// 1. Initialize Supabase
const SUPABASE_URL = "https://ovwktjjeoowlktdfbuuu.supabase.co";
const SUPABASE_KEY = "sb_publishable_B2pz5WTA3UEVUeKACIgmBw_8_r0S3kU";
const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

// 2. Data Definitions (Anonymous to user during ranking, revealed at end)
const DASHBOARDS = [
    {
        id: "py-ds-v4-pro-skills",
        name: "Dashboard 1",
        model: "DeepSeek V4 Pro",
        arm: "skills",
        url: "assets/deepseek-v4-pro-skills.png",
        cost: 0.1038,
        time: 508,
        iterations: 1,
        passed: true,
        framework: "python"
    },
    {
        id: "py-claude-opus-skills",
        name: "Dashboard 2",
        model: "Claude Opus 4-8",
        arm: "skills",
        url: "assets/claude-opus-4-8-skills.png",
        cost: 1.4623,
        time: 309,
        iterations: 1,
        passed: true,
        framework: "python"
    },
    {
        id: "py-ds-v4-flash-skills",
        name: "Dashboard 3",
        model: "DeepSeek V4 Flash",
        arm: "skills",
        url: "assets/deepseek-v4-flash-skills.png",
        cost: 0.0127,
        time: 270,
        iterations: 1,
        passed: true,
        framework: "python"
    },
    {
        id: "py-gpt-5-5-skills",
        name: "Dashboard 4",
        model: "GPT 5.5",
        arm: "skills",
        url: "assets/gpt-5.5-skills.png",
        cost: 0.4274,
        time: 196,
        iterations: 1,
        passed: true,
        framework: "python"
    },
    {
        id: "py-minimax-m3-skills",
        name: "Dashboard 5",
        model: "Minimax M3",
        arm: "skills",
        url: "assets/minimax-m3-skills.png",
        cost: 0.1037,
        time: 519,
        iterations: 2,
        passed: true,
        framework: "python"
    },
    {
        id: "py-qwen-max-skills",
        name: "Dashboard 6",
        model: "Qwen 3.7 Max",
        arm: "skills",
        url: "assets/qwen3.7-max-skills.png",
        cost: 0.5410,
        time: 261,
        iterations: 1,
        passed: true,
        framework: "python"
    },
    {
        id: "py-ds-v4-pro-vanilla",
        name: "Dashboard 7",
        model: "DeepSeek V4 Pro",
        arm: "vanilla",
        url: "assets/deepseek-v4-pro-vanilla.png",
        cost: 0.0862,
        time: 570,
        iterations: 1,
        passed: true,
        framework: "python"
    },
    {
        id: "py-claude-opus-vanilla",
        name: "Dashboard 8",
        model: "Claude Opus 4-8",
        arm: "vanilla",
        url: "assets/claude-opus-4-8-vanilla.png",
        cost: 0.4908,
        time: 142,
        iterations: 1,
        passed: true,
        framework: "python"
    },
    {
        id: "py-ds-v4-flash-vanilla",
        name: "Dashboard 9",
        model: "DeepSeek V4 Flash",
        arm: "vanilla",
        url: "assets/deepseek-v4-flash-vanilla.png",
        cost: 0.0020,
        time: 92,
        iterations: 1,
        passed: true,
        framework: "python"
    },
    {
        id: "r-claude-opus-skills",
        name: "Dashboard 10",
        model: "Claude Opus 4-8",
        arm: "skills",
        url: "assets/r-claude-opus-4-8-skills.png",
        cost: 0.5229,
        time: 188,
        iterations: 1,
        passed: true,
        framework: "r"
    },
    {
        id: "r-ds-v4-flash-skills",
        name: "Dashboard 11",
        model: "DeepSeek V4 Flash",
        arm: "skills",
        url: "assets/r-deepseek-v4-flash-skills.png",
        cost: 0.0043,
        time: 133,
        iterations: 1,
        passed: true,
        framework: "r"
    },
    {
        id: "r-ds-v4-pro-skills",
        name: "Dashboard 12",
        model: "DeepSeek V4 Pro",
        arm: "skills",
        url: "assets/r-deepseek-v4-pro-skills.png",
        cost: 0.0467,
        time: 277,
        iterations: 1,
        passed: true,
        framework: "r"
    },
    {
        id: "r-gpt-5-5-skills",
        name: "Dashboard 13",
        model: "GPT 5.5",
        arm: "skills",
        url: "assets/r-gpt-5.5-skills.png",
        cost: 0.5972,
        time: 267,
        iterations: 1,
        passed: true,
        framework: "r"
    },
    {
        id: "r-minimax-m3-skills",
        name: "Dashboard 14",
        model: "Minimax M3",
        arm: "skills",
        url: "assets/r-minimax-m3-skills.png",
        cost: 0.0869,
        time: 415,
        iterations: 2,
        passed: true,
        framework: "r"
    },
    {
        id: "r-qwen-max-skills",
        name: "Dashboard 15",
        model: "Qwen 3.7 Max",
        arm: "skills",
        url: "assets/r-qwen3.7-max-skills.png",
        cost: 0.2984,
        time: 116,
        iterations: 1,
        passed: true,
        framework: "r"
    },
    {
        id: "r-claude-opus-vanilla",
        name: "Dashboard 16",
        model: "Claude Opus 4-8",
        arm: "vanilla",
        url: "assets/r-claude-opus-4-8-vanilla.png",
        cost: 0.4266,
        time: 123,
        iterations: 1,
        passed: true,
        framework: "r"
    },
    {
        id: "r-ds-v4-flash-vanilla",
        name: "Dashboard 17",
        model: "DeepSeek V4 Flash",
        arm: "vanilla",
        url: "assets/r-deepseek-v4-flash-vanilla.png",
        cost: 0.0029,
        time: 129,
        iterations: 1,
        passed: true,
        framework: "r"
    },
    {
        id: "r-ds-v4-pro-vanilla",
        name: "Dashboard 18",
        model: "DeepSeek V4 Pro",
        arm: "vanilla",
        url: "assets/r-deepseek-v4-pro-vanilla.png",
        cost: 0.0905,
        time: 603,
        iterations: 1,
        passed: true,
        framework: "r"
    },
    {
        id: "r-gpt-5-5-vanilla",
        name: "Dashboard 19",
        model: "GPT 5.5",
        arm: "vanilla",
        url: "assets/r-gpt-5.5-vanilla.png",
        cost: 0.4408,
        time: 203,
        iterations: 1,
        passed: true,
        framework: "r"
    },
    {
        id: "r-minimax-m3-vanilla",
        name: "Dashboard 20",
        model: "Minimax M3",
        arm: "vanilla",
        url: "assets/r-minimax-m3-vanilla.png",
        cost: 0.0247,
        time: 163,
        iterations: 1,
        passed: true,
        framework: "r"
    },
    {
        id: "r-qwen-max-vanilla",
        name: "Dashboard 21",
        model: "Qwen 3.7 Max",
        arm: "vanilla",
        url: "assets/r-qwen3.7-max-vanilla.png",
        cost: 0.1523,
        time: 103,
        iterations: 1,
        passed: true,
        framework: "r"
    }
];

const PRESET_TAGS = [
    "Clean Layout", "Jarring Colors", "Interactive Controls",
    "Confusing Chart", "Incorrect Data", "Very Basic",
    "Beautiful Map", "Failed to Render", "Rainbow Plots",
    "Text Overlap", "Great Colors", "Clear Labels"
];

// Tier scoring system for stats
const TIER_SCORES = { "S": 5, "A": 4, "B": 3, "C": 2, "D": 1 };

// 3. Application State Variables
let sessionId = uuidv4();
let selectedDashboardId = null;
let assignedTiers = {}; // dashboardId -> 'S'|'A'|'B'|'C'|'D'
let assignedTags = {};  // dashboardId -> Array of 2 strings
let tempTargetTier = null;
let currentLightboxDbId = null;

// DOM Elements
const welcomeView = document.getElementById("welcome-view");
const boardView = document.getElementById("board-view");
const summaryView = document.getElementById("summary-view");
const feedbackModal = document.getElementById("feedback-modal");

const poolZone = document.getElementById("pool-zone");
const poolCount = document.getElementById("pool-count");
const btnStartEvaluation = document.getElementById("btn-start-evaluation");
const btnSubmitTiers = document.getElementById("btn-submit-tiers");
const btnSaveTags = document.getElementById("btn-save-tags");
const btnRestart = document.getElementById("btn-restart");

const tagSelectionGrid = document.getElementById("tag-selection-grid");
const revealedTiersContainer = document.getElementById("revealed-tiers-container");
const communityBarsContainer = document.getElementById("community-bars-container");

// Lightbox
const lightboxModal = document.getElementById("lightbox-modal");
const lightboxImg = document.getElementById("lightbox-img");
const lightboxCaption = document.getElementById("lightbox-caption");
const lightboxClose = document.querySelector(".lightbox-close");

// Generate unique session ID
function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// 4. Initialize Board UI
function initializeBoard() {
    poolZone.innerHTML = "";
    // Clear zones
    document.querySelectorAll(".tier-dropzone").forEach(zone => zone.innerHTML = "");
    assignedTiers = {};
    assignedTags = {};
    selectedDashboardId = null;
    btnSubmitTiers.disabled = true;
    
    const qualCard = document.getElementById("qualitative-feedback-card");
    if (qualCard) qualCard.style.display = "none";
    const topReasonInput = document.getElementById("input-top-reason");
    const bottomReasonInput = document.getElementById("input-bottom-reason");
    if (topReasonInput) topReasonInput.value = "";
    if (bottomReasonInput) bottomReasonInput.value = "";

    DASHBOARDS.forEach(db => {
        const card = document.createElement("div");
        card.className = "thumbnail-card";
        card.id = `card-${db.id}`;
        card.draggable = true;
        card.dataset.id = db.id;

        card.innerHTML = `
            <img src="${db.url}" alt="${db.name}" draggable="false">
            <div class="card-label-tag">${db.name}</div>
            <div class="card-overlay-actions">
                <button class="mini-zoom-btn-pool" title="Zoom in"><i class="fa-solid fa-magnifying-glass-plus"></i> Zoom</button>
                <div class="card-placed-actions">
                    <button class="mini-action-btn zoom-placed-btn" title="Zoom in"><i class="fa-solid fa-expand"></i></button>
                </div>
            </div>
        `;

        card.addEventListener("click", (e) => {
            openLightbox(db.id);
            e.stopPropagation();
        });

        // HTML5 Drag and Drop events
        card.addEventListener("dragstart", (e) => {
            e.dataTransfer.setData("text/plain", db.id);
            selectCard(db.id);
        });

        poolZone.appendChild(card);
    });

    updatePoolCount();
}

function selectCard(dbId) {
    document.querySelectorAll(".thumbnail-card").forEach(c => c.classList.remove("selected"));
    selectedDashboardId = dbId;
    const selectedCard = document.getElementById(`card-${dbId}`);
    if (selectedCard) selectedCard.classList.add("selected");
}

function updatePoolCount() {
    const unrankedCount = DASHBOARDS.length - Object.keys(assignedTiers).length;
    poolCount.innerText = `${unrankedCount} item${unrankedCount === 1 ? "" : "s"} left`;
}

// Setup drop zones click handlers and dragover events
document.querySelectorAll(".tier-row").forEach(row => {
    const tier = row.dataset.tier;
    const zone = row.querySelector(".tier-dropzone");

    // Click row target handler
    row.addEventListener("click", () => {
        if (selectedDashboardId) {
            placeCard(selectedDashboardId, tier);
        }
    });

    // Drag-and-drop logic
    zone.addEventListener("dragover", (e) => {
        e.preventDefault();
        zone.classList.add("dragover");
    });

    zone.addEventListener("dragleave", () => {
        zone.classList.remove("dragover");
    });

    zone.addEventListener("drop", (e) => {
        e.preventDefault();
        zone.classList.remove("dragover");
        const dbId = e.dataTransfer.getData("text/plain");
        if (dbId) {
            placeCard(dbId, tier);
        }
    });
});

// Pool drop support
poolZone.addEventListener("dragover", (e) => e.preventDefault());
poolZone.addEventListener("drop", (e) => {
    e.preventDefault();
    const dbId = e.dataTransfer.getData("text/plain");
    if (dbId && assignedTiers[dbId]) {
        // Move back to pool (unassign)
        const card = document.getElementById(`card-${dbId}`);
        poolZone.appendChild(card);
        delete assignedTiers[dbId];
        delete assignedTags[dbId];
        updatePoolCount();
        checkIfComplete();
    }
});

// 5. Direct Placement & Feedback Tags Review Logic (Option A)
function placeCard(dbId, tier) {
    assignedTiers[dbId] = tier;
    if (!assignedTags[dbId]) {
        assignedTags[dbId] = [];
    }

    const card = document.getElementById(`card-${dbId}`);
    const dropzone = document.getElementById(`zone-${tier}`);
    if (card && dropzone) {
        dropzone.appendChild(card);
        card.classList.remove("selected");
    }

    selectedDashboardId = null;
    updatePoolCount();
    checkIfComplete();
    triggerGradePopup(tier);
}

function checkIfComplete() {
    const rankedCount = Object.keys(assignedTiers).length;
    const qualCard = document.getElementById("qualitative-feedback-card");
    if (rankedCount >= 4) {
        if (qualCard) qualCard.style.display = "block";
        renderDynamicReviews();
    } else {
        if (qualCard) qualCard.style.display = "none";
        btnSubmitTiers.disabled = true;
    }
}

function getFeedbackTargets() {
    const tiersOrder = ["S", "A", "B", "C", "D"];
    let topDb = null;
    for (const tier of tiersOrder) {
        const dbs = DASHBOARDS.filter(db => assignedTiers[db.id] === tier);
        if (dbs.length > 0) {
            topDb = dbs[0];
            break;
        }
    }
    let bottomDb = null;
    for (const tier of [...tiersOrder].reverse()) {
        const dbs = DASHBOARDS.filter(db => assignedTiers[db.id] === tier);
        if (dbs.length > 0) {
            bottomDb = dbs[0];
            break;
        }
    }
    if (topDb && bottomDb && topDb.id === bottomDb.id) {
        const tier = assignedTiers[topDb.id];
        const dbs = DASHBOARDS.filter(db => assignedTiers[db.id] === tier);
        if (dbs.length > 1) {
            bottomDb = dbs[1];
        }
    }
    const targets = [];
    if (topDb) targets.push(topDb);
    if (bottomDb && bottomDb.id !== topDb.id) targets.push(bottomDb);
    return targets;
}

function renderDynamicReviews() {
    const dynamicList = document.getElementById("dynamic-reviews-list");
    if (!dynamicList) return;
    dynamicList.innerHTML = "";

    const targets = getFeedbackTargets();

    const topDb = targets[0];
    const topTier = topDb ? assignedTiers[topDb.id] : "S";
    const labelTopReason = document.getElementById("label-top-reason");
    if (labelTopReason) {
        labelTopReason.innerText = `Why did you rank your ${topTier}-Tier dashboard(s) highly?`;
    }

    const bottomDb = targets.length > 1 ? targets[1] : null;
    const bottomTier = bottomDb ? assignedTiers[bottomDb.id] : "D";
    const labelBottomReason = document.getElementById("label-bottom-reason");
    if (labelBottomReason) {
        labelBottomReason.innerText = `What made your ${bottomTier}-Tier dashboard(s) fail?`;
    }

    if (targets.length === 0) {
        dynamicList.innerHTML = `<div style="font-size: 13px; color: var(--text-muted); font-style: italic; padding: 12px; text-align: center;">No dashboards placed. Ready to submit!</div>`;
        btnSubmitTiers.disabled = false;
        return;
    }

    targets.forEach(db => {
        const tier = assignedTiers[db.id];
        const container = document.createElement("div");
        container.className = "glass-subcard";
        container.style.padding = "16px";
        container.style.display = "flex";
        container.style.flexDirection = "column";
        container.style.gap = "10px";

        const labelClass = tier.toLowerCase() + "-tier";
        container.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span class="tier-label ${labelClass}" style="width: auto; min-height: auto; padding: 4px 10px; border-radius: 6px; font-weight: bold; color: #111; font-size: 11px; text-transform: uppercase;">${tier} Tier</span>
                    <span style="font-size: 13px; font-weight: 600; color: var(--text-main);">${db.name} (Anonymous)</span>
                </div>
                <button class="zoom-btn" style="width:22px; height:22px; font-size:9px;" title="Zoom in"><i class="fa-solid fa-expand"></i></button>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 2px;">Select exactly 2 tags to describe this layout:</div>
            <div class="tag-selection-grid" style="margin: 0; gap: 8px;"></div>
        `;

        container.querySelector(".zoom-btn").addEventListener("click", () => openLightbox(db.url, db.name));

        const grid = container.querySelector(".tag-selection-grid");
        if (!assignedTags[db.id]) assignedTags[db.id] = [];

        PRESET_TAGS.forEach(tag => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "tag-btn";
            if (assignedTags[db.id].includes(tag)) btn.classList.add("active");
            btn.innerText = tag;

            btn.addEventListener("click", () => {
                let tags = assignedTags[db.id] || [];
                if (btn.classList.contains("active")) {
                    btn.classList.remove("active");
                    tags = tags.filter(t => t !== tag);
                } else {
                    if (tags.length < 2) {
                        btn.classList.add("active");
                        tags.push(tag);
                    } else if (tags.length === 2) {
                        const first = tags.shift();
                        grid.querySelectorAll(".tag-btn").forEach(b => {
                            if (b.innerText === first) b.classList.remove("active");
                        });
                        btn.classList.add("active");
                        tags.push(tag);
                    }
                }
                assignedTags[db.id] = tags;
                validateSubmission();
            });

            grid.appendChild(btn);
        });

        dynamicList.appendChild(container);
    });

    validateSubmission();
}

function validateSubmission() {
    const targets = getFeedbackTargets();
    const valid = targets.every(db => assignedTags[db.id] && assignedTags[db.id].length === 2);
    btnSubmitTiers.disabled = !valid;
}

// 6. Supabase Commit & Realtime Results
btnSubmitTiers.addEventListener("click", async () => {
    btnSubmitTiers.disabled = true;
    btnSubmitTiers.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Submitting...`;

    const topReason = document.getElementById("input-top-reason")?.value.trim() || "";
    const bottomReason = document.getElementById("input-bottom-reason")?.value.trim() || "";

    // Package records
    const rankedIds = Object.keys(assignedTiers);
    const records = DASHBOARDS
        .filter(db => rankedIds.includes(db.id))
        .map(db => {
            const feedback = assignedTags[db.id] && assignedTags[db.id].length === 2 ? assignedTags[db.id].join(", ") : "";
            return {
                session_id: sessionId,
                dashboard_id: db.id,
                model: db.model,
                arm: db.arm,
                tier: assignedTiers[db.id],
                feedback_words: feedback,
                top_reason: topReason,
                bottom_reason: bottomReason,
                framework: db.framework || "python"
            };
        });

    // Optimistic flow: immediately reveal results without blocking UX
    revealResults();

    // Insert records in the background
    supabaseClient
        .from("dashboard_tiered_rankings_python")
        .insert(records)
        .then(({ error }) => {
            if (error) {
                console.error("Supabase background submission error:", error);
            }
        })
        .catch(err => {
            console.error("Supabase background insertion failed:", err);
        });
});

// 7. Results Page Presentation
function revealResults() {
    boardView.style.display = "none";
    summaryView.classList.add("active-view");

    // Clear previous elements
    revealedTiersContainer.innerHTML = "";

    // Show revealed tier ranks
    const tiers = ["S", "A", "B", "C", "D"];
    tiers.forEach(tier => {
        const tierDbs = DASHBOARDS.filter(db => assignedTiers[db.id] === tier);
        if (tierDbs.length === 0) return;

        const block = document.createElement("div");
        block.className = "results-tier-block";

        const headerClass = tier.toLowerCase() + "-tier";
        block.innerHTML = `
            <div class="results-tier-header ${headerClass}">
                <span>${tier} Tier</span>
            </div>
            <div class="results-tier-body"></div>
        `;

        const body = block.querySelector(".results-tier-body");

        tierDbs.forEach(db => {
            const card = document.createElement("div");
            card.className = "reveal-card";
            
            const costStr = `$${db.cost.toFixed(4)}`;

            card.innerHTML = `
                <div class="reveal-img-wrapper">
                    <img src="${db.url}" alt="${db.name}">
                </div>
                <div class="reveal-details">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                        <span class="reveal-title">${db.model} (${db.name})</span>
                        <div class="reveal-badges">
                            ${db.arm === 'skills' 
                                ? `<span class="reveal-badge reveal-badge-skills" title="Skills Arm: Built with structured dashboard styling, reactive design, and map guidelines."><i class="fa-solid fa-graduation-cap"></i> Skills</span>`
                                : `<span class="reveal-badge reveal-badge-vanilla" title="Vanilla Arm: Built with plain/raw LLM prompts without guidelines or best practices."><i class="fa-solid fa-whiskey-glass"></i> Vanilla</span>`
                            }
                            ${db.passed 
                                ? `<span class="reveal-badge reveal-badge-pass" title="Passed automated Shiny rendering validation."><i class="fa-solid fa-circle-check"></i> Passed</span>`
                                : `<span class="reveal-badge reveal-badge-fail" title="Failed automated Shiny rendering validation."><i class="fa-solid fa-circle-xmark"></i> Failed</span>`
                            }
                        </div>
                    </div>
                    <div class="reveal-meta-row" style="display: flex; gap: 14px; font-size: 11px; color: var(--text-muted); margin: 4px 0 6px 0;">
                        <span><i class="fa-solid fa-money-bill-wave" style="color: #059669;"></i> <strong>Cost:</strong> ${costStr}</span>
                        <span><i class="fa-solid fa-clock" style="color: #2563eb;"></i> <strong>Time:</strong> ${db.time}s</span>
                        <span><i class="fa-solid fa-arrows-spin" style="color: #7c3aed;"></i> <strong>Iterations:</strong> ${db.iterations}</span>
                    </div>
                    <div class="reveal-tags">
                        ${(assignedTags[db.id] || []).map(t => `<span class="reveal-tag">${t}</span>`).join("")}
                    </div>
                </div>
            `;
            
            card.addEventListener("click", () => openLightbox(db.url, `${db.model} (${db.name})`));
            body.appendChild(card);
        });

        revealedTiersContainer.appendChild(block);
    });

    // Populate Community Stats and Subscribe Realtime
    fetchCommunityStats();
    subscribeRealtime();
}

async function fetchCommunityStats() {
    try {
        const { data, error } = await supabaseClient
            .from("dashboard_tiered_rankings_python")
            .select("model, arm, tier, framework");

        if (error) throw error;
        renderCommunityChart(data);
    } catch (err) {
        console.error("Error fetching community stats:", err);
    }
}

function renderCommunityChart(rows) {
    communityBarsContainer.innerHTML = "";
    
    const scoreMap = {};
    const countMap = {};

    DASHBOARDS.forEach(db => {
        const label = `${db.model} (${db.framework.toUpperCase()} - ${db.arm})`;
        scoreMap[label] = 0;
        countMap[label] = 0;
    });

    rows.forEach(r => {
        const frameworkStr = r.framework ? r.framework.toUpperCase() : "PYTHON";
        const label = `${r.model} (${frameworkStr} - ${r.arm})`;
        if (label in scoreMap) {
            scoreMap[label] += TIER_SCORES[r.tier] || 0;
            countMap[label]++;
        }
    });

    const items = Object.keys(scoreMap).map(label => {
        const votes = countMap[label];
        const avg = votes > 0 ? (scoreMap[label] / votes).toFixed(2) : "0.00";
        return { label, avg: parseFloat(avg), votes };
    });

    // Sort best to worst average score
    items.sort((a, b) => b.avg - a.avg);

    items.forEach(item => {
        const block = document.createElement("div");
        block.className = "chart-bar-item";

        // Score maps S=5 to 100% width
        const widthPercent = (item.avg / 5) * 100;

        block.innerHTML = `
            <div class="chart-bar-labels">
                <span class="chart-bar-name">${item.label}</span>
                <span class="chart-bar-count">Avg Score: ${item.avg} / 5.00 (${item.votes} votes)</span>
            </div>
            <div class="chart-bar-track">
                <div class="chart-bar-fill" style="width: ${widthPercent}%;"></div>
            </div>
        `;
        communityBarsContainer.appendChild(block);
    });
}

// Supabase Realtime channel subscription
function subscribeRealtime() {
    supabaseClient
        .channel("realtime-tiered-rankings")
        .on("postgres_changes", { event: "INSERT", schema: "public", table: "dashboard_tiered_rankings_python" }, () => {
            fetchCommunityStats();
        })
        .subscribe();
}

// 8. Event handlers & Welcome onboarding
btnStartEvaluation.addEventListener("click", () => {
    welcomeView.classList.remove("active-view");
    boardView.classList.add("active-view");
    initializeBoard();
});

btnRestart.addEventListener("click", () => {
    sessionId = uuidv4();
    summaryView.classList.remove("active-view");
    boardView.classList.add("active-view");
    btnSubmitTiers.innerHTML = `<i class="fa-solid fa-circle-check"></i> Submit Tier List`;
    initializeBoard();
});

// Fullscreen Lightbox
function openLightbox(dbIdOrUrl, title = null) {
    let db = null;
    let url = "";
    let caption = "";
    let isReviewMode = false;

    if (title !== null) {
        url = dbIdOrUrl;
        caption = title;
        isReviewMode = true;
        currentLightboxDbId = null;
    } else {
        db = DASHBOARDS.find(d => d.id === dbIdOrUrl);
        if (!db) return;
        url = db.url;
        caption = db.name;
        currentLightboxDbId = db.id;
    }

    lightboxImg.src = url;
    const titleEl = document.getElementById("lightbox-title");
    if (titleEl) titleEl.innerText = caption;

    const sidebar = document.querySelector(".lightbox-sidebar");
    if (sidebar) {
        if (isReviewMode) {
            sidebar.style.display = "none";
        } else {
            sidebar.style.display = "flex";
            
            const currentTier = assignedTiers[db.id];
            const rankButtons = document.querySelectorAll(".lightbox-rank-btn");
            const removeBtn = document.getElementById("lightbox-remove-btn");

            rankButtons.forEach(btn => {
                btn.classList.remove("active");
                const tier = btn.dataset.tier;
                if (currentTier === tier) {
                    btn.classList.add("active");
                }
                
                btn.onclick = () => {
                    placeCard(db.id, tier);
                    showNextDashboard();
                };
            });

            if (currentTier) {
                removeBtn.style.display = "flex";
                removeBtn.onclick = () => {
                    const cardEl = document.getElementById(`card-${db.id}`);
                    poolZone.appendChild(cardEl);
                    delete assignedTiers[db.id];
                    delete assignedTags[db.id];
                    updatePoolCount();
                    checkIfComplete();
                    showNextDashboard();
                };
            } else {
                removeBtn.style.display = "none";
            }
        }
    }

    lightboxModal.style.display = "flex";
    lightboxModal.offsetHeight;
    lightboxModal.classList.add("active");
}

function closeLightbox() {
    lightboxModal.classList.remove("active");
    currentLightboxDbId = null;
    setTimeout(() => {
        lightboxModal.style.display = "none";
        lightboxImg.src = "";
    }, 300);
}

function showNextDashboard() {
    if (!currentLightboxDbId) return;
    const currentIndex = DASHBOARDS.findIndex(d => d.id === currentLightboxDbId);
    if (currentIndex !== -1 && currentIndex < DASHBOARDS.length - 1) {
        openLightbox(DASHBOARDS[currentIndex + 1].id);
    } else {
        closeLightbox();
    }
}

function showPrevDashboard() {
    if (!currentLightboxDbId) return;
    const currentIndex = DASHBOARDS.findIndex(d => d.id === currentLightboxDbId);
    if (currentIndex > 0) {
        openLightbox(DASHBOARDS[currentIndex - 1].id);
    }
}

// Event Listeners for closing lightbox
lightboxClose.addEventListener("click", closeLightbox);
lightboxModal.addEventListener("click", (e) => {
    if (e.target === lightboxModal) {
        closeLightbox();
    }
});

// Keyboard Navigation and Hotkeys
window.addEventListener("keydown", (e) => {
    const isLightboxActive = lightboxModal.classList.contains("active");
    const isTyping = document.activeElement.tagName === "TEXTAREA" || document.activeElement.tagName === "INPUT";
    if (!isLightboxActive || isTyping) return;

    const key = e.key.toLowerCase();
    
    if (key === "escape") {
        closeLightbox();
        e.preventDefault();
    } else if (key === "arrowright") {
        showNextDashboard();
        e.preventDefault();
    } else if (key === "arrowleft") {
        showPrevDashboard();
        e.preventDefault();
    } else if (currentLightboxDbId) {
        let tier = null;
        if (key === "s" || key === "1") tier = "S";
        else if (key === "a" || key === "2") tier = "A";
        else if (key === "b" || key === "3") tier = "B";
        else if (key === "c" || key === "4") tier = "C";
        else if (key === "d" || key === "5") tier = "D";

        if (tier) {
            placeCard(currentLightboxDbId, tier);
            showNextDashboard();
            e.preventDefault();
        }
    }
});

// Amazon-style Magnifier Zoom
function initMagnifier() {
    const img = document.getElementById("lightbox-img");
    const lens = document.getElementById("lightbox-lens-tracker");
    const pane = document.getElementById("lightbox-zoom-pane");
    const container = document.querySelector(".lightbox-image-area");
    
    if (!img || !lens || !pane || !container) return;

    const zoom = 2.5; // magnification scale

    img.addEventListener("mousemove", moveZoom);
    img.addEventListener("mouseenter", showZoom);
    img.addEventListener("mouseleave", hideZoom);

    function showZoom() {
        if (!img.src || window.innerWidth <= 768) return;
        pane.style.display = "block";
        lens.style.display = "block";
        pane.style.backgroundImage = `url('${img.src}')`;
        
        const r = img.getBoundingClientRect();
        
        const lensWidth = pane.offsetWidth / zoom;
        const lensHeight = pane.offsetHeight / zoom;
        
        lens.style.width = `${lensWidth}px`;
        lens.style.height = `${lensHeight}px`;
        
        pane.style.backgroundSize = `${r.width * zoom}px ${r.height * zoom}px`;
    }

    function hideZoom() {
        pane.style.display = "none";
        lens.style.display = "none";
    }

    function moveZoom(e) {
        if (window.innerWidth <= 768) return;
        
        const r = img.getBoundingClientRect();
        const cr = container.getBoundingClientRect();
        
        let x = e.clientX - r.left;
        let y = e.clientY - r.top;
        
        if (x < 0) x = 0;
        if (x > r.width) x = r.width;
        if (y < 0) y = 0;
        if (y > r.height) y = r.height;

        let lensX = x - (lens.offsetWidth / 2);
        let lensY = y - (lens.offsetHeight / 2);
        
        if (lensX < 0) lensX = 0;
        if (lensX > r.width - lens.offsetWidth) lensX = r.width - lens.offsetWidth;
        if (lensY < 0) lensY = 0;
        if (lensY > r.height - lens.offsetHeight) lensY = r.height - lens.offsetHeight;

        lens.style.left = `${lensX + r.left - cr.left}px`;
        lens.style.top = `${lensY + r.top - cr.top}px`;
        
        const bgX = lensX * zoom;
        const bgY = lensY * zoom;
        
        pane.style.backgroundPosition = `-${bgX}px -${bgY}px`;
    }
}

// Initialize magnifier zoom on page load
initMagnifier();

// Animated Neon Toast Popup
function triggerGradePopup(tier) {
    const popup = document.getElementById("grade-popup");
    const valSpan = popup.querySelector(".neon-grade-val");
    if (!popup || !valSpan) return;

    valSpan.innerText = tier;
    
    // Reset classes
    popup.className = "neon-grade-popup";
    
    // Add specific neon grade style
    popup.classList.add(`neon-${tier.toLowerCase()}-tier`);
    
    // Trigger pop animation
    popup.classList.add("show");
    
    // Remove after animation completes
    setTimeout(() => {
        popup.classList.remove("show");
    }, 850);
}

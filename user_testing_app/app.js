/* ==========================================================================
   DashSwipe Application Logic
   Tinder Card Deck Drag/Swipe Physics + Supabase Integration
   ========================================================================== */

// 1. Initialize Supabase
const SUPABASE_URL = "https://ovwktjjeoowlktdfbuuu.supabase.co";
const SUPABASE_KEY = "sb_publishable_B2pz5WTA3UEVUeKACIgmBw_8_r0S3kU";
const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

// 2. Data Definition for the 10 Dashboard Screenshots (Real Landing Pages of all 10 Benchmark Apps)
const DASHBOARDS = [
    {
        id: "model=deepseek-v4-pro|arm=skills|tab=Overview|framework=shiny_python|theme=zephyr",
        title: "Workforce Retention Dashboard (Layout 1)",
        badge: "excellent",
        badgeText: "Layout 1",
        desc: "Clean zephyr theme with left-bordered KPI cards, status donut charts, and department headcount col-plots.",
        url: "assets/dashboard1.png"
    },
    {
        id: "model=opus-4-8|arm=skills|tab=Overview|framework=shiny_python|theme=zephyr",
        title: "Workforce Retention Dashboard (Layout 2)",
        badge: "excellent",
        badgeText: "Layout 2",
        desc: "Modern theme utilizing gear menu card popovers, styled SVG icons, and a gt-based department summary table.",
        url: "assets/dashboard2.png"
    },
    {
        id: "model=opus-4-8|arm=skills|tab=Overview|framework=shiny_r|theme=shiny_light",
        title: "Workforce Retention Dashboard (Layout 3)",
        badge: "excellent",
        badgeText: "Layout 3",
        desc: "Pristine R bslib corporate blue layout with tooltip helpers, five value boxes, and horizontal ggplot charts.",
        url: "assets/dashboard3.png"
    },
    {
        id: "model=opus-4-8|arm=vanilla|tab=Overview|framework=shiny_r|theme=flatly",
        title: "Workforce Retention Dashboard (Layout 4)",
        badge: "excellent",
        badgeText: "Layout 4",
        desc: "Highly interactive flatly-themed layout featuring interactive plotly tooltips, value boxes, and dual column grids.",
        url: "assets/dashboard4.png"
    },
    {
        id: "model=opus-4-7|arm=skills|tab=Overview|framework=shiny_python|theme=zephyr",
        title: "Workforce Retention Dashboard (Layout 5)",
        badge: "excellent",
        badgeText: "Layout 5",
        desc: "Structured zephyr theme showcasing multi-select dropdown card toolbar filters and geographic office footprint maps.",
        url: "assets/dashboard5.png"
    },
    {
        id: "model=qwen-3-6-plus|arm=skills|tab=Overview|framework=shiny_python|theme=zephyr",
        title: "Workforce Retention Dashboard (Layout 6)",
        badge: "excellent",
        badgeText: "Layout 6",
        desc: "Single-page scroll layout integrating live interactive maps, great-tables directory grids, and spacing details.",
        url: "assets/dashboard6.png"
    },
    {
        id: "model=minimax-m3|arm=vanilla|tab=Overview|framework=shiny_python|theme=standard",
        title: "Workforce Retention Dashboard (Layout 7)",
        badge: "excellent",
        badgeText: "Layout 7",
        desc: "Standard layout featuring five essential KPI cards, status mix donut, department headcounts, and metric box plots.",
        url: "assets/dashboard7.png"
    },
    {
        id: "model=opus-4-8|arm=vanilla|tab=Overview|framework=shiny_python|theme=standard",
        title: "Workforce Retention Dashboard (Layout 8)",
        badge: "excellent",
        badgeText: "Layout 8",
        desc: "Standard theme utilizing saturated gradient metric value cards, a bubble locations map, and a burnout quadrant.",
        url: "assets/dashboard8.png"
    },
    {
        id: "model=minimax-m3|arm=skills|tab=Overview|framework=shiny_python|theme=standard",
        title: "Workforce Retention Dashboard (Layout 9)",
        badge: "excellent",
        badgeText: "Layout 9",
        desc: "Premium styled layout utilizing sidebar controls, left-bordered accent KPI value boxes, and high-contrast department metrics.",
        url: "assets/dashboard9.png"
    },
    {
        id: "model=opus-4-7|arm=vanilla|tab=Overview|framework=shiny_python|theme=standard",
        title: "Workforce Retention Dashboard (Layout 10)",
        badge: "excellent",
        badgeText: "Layout 10",
        desc: "Palmer Penguins species distribution morphological catalog with simple colored cards and low-contrast borders.",
        url: "assets/dashboard10.png"
    }
];

// 3. Application State Variables
let currentCardIndex = 0;
let sessionResponses = []; // Tracks local session votes to populate analytics
let isSwiping = false;

// Drag Physics Variables
let isDragging = false;
let startX = 0;
let startY = 0;
let currentX = 0;
let currentY = 0;
const SWIPE_THRESHOLD = 130; // Min drag pixels to execute swipe-off

// DOM Element Selections
const cardDeck = document.getElementById("card-deck");
const progressText = document.getElementById("progress-text");
const progressPercent = document.getElementById("progress-percent");
const progressBarFill = document.getElementById("progress-bar-fill");
const dislikeIndicator = document.querySelector(".swipe-indicator.dislike");
const likeIndicator = document.querySelector(".swipe-indicator.like");

const btnLike = document.getElementById("btn-like");
const btnDislike = document.getElementById("btn-dislike");
const feedbackModal = document.getElementById("feedback-modal");
const feedbackForm = document.getElementById("feedback-form");
const detailTextarea = document.getElementById("disapproval_details");
const btnCancelFeedback = document.getElementById("btn-cancel-feedback");

const deckView = document.getElementById("deck-view");
const summaryView = document.getElementById("summary-view");
const valApprovalRate = document.getElementById("val-approval-rate");
const valTotalSwipes = document.getElementById("val-total-swipes");
const chartBarsContainer = document.getElementById("chart-bars-container");
const btnRestart = document.getElementById("btn-restart");

// 4. Card Initialization Functions
function buildCardStack() {
    cardDeck.innerHTML = "";
    // Build stack starting from index backwards so DOM orders them correctly (top card last)
    for (let i = DASHBOARDS.length - 1; i >= currentCardIndex; i--) {
        const item = DASHBOARDS[i];
        const card = document.createElement("div");
        card.className = "tinder-card glass-card";
        card.dataset.id = item.id;
        card.dataset.index = i;
        
        card.innerHTML = `
            <div class="card-img-wrapper">
                <img src="${item.url}" alt="${item.title}" draggable="false">
            </div>
            <div class="card-details">
                <div>
                    <h3>${item.title}</h3>
                    <p style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">${item.desc}</p>
                </div>
                <span class="rating-badge ${item.badge}">${item.badgeText}</span>
            </div>
        `;
        
        if (i === currentCardIndex) {
            setupCardDrag(card);
        }
        
        cardDeck.appendChild(card);
    }
    updateProgressUI();
}

function updateProgressUI() {
    const total = DASHBOARDS.length;
    const current = Math.min(currentCardIndex + 1, total);
    const percent = Math.round((currentCardIndex / total) * 100);
    
    progressText.innerText = `Dashboard ${current} of ${total}`;
    progressPercent.innerText = `${percent}% Completed`;
    progressBarFill.style.width = `${percent}%`;
}

// 5. Drag/Swipe Physics Integration
function setupCardDrag(cardElement) {
    cardElement.addEventListener("pointerdown", onPointerDown);
    
    function onPointerDown(e) {
        if (isSwiping) return;
        isDragging = true;
        cardElement.style.transition = "none";
        startX = e.clientX;
        startY = e.clientY;
        
        cardElement.setPointerCapture(e.pointerId);
        cardElement.addEventListener("pointermove", onPointerMove);
        cardElement.addEventListener("pointerup", onPointerUp);
        cardElement.addEventListener("pointercancel", onPointerUp);
    }

    function onPointerMove(e) {
        if (!isDragging) return;
        currentX = e.clientX - startX;
        currentY = e.clientY - startY;
        
        // Dynamic drag offsets & standard tilting rotation
        const rot = currentX / 12;
        cardElement.style.transform = `translate3d(${currentX}px, ${currentY}px, 0) rotate(${rot}deg)`;
        
        // Handle drag opacity overlays
        if (currentX > 25) {
            const opacity = Math.min(currentX / 100, 0.95);
            likeIndicator.style.opacity = opacity;
            dislikeIndicator.style.opacity = 0;
        } else if (currentX < -25) {
            const opacity = Math.min(Math.abs(currentX) / 100, 0.95);
            dislikeIndicator.style.opacity = opacity;
            likeIndicator.style.opacity = 0;
        } else {
            likeIndicator.style.opacity = 0;
            dislikeIndicator.style.opacity = 0;
        }
    }

    function onPointerUp(e) {
        if (!isDragging) return;
        isDragging = false;
        
        likeIndicator.style.opacity = 0;
        dislikeIndicator.style.opacity = 0;
        
        cardElement.removeEventListener("pointermove", onPointerMove);
        cardElement.removeEventListener("pointerup", onPointerUp);
        cardElement.removeEventListener("pointercancel", onPointerUp);
        
        // Execute swipe or snap back
        if (currentX > SWIPE_THRESHOLD) {
            executeSwipe(cardElement, "right");
        } else if (currentX < -SWIPE_THRESHOLD) {
            executeSwipe(cardElement, "left");
        } else {
            // Smoothly snap back to origin
            cardElement.style.transition = "transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)";
            cardElement.style.transform = "translate3d(0, 0, 0) rotate(0deg)";
        }
    }
}

// 6. Action Execution (Swiping Animations)
function executeSwipe(cardElement, direction) {
    isSwiping = true;
    const flyX = direction === "right" ? window.innerWidth + 200 : -window.innerWidth - 200;
    const rot = direction === "right" ? 35 : -35;
    
    cardElement.style.transition = "transform 0.5s ease-in, opacity 0.5s ease-in";
    cardElement.style.transform = `translate3d(${flyX}px, ${currentY}px, 0) rotate(${rot}deg)`;
    cardElement.style.opacity = 0;
    
    setTimeout(() => {
        cardElement.remove();
        isSwiping = false;
        handleSwipeOutcome(direction);
    }, 450);
}

// Button click triggers
function triggerSwipeByButton(direction) {
    if (isSwiping || currentCardIndex >= DASHBOARDS.length) return;
    
    const activeCard = cardDeck.querySelector(`.tinder-card[data-index="${currentCardIndex}"]`);
    if (!activeCard) return;
    
    isSwiping = true;
    const flyX = direction === "right" ? window.innerWidth + 200 : -window.innerWidth - 200;
    const rot = direction === "right" ? 35 : -35;
    
    // Animate swiping out
    activeCard.style.transition = "transform 0.5s cubic-bezier(0.25, 0.8, 0.25, 1), opacity 0.4s ease";
    activeCard.style.transform = `translate3d(${flyX}px, -40px, 0) rotate(${rot}deg)`;
    activeCard.style.opacity = 0;
    
    setTimeout(() => {
        activeCard.remove();
        isSwiping = false;
        handleSwipeOutcome(direction);
    }, 400);
}

// Keyboard Arrow Listening
window.addEventListener("keydown", (e) => {
    // Ignore when modal is open
    if (feedbackModal.classList.contains("active")) return;
    
    if (e.key === "ArrowLeft") {
        triggerSwipeByButton("left");
    } else if (e.key === "ArrowRight") {
        triggerSwipeByButton("right");
    }
});

btnLike.addEventListener("click", () => triggerSwipeByButton("right"));
btnDislike.addEventListener("click", () => triggerSwipeByButton("left"));

// 7. Supabase Database Commits
function handleSwipeOutcome(direction) {
    const currentItem = DASHBOARDS[currentCardIndex];
    
    if (direction === "right") {
        // Committing APPROVED outcome directly to Supabase
        commitFeedbackToSupabase(currentItem.id, currentItem.url, "approve", null, null);
        proceedToNextCard();
    } else {
        // Open the disapproval feedback form
        openFeedbackModal();
    }
}

async function commitFeedbackToSupabase(screenshotId, screenshotUrl, rating, reason, details) {
    try {
        const record = {
            screenshot_id: screenshotId,
            screenshot_url: screenshotUrl,
            user_rating: rating,
            disapproval_reason: reason,
            disapproval_details: details
        };
        
        // Push local session variables for the end analytics
        sessionResponses.push(record);
        
        const { data, error } = await supabaseClient
            .from("dashboard_feedback")
            .insert([record]);
            
        if (error) {
            console.error("Supabase insert error:", error);
        } else {
            console.log("Feedback committed successfully to Supabase:", record);
        }
    } catch (err) {
        console.error("Failed to commit feedback:", err);
    }
}

function proceedToNextCard() {
    currentCardIndex++;
    if (currentCardIndex < DASHBOARDS.length) {
        buildCardStack();
    } else {
        updateProgressUI();
        displaySummaryView();
    }
}

// 8. Feedback Form Submissions
function openFeedbackModal() {
    feedbackForm.reset();
    detailTextarea.value = "";
    feedbackModal.classList.add("active");
}

function closeFeedbackModal() {
    feedbackModal.classList.remove("active");
}

feedbackForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const currentItem = DASHBOARDS[currentCardIndex];
    const selectedOption = feedbackForm.querySelector('input[name="disapproval_reason"]:checked');
    const reasonValue = selectedOption ? selectedOption.value : "Skip";
    const detailsValue = detailTextarea.value.trim() || null;
    
    commitFeedbackToSupabase(
        currentItem.id,
        currentItem.url,
        "disapprove",
        reasonValue,
        detailsValue
    );
    
    closeFeedbackModal();
    proceedToNextCard();
});

btnCancelFeedback.addEventListener("click", () => {
    const currentItem = DASHBOARDS[currentCardIndex];
    commitFeedbackToSupabase(currentItem.id, currentItem.url, "disapprove", "Skipped", null);
    
    closeFeedbackModal();
    proceedToNextCard();
});

// 9. Session Stats & Summary Analytics Dashboard
function displaySummaryView() {
    deckView.classList.remove("active-view");
    summaryView.style.display = "flex";
    
    // Approval Rate Calculations
    const approves = sessionResponses.filter(r => r.user_rating === "approve").length;
    const total = sessionResponses.length;
    const rate = total > 0 ? Math.round((approves / total) * 100) : 0;
    
    valApprovalRate.innerText = `${rate}%`;
    valTotalSwipes.innerText = total;
    
    // Flagged reasons metrics counts
    const reasonsMap = {
        "Visual Clutter": 0,
        "Bad Color Theme": 0,
        "Lack of Insights": 0,
        "Confusing Charts": 0,
        "Too Basic": 0,
        "Other": 0
    };
    
    sessionResponses.forEach(r => {
        if (r.user_rating === "disapprove" && r.disapproval_reason in reasonsMap) {
            reasonsMap[r.disapproval_reason]++;
        }
    });
    
    chartBarsContainer.innerHTML = "";
    
    // Render dynamic glassmorphic charts bars
    Object.entries(reasonsMap).forEach(([reason, count]) => {
        const item = document.createElement("div");
        item.className = "chart-bar-item";
        
        // Find percentage size relative to the disapproval count
        const totalDisapproves = sessionResponses.filter(r => r.user_rating === "disapprove").length;
        const widthPercent = totalDisapproves > 0 ? Math.round((count / totalDisapproves) * 100) : 0;
        
        item.innerHTML = `
            <div class="chart-bar-labels">
                <span class="chart-bar-name">${reason}</span>
                <span class="chart-bar-count">${count} vote(s)</span>
            </div>
            <div class="chart-bar-track">
                <div class="chart-bar-fill" style="width: 0%;"></div>
            </div>
        `;
        
        chartBarsContainer.appendChild(item);
        
        // Animate the growth of the bar
        setTimeout(() => {
            const fill = item.querySelector(".chart-bar-fill");
            if (fill) fill.style.width = `${widthPercent}%`;
        }, 150);
    });
}

// 10. Restart Session Handler
btnRestart.addEventListener("click", () => {
    currentCardIndex = 0;
    sessionResponses = [];
    isSwiping = false;
    isDragging = false;
    
    summaryView.style.display = "none";
    deckView.classList.add("active-view");
    
    buildCardStack();
});

// Start the deck stack
document.addEventListener("DOMContentLoaded", () => {
    buildCardStack();
});

const SUPABASE_URL = "https://ovwktjjeoowlktdfbuuu.supabase.co";
const SUPABASE_KEY = "sb_publishable_B2pz5WTA3UEVUeKACIgmBw_8_r0S3kU";
const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

const DASHBOARDS_METADATA = {
    "py-ds-v4-pro-skills": { name: "Dashboard 1", model: "DeepSeek V4 Pro", arm: "skills", cost: 0.1038, time: 508, framework: "python", url: "assets/deepseek-v4-pro-skills.png" },
    "py-claude-opus-skills": { name: "Dashboard 2", model: "Claude Opus 4-8", arm: "skills", cost: 1.4623, time: 309, framework: "python", url: "assets/claude-opus-4-8-skills.png" },
    "py-ds-v4-flash-skills": { name: "Dashboard 3", model: "DeepSeek V4 Flash", arm: "skills", cost: 0.0127, time: 270, framework: "python", url: "assets/deepseek-v4-flash-skills.png" },
    "py-gpt-5-5-skills": { name: "Dashboard 4", model: "GPT 5.5", arm: "skills", cost: 0.4274, time: 196, framework: "python", url: "assets/gpt-5.5-skills.png" },
    "py-minimax-m3-skills": { name: "Dashboard 5", model: "Minimax M3", arm: "skills", cost: 0.1037, time: 519, framework: "python", url: "assets/minimax-m3-skills.png" },
    "py-qwen-max-skills": { name: "Dashboard 6", model: "Qwen 3.7 Max", arm: "skills", cost: 0.5410, time: 261, framework: "python", url: "assets/qwen3.7-max-skills.png" },
    "py-ds-v4-pro-vanilla": { name: "Dashboard 7", model: "DeepSeek V4 Pro", arm: "vanilla", cost: 0.0862, time: 570, framework: "python", url: "assets/deepseek-v4-pro-vanilla.png" },
    "py-claude-opus-vanilla": { name: "Dashboard 8", model: "Claude Opus 4-8", arm: "vanilla", cost: 0.4908, time: 142, framework: "python", url: "assets/claude-opus-4-8-vanilla.png" },
    "py-ds-v4-flash-vanilla": { name: "Dashboard 9", model: "DeepSeek V4 Flash", arm: "vanilla", cost: 0.0020, time: 92, framework: "python", url: "assets/deepseek-v4-flash-vanilla.png" },
    "r-claude-opus-skills": { name: "Dashboard 10", model: "Claude Opus 4-8", arm: "skills", cost: 0.5229, time: 188, framework: "r", url: "assets/r-claude-opus-4-8-skills.png" },
    "r-ds-v4-flash-skills": { name: "Dashboard 11", model: "DeepSeek V4 Flash", arm: "skills", cost: 0.0043, time: 133, framework: "r", url: "assets/r-deepseek-v4-flash-skills.png" },
    "r-ds-v4-pro-skills": { name: "Dashboard 12", model: "DeepSeek V4 Pro", arm: "skills", cost: 0.0467, time: 277, framework: "r", url: "assets/r-deepseek-v4-pro-skills.png" },
    "r-gpt-5-5-skills": { name: "Dashboard 13", model: "GPT 5.5", arm: "skills", cost: 0.5972, time: 267, framework: "r", url: "assets/r-gpt-5.5-skills.png" },
    "r-minimax-m3-skills": { name: "Dashboard 14", model: "Minimax M3", arm: "skills", cost: 0.0869, time: 415, framework: "r", url: "assets/r-minimax-m3-skills.png" },
    "r-qwen-max-skills": { name: "Dashboard 15", model: "Qwen 3.7 Max", arm: "skills", cost: 0.2984, time: 116, framework: "r", url: "assets/r-qwen3.7-max-skills.png" },
    "r-claude-opus-vanilla": { name: "Dashboard 16", model: "Claude Opus 4-8", arm: "vanilla", cost: 0.4266, time: 123, framework: "r", url: "assets/r-claude-opus-4-8-vanilla.png" },
    "r-ds-v4-flash-vanilla": { name: "Dashboard 17", model: "DeepSeek V4 Flash", arm: "vanilla", cost: 0.0029, time: 129, framework: "r", url: "assets/r-deepseek-v4-flash-vanilla.png" },
    "r-ds-v4-pro-vanilla": { name: "Dashboard 18", model: "DeepSeek V4 Pro", arm: "vanilla", cost: 0.0905, time: 603, framework: "r", url: "assets/r-deepseek-v4-pro-vanilla.png" },
    "r-gpt-5-5-vanilla": { name: "Dashboard 19", model: "GPT 5.5", arm: "vanilla", cost: 0.4408, time: 203, framework: "r", url: "assets/r-gpt-5.5-vanilla.png" },
    "r-minimax-m3-vanilla": { name: "Dashboard 20", model: "Minimax M3", arm: "vanilla", cost: 0.0247, time: 163, framework: "r", url: "assets/r-minimax-m3-vanilla.png" },
    "r-qwen-max-vanilla": { name: "Dashboard 21", model: "Qwen 3.7 Max", arm: "vanilla", cost: 0.1523, time: 103, framework: "r", url: "assets/r-qwen3.7-max-vanilla.png" }
};

const TIER_SCORES = { "S": 5, "A": 4, "B": 3, "C": 2, "D": 1 };

let rawDbRows = [];
let standingsList = [];
let chartRoiInstance = null;
let chartSkillsInstance = null;
let chartFrameworkInstance = null;
let chartTagsInstance = null;

let currentBeeswarmGroup = "model";

const totalVotersEl = document.getElementById("val-total-voters");
const totalRatingsEl = document.getElementById("val-total-ratings");
const topModelEl = document.getElementById("val-top-model");
const avgCostEl = document.getElementById("val-avg-cost");
const leaderboardBody = document.getElementById("leaderboard-body");
const activityStream = document.getElementById("activity-stream");
const streamCount = document.getElementById("stream-count");
const lastUpdated = document.getElementById("last-updated");
const insightsContent = document.getElementById("insights-content");
const tableCount = document.getElementById("table-count");

async function init() {
    await fetchTelemetryData();
    subscribeToRealtime();
    bindUIEvents();
}

function bindUIEvents() {
    const refreshBtn = document.getElementById("btn-refresh");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", async () => {
            refreshBtn.classList.add("spinning");
            await fetchTelemetryData();
            setTimeout(() => refreshBtn.classList.remove("spinning"), 400);
        });
    }

    const exportBtn = document.getElementById("btn-export");
    if (exportBtn) {
        exportBtn.addEventListener("click", exportCSV);
    }

    setupLeaderboardPreview();
    setupBeeswarmToggles();
}

async function fetchTelemetryData() {
    try {
        const { data, error } = await supabaseClient
            .from("dashboard_tiered_rankings_python")
            .select("*")
            .order("created_at", { ascending: false });

        if (error) throw error;

        rawDbRows = data || [];
        processAndRenderAnalytics();
        updateLastUpdated();
    } catch (err) {
        console.error("Telemetry Retrieval Error:", err);
    }
}

function updateLastUpdated() {
    if (!lastUpdated) return;
    const now = new Date();
    const time = now.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    lastUpdated.innerHTML = `<i class="fa-regular fa-clock"></i> Updated ${time}`;
}

function animateCounter(el, target, suffix = "", duration = 800, isCurrency = false) {
    if (!el) return;
    const start = performance.now();
    const initial = 0;

    function update(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = initial + (target - initial) * eased;
        if (isCurrency) {
            el.innerText = "$" + current.toFixed(4);
        } else {
            el.innerText = Math.floor(current).toLocaleString() + suffix;
        }
        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            if (isCurrency) {
                el.innerText = "$" + target.toFixed(4);
            } else {
                el.innerText = target.toLocaleString() + suffix;
            }
        }
    }

    requestAnimationFrame(update);
}

function processAndRenderAnalytics() {
    const totalRatings = rawDbRows.length;
    const voterSessions = new Set(rawDbRows.map(r => r.session_id));
    const totalVoters = voterSessions.size;

    animateCounter(totalVotersEl, totalVoters);
    animateCounter(totalRatingsEl, totalRatings);

    if (totalRatings === 0) {
        leaderboardBody.innerHTML = `<tr><td colspan="8" class="loading-cell"><span class="skeleton-pulse"></span> No ratings recorded yet.</td></tr>`;
        insightsContent.innerHTML = `<span class="insight-pill">No data yet — be the first to submit rankings!</span>`;
        return;
    }

    const modelStatsMap = {};
    Object.keys(DASHBOARDS_METADATA).forEach(id => {
        modelStatsMap[id] = {
            metadata: DASHBOARDS_METADATA[id],
            scoreSum: 0,
            voteCount: 0
        };
    });

    let totalCostAccum = 0;
    let countedCosts = 0;

    rawDbRows.forEach(row => {
        const meta = DASHBOARDS_METADATA[row.dashboard_id];
        if (meta) {
            totalCostAccum += meta.cost;
            countedCosts++;
        }
        if (row.dashboard_id in modelStatsMap) {
            modelStatsMap[row.dashboard_id].scoreSum += TIER_SCORES[row.tier] || 0;
            modelStatsMap[row.dashboard_id].voteCount++;
        }
    });

    const avgCost = countedCosts > 0 ? totalCostAccum / countedCosts : 0;
    animateCounter(avgCostEl, avgCost, "", 600, true);

    standingsList = Object.keys(modelStatsMap).map(id => {
        const item = modelStatsMap[id];
        const avgScore = item.voteCount > 0 ? (item.scoreSum / item.voteCount) : 0;
        return {
            id: id,
            name: item.metadata.model + " (" + item.metadata.arm + ")",
            modelName: item.metadata.model,
            arm: item.metadata.arm,
            framework: item.metadata.framework,
            avg: avgScore,
            votes: item.voteCount,
            cost: item.metadata.cost,
            time: item.metadata.time
        };
    });

    standingsList.sort((a, b) => b.avg - a.avg);

    const bestModel = standingsList.find(s => s.votes > 0);
    topModelEl.innerText = bestModel ? bestModel.modelName : "N/A";

    renderLeaderboardTable(standingsList);
    renderRoiChart(standingsList);
    renderSkillsChart(rawDbRows);
    renderFrameworksChart(rawDbRows);
    renderDriversChart(rawDbRows);
    renderBeeswarm(rawDbRows);
    renderActivityFeed(rawDbRows.slice(0, 20));
    renderInsights(standingsList, totalRatings, totalVoters, avgCost);
}

function renderInsights(standings, totalRatings, totalVoters, avgCost) {
    if (!insightsContent) return;

    const active = standings.filter(s => s.votes > 0);
    if (active.length === 0) {
        insightsContent.innerHTML = `<span class="insight-pill">No rankings submitted yet</span>`;
        return;
    }

    const best = active[0];
    const worst = active[active.length - 1];
    const skillsAvg = active.filter(s => s.arm === "skills").reduce((s, i) => s + i.avg, 0) / Math.max(1, active.filter(s => s.arm === "skills").length);
    const vanillaAvg = active.filter(s => s.arm === "vanilla").reduce((s, i) => s + i.avg, 0) / Math.max(1, active.filter(s => s.arm === "vanilla").length);
    const skillsWins = skillsAvg > vanillaAvg;
    const bestModel = `${best.modelName} (${best.avg.toFixed(2)})`;
    const totalCost = totalRatings > 0 ? avgCost.toFixed(4) : "$0";

    const pills = [
        `<span class="insight-pill"><i class="fa-solid fa-crown" style="color: #f59e0b;"></i> Leader: ${bestModel}</span>`,
        `<span class="insight-pill"><i class="fa-solid fa-${skillsWins ? 'graduation-cap' : 'flask'}"></i> ${skillsWins ? 'Skills' : 'Vanilla'} leads by ${Math.abs(skillsAvg - vanillaAvg).toFixed(2)} pts</span>`,
        `<span class="insight-pill"><i class="fa-solid fa-users"></i> ${totalVoters} voter${totalVoters !== 1 ? 's' : ''} · ${totalRatings} rating${totalRatings !== 1 ? 's' : ''}</span>`
    ];

    if (worst && worst.votes > 0 && worst.modelName !== best.modelName) {
        pills.push(`<span class="insight-pill"><i class="fa-solid fa-triangle-exclamation" style="color: #ef4444;"></i> Lowest: ${worst.modelName} (${worst.avg.toFixed(2)})</span>`);
    }

    insightsContent.innerHTML = pills.join(" ");
}

function renderLeaderboardTable(standings) {
    leaderboardBody.innerHTML = "";
    const active = standings.filter(s => s.votes > 0);
    const inactive = standings.filter(s => s.votes === 0);

    if (tableCount) {
        const activeCount = active.length;
        tableCount.innerText = activeCount > 0 ? `${activeCount} ranked` : "";
    }

    active.forEach((item, index) => {
        const rank = index + 1;
        const avgScoreText = item.avg.toFixed(2);
        const medal = rank === 1 ? '<i class="fa-solid fa-crown" style="color: #f59e0b;"></i>' :
                      rank === 2 ? '<i class="fa-solid fa-medal" style="color: #94a3b8;"></i>' :
                      rank === 3 ? '<i class="fa-solid fa-medal" style="color: #cd7f32;"></i>' :
                      `#${rank}`;

        const tr = document.createElement("tr");
        tr.setAttribute("data-id", item.id);
        tr.innerHTML = `
            <td style="font-size: 12px;">${medal}</td>
            <td>
                <div style="font-weight: 600; font-size: 13px;">${item.modelName}</div>
            </td>
            <td>
                <span style="display: inline-flex; align-items: center; gap: 4px; font-size: 11px; color: var(--text-muted);">
                    ${item.arm === 'skills' ? '<i class="fa-solid fa-graduation-cap" style="color: var(--primary-neon);"></i> Skills' : '<i class="fa-solid fa-flask" style="color: var(--accent-red);"></i> Vanilla'}
                </span>
            </td>
            <td><span class="activity-tag" style="text-transform: uppercase;">${item.framework}</span></td>
            <td style="font-weight: 700; color: var(--primary-neon); font-family: var(--font-mono);">${avgScoreText}</td>
            <td style="color: var(--text-muted);">${item.votes}</td>
            <td style="color: var(--text-muted); font-family: var(--font-mono);">${item.time}s</td>
            <td style="font-family: var(--font-mono); color: #10b981;">$${item.cost.toFixed(4)}</td>
        `;
        leaderboardBody.appendChild(tr);
    });

    inactive.forEach(item => {
        const tr = document.createElement("tr");
        tr.setAttribute("data-id", item.id);
        tr.style.opacity = "0.35";
        tr.innerHTML = `
            <td style="font-size: 12px; color: var(--text-dim);">—</td>
            <td>
                <div style="font-weight: 600; font-size: 13px;">${item.modelName}</div>
            </td>
            <td>
                <span style="display: inline-flex; align-items: center; gap: 4px; font-size: 11px; color: var(--text-muted);">
                    ${item.arm === 'skills' ? '<i class="fa-solid fa-graduation-cap" style="color: var(--primary-neon);"></i> Skills' : '<i class="fa-solid fa-flask" style="color: var(--accent-red);"></i> Vanilla'}
                </span>
            </td>
            <td><span class="activity-tag" style="text-transform: uppercase;">${item.framework}</span></td>
            <td style="color: var(--text-dim);">—</td>
            <td style="color: var(--text-dim);">0</td>
            <td style="color: var(--text-dim); font-family: var(--font-mono);">${item.time}s</td>
            <td style="font-family: var(--font-mono); color: #10b981;">$${item.cost.toFixed(4)}</td>
        `;
        leaderboardBody.appendChild(tr);
    });
}

function setupLeaderboardPreview() {
    const previewCard = document.createElement("div");
    previewCard.id = "leaderboard-preview-card";
    previewCard.className = "preview-card-floating";
    document.body.appendChild(previewCard);

    leaderboardBody.addEventListener("mousemove", (e) => {
        const tr = e.target.closest("tr");
        if (!tr) {
            hidePreview();
            return;
        }

        const dbId = tr.getAttribute("data-id");
        if (!dbId || !DASHBOARDS_METADATA[dbId]) {
            hidePreview();
            return;
        }

        const meta = DASHBOARDS_METADATA[dbId];

        previewCard.innerHTML = `
            <div class="preview-card-img-wrapper">
                <img src="${meta.url}" alt="${meta.name}">
            </div>
            <div class="preview-card-content">
                <div class="preview-card-title">${meta.model}</div>
                <div class="preview-card-sub">
                    <span style="text-transform: uppercase; font-weight: 600; font-family: var(--font-mono); font-size: 10px;">${meta.framework}</span>
                    <span>·</span>
                    <span>${meta.arm === 'skills' ? 'Skills Guidelines' : 'Vanilla Prompting'}</span>
                </div>
            </div>
        `;

        previewCard.classList.add("active");

        const cardWidth = 300;
        const cardHeight = 240;

        let x = e.clientX + 20;
        let y = e.clientY + 20;

        if (x + cardWidth > window.innerWidth) {
            x = e.clientX - cardWidth - 20;
        }
        if (y + cardHeight > window.innerHeight) {
            y = e.clientY - cardHeight - 20;
        }

        previewCard.style.left = `${x}px`;
        previewCard.style.top = `${y}px`;
    });

    leaderboardBody.addEventListener("mouseleave", () => {
        hidePreview();
    });

    function hidePreview() {
        previewCard.classList.remove("active");
    }
}

function renderRoiChart(standings) {
    const activeData = standings.filter(s => s.votes > 0);
    if (activeData.length === 0) return;

    const svg = d3.select("#chart-roi-svg");
    svg.selectAll("*").remove();

    const container = svg.node().parentElement;
    const width = container.clientWidth || 400;
    const height = 260;
    svg.attr("width", width).attr("height", height);

    const margin = { top: 20, right: 30, bottom: 40, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const g = svg.append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    const xScale = d3.scaleLinear()
        .domain([1.5, 5.0])
        .range([0, innerWidth]);

    const yScale = d3.scaleLog()
        .domain([0.001, 2.0])
        .range([innerHeight, 0]);

    // X axis grid
    g.append("g")
        .attr("class", "grid")
        .attr("transform", `translate(0,${innerHeight})`)
        .call(d3.axisBottom(xScale).ticks(5).tickSize(-innerHeight).tickFormat(""))
        .selectAll("line")
        .attr("stroke", "rgba(0, 0, 0, 0.05)")
        .attr("stroke-dasharray", "2,2");

    // Y axis grid
    g.append("g")
        .attr("class", "grid")
        .call(d3.axisLeft(yScale).ticks(4).tickSize(-innerWidth).tickFormat(""))
        .selectAll("line")
        .attr("stroke", "rgba(0, 0, 0, 0.05)")
        .attr("stroke-dasharray", "2,2");

    g.append("g")
        .attr("transform", `translate(0,${innerHeight})`)
        .call(d3.axisBottom(xScale).ticks(5))
        .selectAll("text")
        .attr("fill", "#64748b")
        .style("font-family", "var(--font-body)")
        .style("font-size", "10px");

    g.append("g")
        .call(d3.axisLeft(yScale).ticks(4, "$,.3f"))
        .selectAll("text")
        .attr("fill", "#64748b")
        .style("font-family", "var(--font-body)")
        .style("font-size", "10px");

    // Calculate Pareto Frontier
    const activeItems = [...activeData];
    activeItems.sort((a, b) => a.avg - b.avg);

    const frontier = [];
    let minCostSoFar = Infinity;

    const sortedDesc = [...activeItems].sort((a, b) => b.avg - a.avg);
    sortedDesc.forEach(item => {
        if (item.cost < minCostSoFar) {
            frontier.push(item);
            minCostSoFar = item.cost;
        }
    });
    frontier.sort((a, b) => a.avg - b.avg);

    const line = d3.line()
        .x(d => xScale(d.avg))
        .y(d => yScale(d.cost))
        .curve(d3.curveLinear);

    g.append("path")
        .datum(frontier)
        .attr("fill", "none")
        .attr("stroke", "#10b981")
        .attr("stroke-width", 2)
        .attr("stroke-dasharray", "4,4")
        .attr("d", line);

    if (frontier.length > 0) {
        const lastFrontierPt = frontier[frontier.length - 1];
        g.append("text")
            .attr("x", xScale(lastFrontierPt.avg) - 8)
            .attr("y", yScale(lastFrontierPt.cost) - 8)
            .attr("text-anchor", "end")
            .style("font-family", "var(--font-heading)")
            .style("font-size", "9px")
            .style("font-weight", "bold")
            .style("fill", "#10b981")
            .text("Efficient Frontier");
    }

    const dots = g.selectAll(".roi-dot")
        .data(activeData, d => d.id)
        .join("circle")
        .attr("class", "roi-dot")
        .attr("cx", d => xScale(d.avg))
        .attr("cy", d => yScale(d.cost))
        .attr("r", 6)
        .attr("fill", d => d.arm === "skills" ? "#007bc2" : "#64748b")
        .attr("stroke", "#ffffff")
        .attr("stroke-width", 1.5)
        .style("cursor", "pointer");

    let tooltip = d3.select("#beeswarm-tooltip");
    if (tooltip.empty()) {
        tooltip = d3.select("body").append("div")
            .attr("id", "beeswarm-tooltip")
            .attr("class", "beeswarm-tooltip");
    }

    dots
        .on("mouseenter", function(event, d) {
            d3.select(this)
                .transition()
                .duration(150)
                .attr("r", 9)
                .attr("stroke", "#1e293b");

            const maxCost = d3.max(activeData, x => x.cost);
            const savingsPercent = ((maxCost - d.cost) / maxCost * 100).toFixed(0);

            tooltip.style("display", "block")
                .html(`
                    <strong>${d.modelName}</strong>
                    <div style="font-size: 10px; color: #94a3b8; margin-top: 2px;">
                        Framework: <span style="text-transform: uppercase; color: #ffffff;">${d.framework}</span> · 
                        Approach: <span style="text-transform: capitalize; color: #ffffff;">${d.arm}</span>
                    </div>
                    <div style="margin-top: 6px; font-size: 11px;">
                        Rating: <span style="font-weight: bold; color: #38bdf8;">${d.avg.toFixed(2)} / 5.0</span><br/>
                        Cost: <span style="font-weight: bold; color: #10b981;">$${d.cost.toFixed(4)}</span>
                    </div>
                    <div style="margin-top: 6px; font-size: 9px; color: #a7f3d0; background: rgba(16, 185, 129, 0.15); padding: 4px 6px; border-radius: 4px;">
                        <i class="fa-solid fa-piggy-bank"></i> ${savingsPercent}% cost savings vs max cost
                    </div>
                `);
        })
        .on("mousemove", function(event) {
            tooltip
                .style("left", (event.pageX + 12) + "px")
                .style("top", (event.pageY - 20) + "px");
        })
        .on("mouseleave", function() {
            d3.select(this)
                .transition()
                .duration(150)
                .attr("r", 6)
                .attr("stroke", "#ffffff");
            tooltip.style("display", "none");
        });
}

function renderSkillsChart(rows) {
    const ctx = document.getElementById("chart-skills-comparison").getContext("2d");

    let skillsSum = 0, skillsCount = 0;
    let vanillaSum = 0, vanillaCount = 0;

    rows.forEach(r => {
        if (r.arm === "skills") { skillsSum += TIER_SCORES[r.tier] || 0; skillsCount++; }
        else if (r.arm === "vanilla") { vanillaSum += TIER_SCORES[r.tier] || 0; vanillaCount++; }
    });

    const avgSkills = skillsCount > 0 ? skillsSum / skillsCount : 0;
    const avgVanilla = vanillaCount > 0 ? vanillaSum / vanillaCount : 0;

    if (chartSkillsInstance) chartSkillsInstance.destroy();

    chartSkillsInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Skills Guidelines", "Vanilla Prompting"],
            datasets: [{
                data: [avgSkills, avgVanilla],
                backgroundColor: [
                    "rgba(0, 123, 194, 0.25)",
                    "rgba(100, 116, 139, 0.25)"
                ],
                borderColor: ["#007bc2", "#64748b"],
                borderWidth: 2,
                borderRadius: 6,
                barPercentage: 0.5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: { color: "rgba(0, 0, 0, 0.05)" },
                    ticks: { color: "#64748b" },
                    min: 0, max: 5
                },
                x: {
                    grid: { display: false },
                    ticks: { color: "#475569", font: { size: 11 } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "rgba(30, 41, 59, 0.95)",
                    titleColor: "#ffffff",
                    bodyColor: "#cbd5e1",
                    borderColor: "#475569",
                    borderWidth: 1,
                    padding: 10,
                    cornerRadius: 8,
                    callbacks: {
                        label: ctx => ctx.parsed.y.toFixed(2) + " / 5.00"
                    }
                }
            }
        },
        plugins: [{
            id: "barLabels",
            afterDatasetsDraw(chart) {
                const meta = chart.getDatasetMeta(0);
                meta.data.forEach((bar, idx) => {
                    const val = chart.data.datasets[0].data[idx];
                    const ctx2 = chart.ctx;
                    ctx2.save();
                    ctx2.fillStyle = "#475569";
                    ctx2.font = "600 11px Outfit";
                    ctx2.textAlign = "center";
                    ctx2.fillText(val.toFixed(2), bar.x, bar.y - 8);
                    ctx2.restore();
                });
            }
        }]
    });
}

function renderFrameworksChart(rows) {
    const ctx = document.getElementById("chart-frameworks").getContext("2d");

    let pythonSum = 0, pythonCount = 0;
    let rSum = 0, rCount = 0;

    rows.forEach(r => {
        const fw = r.framework || "python";
        if (fw === "python") { pythonSum += TIER_SCORES[r.tier] || 0; pythonCount++; }
        else if (fw === "r") { rSum += TIER_SCORES[r.tier] || 0; rCount++; }
    });

    const avgPython = pythonCount > 0 ? pythonSum / pythonCount : 0;
    const avgR = rCount > 0 ? rSum / rCount : 0;

    if (chartFrameworkInstance) chartFrameworkInstance.destroy();

    chartFrameworkInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Python Shiny", "R Shiny"],
            datasets: [{
                data: [avgPython, avgR],
                backgroundColor: ["rgba(251, 191, 36, 0.25)", "rgba(59, 130, 246, 0.25)"],
                borderColor: ["#fbbf24", "#3b82f6"],
                borderWidth: 2,
                borderRadius: 6,
                barPercentage: 0.5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: { color: "rgba(0, 0, 0, 0.05)" },
                    ticks: { color: "#64748b" },
                    min: 0, max: 5
                },
                x: {
                    grid: { display: false },
                    ticks: { color: "#475569", font: { size: 11 } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "rgba(30, 41, 59, 0.95)",
                    titleColor: "#ffffff",
                    bodyColor: "#cbd5e1",
                    borderColor: "#475569",
                    borderWidth: 1,
                    padding: 10,
                    cornerRadius: 8,
                    callbacks: {
                        label: ctx => ctx.parsed.y.toFixed(2) + " / 5.00"
                    }
                }
            }
        },
        plugins: [{
            id: "barLabels",
            afterDatasetsDraw(chart) {
                const meta = chart.getDatasetMeta(0);
                meta.data.forEach((bar, idx) => {
                    const val = chart.data.datasets[0].data[idx];
                    const ctx2 = chart.ctx;
                    ctx2.save();
                    ctx2.fillStyle = "#475569";
                    ctx2.font = "600 11px Outfit";
                    ctx2.textAlign = "center";
                    ctx2.fillText(val.toFixed(2), bar.x, bar.y - 8);
                    ctx2.restore();
                });
            }
        }]
    });
}

function renderDriversChart(rows) {
    const overallAvg = d3.mean(rows, r => TIER_SCORES[r.tier] || 0) || 0;

    const tagScores = {};
    const tagCounts = {};
    rows.forEach(r => {
        if (r.feedback_words) {
            const score = TIER_SCORES[r.tier] || 0;
            r.feedback_words.split(",").forEach(t => {
                const tag = t.trim();
                if (tag) {
                    tagScores[tag] = (tagScores[tag] || 0) + score;
                    tagCounts[tag] = (tagCounts[tag] || 0) + 1;
                }
            });
        }
    });

    const driverData = Object.keys(tagScores).map(tag => {
        const avg = tagScores[tag] / tagCounts[tag];
        return {
            tag: tag,
            deviation: avg - overallAvg,
            avgScore: avg,
            count: tagCounts[tag]
        };
    });

    driverData.sort((a, b) => b.deviation - a.deviation);
    const data = driverData.slice(0, 10);

    const svg = d3.select("#chart-drivers-svg");
    svg.selectAll("*").remove();

    const container = svg.node().parentElement;
    const width = container.clientWidth || 400;
    const height = 260;
    svg.attr("width", width).attr("height", height);

    const margin = { top: 20, right: 30, bottom: 20, left: 110 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const g = svg.append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    const maxDev = d3.max(data, d => Math.abs(d.deviation)) || 1.0;
    const xLimit = Math.max(0.5, Math.min(2.0, maxDev * 1.1));
    const xScale = d3.scaleLinear()
        .domain([-xLimit, xLimit])
        .range([0, innerWidth]);

    const yScale = d3.scaleBand()
        .domain(data.map(d => d.tag))
        .range([0, innerHeight])
        .padding(0.15);

    g.append("line")
        .attr("x1", xScale(0))
        .attr("y1", 0)
        .attr("x2", xScale(0))
        .attr("y2", innerHeight)
        .attr("stroke", "#94a3b8")
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "3,3");

    g.append("text")
        .attr("x", xScale(0))
        .attr("y", -6)
        .attr("text-anchor", "middle")
        .style("font-family", "var(--font-heading)")
        .style("font-size", "9px")
        .style("font-weight", "bold")
        .style("fill", "#64748b")
        .text("Baseline (" + overallAvg.toFixed(2) + ")");

    const bars = g.selectAll(".driver-bar")
        .data(data, d => d.tag)
        .join("rect")
        .attr("class", "driver-bar")
        .attr("y", d => yScale(d.tag))
        .attr("x", d => d.deviation < 0 ? xScale(d.deviation) : xScale(0))
        .attr("width", d => Math.abs(xScale(d.deviation) - xScale(0)))
        .attr("height", yScale.bandwidth())
        .attr("fill", d => d.deviation >= 0 ? "#10b981" : "#ef4444")
        .attr("rx", 3)
        .style("cursor", "pointer")
        .style("opacity", 0.85);

    g.append("g")
        .call(d3.axisLeft(yScale).tickSize(0))
        .selectAll("text")
        .attr("fill", "var(--text-main)")
        .style("font-family", "var(--font-body)")
        .style("font-size", "10px")
        .style("font-weight", "500");

    let tooltip = d3.select("#beeswarm-tooltip");
    if (tooltip.empty()) {
        tooltip = d3.select("body").append("div")
            .attr("id", "beeswarm-tooltip")
            .attr("class", "beeswarm-tooltip");
    }

    bars
        .on("mouseenter", function(event, d) {
            d3.select(this)
                .transition()
                .duration(150)
                .style("opacity", 1.0);

            const sign = d.deviation >= 0 ? "+" : "";

            tooltip.style("display", "block")
                .html(`
                    <strong>${d.tag}</strong>
                    <div style="font-size: 10px; color: #94a3b8; margin-top: 2px;">
                        Sample Count: ${d.count} ratings
                    </div>
                    <div style="margin-top: 6px; font-size: 11px;">
                        Average Rating: <span style="font-weight: bold; color: #ffffff;">${d.avgScore.toFixed(2)} / 5.0</span>
                    </div>
                    <div style="margin-top: 6px; font-size: 10px; color: ${d.deviation >= 0 ? '#a7f3d0' : '#fca5a5'};">
                        Shift: <strong>${sign}${d.deviation.toFixed(2)}</strong> from baseline
                    </div>
                `);
        })
        .on("mousemove", function(event) {
            tooltip
                .style("left", (event.pageX + 12) + "px")
                .style("top", (event.pageY - 20) + "px");
        })
        .on("mouseleave", function() {
            d3.select(this)
                .transition()
                .duration(150)
                .style("opacity", 0.85);
            tooltip.style("display", "none");
        });
}

function renderActivityFeed(rows) {
    activityStream.innerHTML = "";

    if (rows.length === 0) {
        activityStream.innerHTML = `<div class="activity-loading"><span class="skeleton-pulse"></span> Awaiting submissions...</div>`;
        if (streamCount) streamCount.innerText = "0";
        return;
    }

    if (streamCount) streamCount.innerText = rows.length;

    rows.forEach(row => {
        const meta = DASHBOARDS_METADATA[row.dashboard_id];
        const modelName = meta ? meta.model : row.model;
        const frameworkStr = row.framework ? row.framework.toUpperCase() : "PY";

        const item = document.createElement("div");
        item.className = "activity-item";

        const tagsHtml = row.feedback_words
            ? row.feedback_words.split(",").map(t => `<span class="activity-tag">${t.trim()}</span>`).join("")
            : "";

        let commentText = "";
        if (row.tier === "S" || row.tier === "A") commentText = row.top_reason;
        else if (row.tier === "D" || row.tier === "C") commentText = row.bottom_reason;

        const displayComment = commentText ? `<div class="activity-feedback">"${commentText}"</div>` : "";

        item.innerHTML = `
            <div class="activity-meta">
                <span class="activity-model">${modelName} <span style="color: var(--text-dim); font-weight: 400;">(${frameworkStr})</span></span>
                <span class="activity-tier tier-${row.tier.toLowerCase()}">${row.tier}</span>
            </div>
            ${displayComment}
            <div class="activity-tags">
                ${tagsHtml}
            </div>
        `;
        activityStream.appendChild(item);
    });
}

function subscribeToRealtime() {
    supabaseClient
        .channel("realtime-analytics-stream")
        .on("postgres_changes", { event: "INSERT", schema: "public", table: "dashboard_tiered_rankings_python" }, (payload) => {
            const newRow = payload.new;
            if (newRow) {
                rawDbRows.unshift(newRow);
                processAndRenderAnalytics();
                updateLastUpdated();

                const streamItems = activityStream.getElementsByClassName("activity-item");
                if (streamItems.length > 0) {
                    const firstItem = streamItems[0];
                    firstItem.classList.add("flash");
                    setTimeout(() => firstItem.classList.remove("flash"), 1500);
                }
            }
        })
        .subscribe();
}

function exportCSV() {
    if (standingsList.length === 0) return;

    const headers = ["Rank", "Model", "Approach", "Framework", "Avg Rating", "Votes", "Time (s)", "Cost ($)"];
    const rows = standingsList.map((item, idx) => {
        return [
            idx + 1,
            item.modelName,
            item.arm === "skills" ? "Skills Guidelines" : "Vanilla Prompting",
            item.framework.toUpperCase(),
            item.votes > 0 ? item.avg.toFixed(2) : "—",
            item.votes,
            item.time,
            item.cost.toFixed(4)
        ];
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "analytics-export-" + new Date().toISOString().slice(0, 10) + ".csv";
    link.click();
    URL.revokeObjectURL(link.href);
}

function setupBeeswarmToggles() {
    const toggleBtns = document.querySelectorAll(".toggle-btn");
    toggleBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            toggleBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentBeeswarmGroup = btn.getAttribute("data-group");
            renderBeeswarm(rawDbRows);
        });
    });
}

function renderBeeswarm(rows) {
    if (!rows || rows.length === 0) return;

    const svg = d3.select("#beeswarm-svg");
    svg.selectAll("*").remove();

    const container = svg.node().parentElement;
    const width = container.clientWidth || 800;
    const height = 380;
    svg.attr("width", width).attr("height", height);

    const tiers = ["S", "A", "B", "C", "D"];
    const yScale = d3.scalePoint()
        .domain(tiers)
        .range([50, height - 50]);

    // Draw horizontal guidelines
    tiers.forEach(tier => {
        svg.append("line")
            .attr("class", "beeswarm-axis-line")
            .attr("x1", 90)
            .attr("y1", yScale(tier))
            .attr("x2", width - 40)
            .attr("y2", yScale(tier));

        svg.append("text")
            .attr("class", "beeswarm-axis-label")
            .attr("x", 45)
            .attr("y", yScale(tier))
            .attr("dy", "0.35em")
            .attr("text-anchor", "middle")
            .text(tier + " Tier");
    });

    // Grouping
    let groups = [];
    if (currentBeeswarmGroup === "model") {
        groups = Array.from(new Set(rows.map(r => {
            const meta = DASHBOARDS_METADATA[r.dashboard_id];
            return meta ? meta.model : r.model;
        })));
        groups.sort();
    } else if (currentBeeswarmGroup === "arm") {
        groups = ["skills", "vanilla"];
    } else if (currentBeeswarmGroup === "framework") {
        groups = ["python", "r"];
    }

    const xScale = d3.scalePoint()
        .domain(groups)
        .range([groups.length > 2 ? 160 : 250, groups.length > 2 ? width - 80 : width - 200]);

    // Draw header labels for each column/group
    groups.forEach(groupName => {
        let label = groupName;
        if (groupName === "skills") label = "Skills Guidelines";
        else if (groupName === "vanilla") label = "Vanilla Prompting";
        else if (groupName === "python") label = "Python Shiny";
        else if (groupName === "r") label = "R Shiny";

        svg.append("text")
            .attr("x", xScale(groupName))
            .attr("y", 24)
            .attr("text-anchor", "middle")
            .style("font-family", "var(--font-heading)")
            .style("font-size", "11px")
            .style("font-weight", "800")
            .style("fill", "var(--text-main)")
            .text(label);
    });

    // Create node objects
    const nodes = rows.map((r, i) => {
        const meta = DASHBOARDS_METADATA[r.dashboard_id];
        const modelName = meta ? meta.model : r.model;
        const approach = meta ? meta.arm : r.arm;
        const framework = meta ? meta.framework : r.framework;

        let groupVal = "";
        if (currentBeeswarmGroup === "model") {
            groupVal = modelName;
        } else if (currentBeeswarmGroup === "arm") {
            groupVal = approach;
        } else if (currentBeeswarmGroup === "framework") {
            groupVal = framework;
        }

        return {
            id: i,
            tier: r.tier,
            model: modelName,
            approach: approach,
            framework: framework,
            feedback: r.feedback_words || "",
            topReason: r.top_reason || "",
            bottomReason: r.bottom_reason || "",
            targetX: xScale(groupVal) || (width / 2),
            targetY: yScale(r.tier) || (height / 2),
            x: xScale(groupVal) + (Math.random() - 0.5) * 10,
            y: yScale(r.tier) + (Math.random() - 0.5) * 10
        };
    });

    // Run force simulation statically
    const simulation = d3.forceSimulation(nodes)
        .force("x", d3.forceX(d => d.targetX).strength(0.85))
        .force("y", d3.forceY(d => d.targetY).strength(0.85))
        .force("collide", d3.forceCollide(7))
        .stop();

    for (let i = 0; i < 120; ++i) simulation.tick();

    // Color mapper matching standard Tier colors
    const colors = {
        "S": "#ff8b94",
        "A": "#ffcaa6",
        "B": "#ffdca3",
        "C": "#d8f8a8",
        "D": "#a8f8b4"
    };

    // Tooltip
    let tooltip = d3.select("#beeswarm-tooltip");
    if (tooltip.empty()) {
        tooltip = d3.select("body").append("div")
            .attr("id", "beeswarm-tooltip")
            .attr("class", "beeswarm-tooltip");
    }

    const circles = svg.selectAll("circle")
        .data(nodes, d => d.id)
        .join("circle")
        .attr("class", "beeswarm-node")
        .attr("r", 6)
        .attr("fill", d => colors[d.tier] || "#94a3b8")
        .attr("cx", d => d.x)
        .attr("cy", d => d.y);

    // Dynamic hover behaviors
    circles
        .on("mouseenter", function(event, d) {
            d3.select(this)
                .transition()
                .duration(150)
                .attr("r", 9)
                .style("stroke-width", "2px");

            let commentHtml = "";
            let comment = "";
            if (d.tier === "S" || d.tier === "A") comment = d.topReason;
            else if (d.tier === "D" || d.tier === "C") comment = d.bottomReason;

            if (comment) {
                commentHtml = `<div style="font-style: italic; margin-top: 6px; border-left: 2px solid #38bdf8; padding-left: 6px; color: #cbd5e1;">"${comment}"</div>`;
            }

            let tagsHtml = "";
            if (d.feedback) {
                tagsHtml = `<div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px;">${
                    d.feedback.split(",").map(t => `<span style="font-size: 8px; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 2px 5px; border-radius: 4px;">${t.trim()}</span>`).join("")
                }</div>`;
            }

            tooltip.style("display", "block")
                .html(`
                    <strong>${d.model}</strong>
                    <div style="font-size: 10px; color: #94a3b8; margin-top: 2px;">
                        Tier: <span style="font-weight: bold; color: #ffffff;">${d.tier}</span> · 
                        Approach: <span style="text-transform: capitalize;">${d.approach}</span> · 
                        Framework: <span style="text-transform: uppercase;">${d.framework}</span>
                    </div>
                    ${tagsHtml}
                    ${commentHtml}
                `);
        })
        .on("mousemove", function(event) {
            tooltip
                .style("left", (event.pageX + 12) + "px")
                .style("top", (event.pageY - 20) + "px");
        })
        .on("mouseleave", function() {
            d3.select(this)
                .transition()
                .duration(150)
                .attr("r", 6)
                .style("stroke-width", "1px");
            tooltip.style("display", "none");
        });
}

init();

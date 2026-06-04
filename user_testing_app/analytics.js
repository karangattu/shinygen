const SUPABASE_URL = "https://ovwktjjeoowlktdfbuuu.supabase.co";
const SUPABASE_KEY = "sb_publishable_B2pz5WTA3UEVUeKACIgmBw_8_r0S3kU";
const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

const DASHBOARDS_METADATA = {
    "py-ds-v4-pro-skills": { name: "Dashboard 1", model: "DeepSeek V4 Pro", arm: "skills", cost: 0.1038, time: 508, framework: "python" },
    "py-claude-opus-skills": { name: "Dashboard 2", model: "Claude Opus 4-8", arm: "skills", cost: 1.4623, time: 309, framework: "python" },
    "py-ds-v4-flash-skills": { name: "Dashboard 3", model: "DeepSeek V4 Flash", arm: "skills", cost: 0.0127, time: 270, framework: "python" },
    "py-gpt-5-5-skills": { name: "Dashboard 4", model: "GPT 5.5", arm: "skills", cost: 0.4274, time: 196, framework: "python" },
    "py-minimax-m3-skills": { name: "Dashboard 5", model: "Minimax M3", arm: "skills", cost: 0.1037, time: 519, framework: "python" },
    "py-qwen-max-skills": { name: "Dashboard 6", model: "Qwen 3.7 Max", arm: "skills", cost: 0.5410, time: 261, framework: "python" },
    "py-ds-v4-pro-vanilla": { name: "Dashboard 7", model: "DeepSeek V4 Pro", arm: "vanilla", cost: 0.0862, time: 570, framework: "python" },
    "py-claude-opus-vanilla": { name: "Dashboard 8", model: "Claude Opus 4-8", arm: "vanilla", cost: 0.4908, time: 142, framework: "python" },
    "py-ds-v4-flash-vanilla": { name: "Dashboard 9", model: "DeepSeek V4 Flash", arm: "vanilla", cost: 0.0020, time: 92, framework: "python" },
    "r-claude-opus-skills": { name: "Dashboard 10", model: "Claude Opus 4-8", arm: "skills", cost: 0.5229, time: 188, framework: "r" },
    "r-ds-v4-flash-skills": { name: "Dashboard 11", model: "DeepSeek V4 Flash", arm: "skills", cost: 0.0043, time: 133, framework: "r" },
    "r-ds-v4-pro-skills": { name: "Dashboard 12", model: "DeepSeek V4 Pro", arm: "skills", cost: 0.0467, time: 277, framework: "r" },
    "r-gpt-5-5-skills": { name: "Dashboard 13", model: "GPT 5.5", arm: "skills", cost: 0.5972, time: 267, framework: "r" },
    "r-minimax-m3-skills": { name: "Dashboard 14", model: "Minimax M3", arm: "skills", cost: 0.0869, time: 415, framework: "r" },
    "r-qwen-max-skills": { name: "Dashboard 15", model: "Qwen 3.7 Max", arm: "skills", cost: 0.2984, time: 116, framework: "r" },
    "r-claude-opus-vanilla": { name: "Dashboard 16", model: "Claude Opus 4-8", arm: "vanilla", cost: 0.4266, time: 123, framework: "r" },
    "r-ds-v4-flash-vanilla": { name: "Dashboard 17", model: "DeepSeek V4 Flash", arm: "vanilla", cost: 0.0029, time: 129, framework: "r" },
    "r-ds-v4-pro-vanilla": { name: "Dashboard 18", model: "DeepSeek V4 Pro", arm: "vanilla", cost: 0.0905, time: 603, framework: "r" },
    "r-gpt-5-5-vanilla": { name: "Dashboard 19", model: "GPT 5.5", arm: "vanilla", cost: 0.4408, time: 203, framework: "r" },
    "r-minimax-m3-vanilla": { name: "Dashboard 20", model: "Minimax M3", arm: "vanilla", cost: 0.0247, time: 163, framework: "r" },
    "r-qwen-max-vanilla": { name: "Dashboard 21", model: "Qwen 3.7 Max", arm: "vanilla", cost: 0.1523, time: 103, framework: "r" }
};

const TIER_SCORES = { "S": 5, "A": 4, "B": 3, "C": 2, "D": 1 };

let rawDbRows = [];
let standingsList = [];
let chartRoiInstance = null;
let chartSkillsInstance = null;
let chartFrameworkInstance = null;
let chartTagsInstance = null;

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
    renderTagsChart(rawDbRows);
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

function renderRoiChart(standings) {
    const ctx = document.getElementById("chart-roi").getContext("2d");
    const activeData = standings.filter(s => s.votes > 0);

    if (chartRoiInstance) chartRoiInstance.destroy();

    const skillsData = activeData.filter(s => s.arm === "skills").map(s => ({
        x: s.cost, y: s.avg, label: s.modelName + " (" + s.framework.toUpperCase() + ")"
    }));
    const vanillaData = activeData.filter(s => s.arm === "vanilla").map(s => ({
        x: s.cost, y: s.avg, label: s.modelName + " (" + s.framework.toUpperCase() + ")"
    }));

    chartRoiInstance = new Chart(ctx, {
        type: "scatter",
        data: {
            datasets: [{
                label: "Skills Guidelines",
                data: skillsData,
                backgroundColor: "rgba(0, 240, 255, 0.7)",
                borderColor: "#00f0ff",
                borderWidth: 1,
                pointRadius: 7,
                pointHoverRadius: 10,
                pointHoverBackgroundColor: "#00f0ff"
            }, {
                label: "Vanilla Prompting",
                data: vanillaData,
                backgroundColor: "rgba(255, 0, 127, 0.7)",
                borderColor: "#ff007f",
                borderWidth: 1,
                pointRadius: 7,
                pointHoverRadius: 10,
                pointHoverBackgroundColor: "#ff007f"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: { display: true, text: "Cost per Generation ($)", color: "#8896b6", font: { weight: "600", size: 11 } },
                    grid: { color: "rgba(255, 255, 255, 0.04)" },
                    ticks: { color: "#4a5578" }
                },
                y: {
                    title: { display: true, text: "Avg Tier Rating", color: "#8896b6", font: { weight: "600", size: 11 } },
                    grid: { color: "rgba(255, 255, 255, 0.04)" },
                    ticks: { color: "#4a5578" },
                    min: 1, max: 5
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: "#8896b6",
                        font: { family: "Outfit", size: 11 },
                        usePointStyle: true,
                        padding: 16
                    }
                },
                tooltip: {
                    backgroundColor: "rgba(7, 11, 20, 0.9)",
                    titleColor: "#f1f5f9",
                    bodyColor: "#8896b6",
                    borderColor: "rgba(255, 255, 255, 0.08)",
                    borderWidth: 1,
                    padding: 10,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(ctx) {
                            const p = ctx.raw;
                            return p.label + ": " + p.y.toFixed(2) + " / $" + p.x.toFixed(4);
                        }
                    }
                }
            }
        }
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
                    "rgba(0, 240, 255, 0.25)",
                    "rgba(255, 0, 127, 0.25)"
                ],
                borderColor: ["#00f0ff", "#ff007f"],
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
                    grid: { color: "rgba(255, 255, 255, 0.04)" },
                    ticks: { color: "#4a5578" },
                    min: 0, max: 5
                },
                x: {
                    grid: { display: false },
                    ticks: { color: "#8896b6", font: { size: 11 } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "rgba(7, 11, 20, 0.9)",
                    titleColor: "#f1f5f9",
                    bodyColor: "#8896b6",
                    borderColor: "rgba(255, 255, 255, 0.08)",
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
                    ctx2.fillStyle = "#8896b6";
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
                    grid: { color: "rgba(255, 255, 255, 0.04)" },
                    ticks: { color: "#4a5578" },
                    min: 0, max: 5
                },
                x: {
                    grid: { display: false },
                    ticks: { color: "#8896b6", font: { size: 11 } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "rgba(7, 11, 20, 0.9)",
                    titleColor: "#f1f5f9",
                    bodyColor: "#8896b6",
                    borderColor: "rgba(255, 255, 255, 0.08)",
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
                    ctx2.fillStyle = "#8896b6";
                    ctx2.font = "600 11px Outfit";
                    ctx2.textAlign = "center";
                    ctx2.fillText(val.toFixed(2), bar.x, bar.y - 8);
                    ctx2.restore();
                });
            }
        }]
    });
}

function renderTagsChart(rows) {
    const ctx = document.getElementById("chart-tags").getContext("2d");

    const tagCount = {};
    rows.forEach(r => {
        if (r.feedback_words) {
            r.feedback_words.split(",").forEach(tag => {
                const cleanTag = tag.trim();
                if (cleanTag) {
                    tagCount[cleanTag] = (tagCount[cleanTag] || 0) + 1;
                }
            });
        }
    });

    const sortedTags = Object.keys(tagCount).map(k => ({ tag: k, count: tagCount[k] }));
    sortedTags.sort((a, b) => b.count - a.count);

    const labels = sortedTags.slice(0, 8).map(s => s.tag);
    const data = sortedTags.slice(0, 8).map(s => s.count);

    if (chartTagsInstance) chartTagsInstance.destroy();

    const maxCount = Math.max(...data, 1);

    chartTagsInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: data.map(v => {
                    const intensity = 0.15 + (v / maxCount) * 0.45;
                    return `rgba(0, 240, 255, ${intensity})`;
                }),
                borderColor: data.map(v => {
                    const intensity = 0.3 + (v / maxCount) * 0.7;
                    return `rgba(0, 240, 255, ${intensity})`;
                }),
                borderWidth: 2,
                borderRadius: 4,
                barPercentage: 0.6
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: "rgba(255, 255, 255, 0.04)" },
                    ticks: { color: "#4a5578", stepSize: 1 }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: "#8896b6", font: { size: 10 } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "rgba(7, 11, 20, 0.9)",
                    titleColor: "#f1f5f9",
                    bodyColor: "#8896b6",
                    borderColor: "rgba(255, 255, 255, 0.08)",
                    borderWidth: 1,
                    padding: 10,
                    cornerRadius: 8
                }
            }
        }
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

    let csv = headers.join(",") + "\n";
    rows.forEach(row => {
        csv += row.join(",") + "\n";
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "analytics-export-" + new Date().toISOString().slice(0, 10) + ".csv";
    link.click();
    URL.revokeObjectURL(link.href);
}

init();

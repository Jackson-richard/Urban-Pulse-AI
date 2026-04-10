const API_BASE = window.location.origin;
const POLL_INTERVAL = 2000;
const FORECAST_INTERVAL = 5000;
const ADVANCED_INTERVAL = 3000;
const CONFIG_INTERVAL = 10000;

const chartLabels = [];
const densityData = [];
const speedData = [];
const riskData = [];
const forecastData = [];
let trendChart = null;
let updateCount = 0;
let lastRiskLevel = "Low";
let alertCooldown = false;

const RISK_MAP = {
    "Low":    { color: "#10b981", icon: "✅", score: 1 },
    "Medium": { color: "#f59e0b", icon: "⚠️", score: 2 },
    "High":   { color: "#ef4444", icon: "🚨", score: 3 },
};

// Sound alert using Web Audio API
function playAlertSound() {
    if (alertCooldown) return;
    alertCooldown = true;
    setTimeout(() => { alertCooldown = false; }, 15000);

    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const playBeep = (freq, startTime, duration) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = freq;
            osc.type = "sine";
            gain.gain.setValueAtTime(0.3, startTime);
            gain.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
            osc.start(startTime);
            osc.stop(startTime + duration);
        };
        const now = ctx.currentTime;
        playBeep(880, now, 0.15);
        playBeep(880, now + 0.2, 0.15);
        playBeep(1100, now + 0.4, 0.3);
    } catch (e) { /* audio not available */ }
}

function initChart() {
    const ctx = document.getElementById("trendChart").getContext("2d");
    trendChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: chartLabels,
            datasets: [
                {
                    label: "Density",
                    data: densityData,
                    borderColor: "#06b6d4",
                    backgroundColor: "rgba(6, 182, 212, 0.1)",
                    fill: true, tension: 0.4, borderWidth: 2,
                    pointRadius: 0, pointHoverRadius: 4,
                },
                {
                    label: "Speed (÷10)",
                    data: speedData,
                    borderColor: "#8b5cf6",
                    backgroundColor: "rgba(139, 92, 246, 0.1)",
                    fill: true, tension: 0.4, borderWidth: 2,
                    pointRadius: 0, pointHoverRadius: 4,
                },
                {
                    label: "Risk Score",
                    data: riskData,
                    borderColor: "#f59e0b",
                    backgroundColor: "rgba(245, 158, 11, 0.05)",
                    fill: false, tension: 0.3, borderWidth: 2,
                    borderDash: [5, 5],
                    pointRadius: 0, pointHoverRadius: 4,
                },
                {
                    label: "Forecast",
                    data: forecastData,
                    borderColor: "rgba(139, 92, 246, 0.6)",
                    backgroundColor: "rgba(139, 92, 246, 0.05)",
                    fill: false, tension: 0.3, borderWidth: 2,
                    borderDash: [3, 6],
                    pointRadius: 3, pointStyle: "triangle",
                    pointBackgroundColor: "#8b5cf6",
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: "index" },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "rgba(17, 24, 39, 0.95)",
                    titleColor: "#f1f5f9", bodyColor: "#94a3b8",
                    borderColor: "rgba(255, 255, 255, 0.1)", borderWidth: 1,
                    cornerRadius: 8, padding: 12,
                },
            },
            scales: {
                x: {
                    display: true,
                    grid: { color: "rgba(255,255,255,0.03)" },
                    ticks: { color: "#64748b", font: { size: 10 }, maxTicksLimit: 10 },
                },
                y: {
                    display: true,
                    grid: { color: "rgba(255,255,255,0.03)" },
                    ticks: { color: "#64748b", font: { size: 10 } },
                    min: 0,
                },
            },
        },
    });
}

function updateZones(zones, hottestZone) {
    if (!zones) return;
    const zoneIds = ["A1", "A2", "B1", "B2"];
    zoneIds.forEach(z => {
        const el = document.getElementById("zone" + z);
        if (!el) return;
        const count = zones[z] || 0;
        el.querySelector(".zone-count").textContent = count;

        el.classList.remove("zone-low", "zone-med", "zone-high", "zone-hot");
        if (count >= 4) el.classList.add("zone-high");
        else if (count >= 2) el.classList.add("zone-med");
        else el.classList.add("zone-low");

        if (z === hottestZone && count > 0) el.classList.add("zone-hot");
    });

    const badge = document.getElementById("hotzoneBadge");
    if (badge) {
        const hotCount = zones[hottestZone] || 0;
        badge.textContent = `🔥 Hot: ${hottestZone} (${hotCount}p)`;
    }
}

function updateDashboard(data) {
    if (data.status === "no_data") return;

    updateCount++;

    document.getElementById("densityValue").textContent = data.density.toFixed(1);
    document.getElementById("speedValue").textContent = data.speed.toFixed(1);
    document.getElementById("riskValue").textContent = data.risk_level;
    document.getElementById("riskConfText").textContent = `confidence: ${(data.confidence * 100).toFixed(0)}%`;
    document.getElementById("flowValue").textContent = data.flow_direction || "—";

    const riskInfo = RISK_MAP[data.risk_level] || RISK_MAP["Low"];
    document.getElementById("riskValue").style.color = riskInfo.color;

    const gaugePercent = (riskInfo.score / 3) * 100;
    const gaugeFill = document.getElementById("gaugeFill");
    gaugeFill.style.width = gaugePercent + "%";
    gaugeFill.style.background = riskInfo.color;

    const banner = document.getElementById("riskBanner");
    banner.className = "risk-banner risk-" + data.risk_level.toLowerCase();
    document.getElementById("riskIcon").textContent = riskInfo.icon;
    document.getElementById("riskLabel").textContent = `CONGESTION RISK: ${data.risk_level.toUpperCase()}`;
    document.getElementById("riskLabel").style.color = riskInfo.color;
    document.getElementById("riskReason").textContent = data.reason;
    document.getElementById("riskConfidence").textContent = (data.confidence * 100).toFixed(0) + "%";
    document.getElementById("riskConfidence").style.color = riskInfo.color;

    // Sound alert on HIGH
    if (data.risk_level === "High" && lastRiskLevel !== "High") {
        playAlertSound();
    }
    lastRiskLevel = data.risk_level;

    // Zone heatmap
    updateZones(data.zones, data.hottest_zone);

    // Chart
    const now = new Date();
    const timeLabel = now.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });

    chartLabels.push(timeLabel);
    densityData.push(data.density);
    speedData.push(data.speed / 10);
    riskData.push(riskInfo.score);
    forecastData.push(null);

    if (chartLabels.length > 50) {
        chartLabels.shift();
        densityData.shift();
        speedData.shift();
        riskData.shift();
        forecastData.shift();
    }

    trendChart.update("none");

    animateValue("densityValue");
    animateValue("speedValue");
}

function animateValue(elementId) {
    const el = document.getElementById(elementId);
    el.style.transform = "scale(1.05)";
    el.style.transition = "transform 0.2s ease";
    setTimeout(() => { el.style.transform = "scale(1)"; }, 200);
}

async function pollLatest() {
    try {
        const response = await fetch(`${API_BASE}/latest`);
        const data = await response.json();
        const badge = document.getElementById("statusBadge");
        badge.className = "status-badge connected";
        badge.querySelector("span").textContent = "Live";
        updateDashboard(data);
    } catch (err) {
        const badge = document.getElementById("statusBadge");
        badge.className = "status-badge disconnected";
        badge.querySelector("span").textContent = "Disconnected";
    }
}

async function pollForecast() {
    try {
        const response = await fetch(`${API_BASE}/forecast`);
        const data = await response.json();
        const statusEl = document.getElementById("forecastStatus");

        if (data.status === "ok") {
            statusEl.textContent = "Active";
            statusEl.style.color = "#10b981";
            statusEl.style.background = "rgba(16, 185, 129, 0.12)";

            const riskInfo = RISK_MAP[data.predicted_risk] || RISK_MAP["Low"];

            document.getElementById("forecastDensity").textContent = data.predicted_density.toFixed(1);
            const riskEl = document.getElementById("forecastRisk");
            riskEl.textContent = data.predicted_risk;
            riskEl.style.color = riskInfo.color;
            document.getElementById("forecastConf").textContent = (data.risk_confidence * 100).toFixed(0) + "%";
            document.getElementById("forecastSnapshots").textContent = data.based_on_snapshots + " snapshots";

            // Add forecast point to chart
            if (forecastData.length > 0) {
                forecastData[forecastData.length - 1] = data.predicted_density;
                trendChart.update("none");
            }
        } else {
            statusEl.textContent = data.message || "Waiting...";
            statusEl.style.color = "";
            statusEl.style.background = "";
        }
    } catch (err) { /* ignore */ }
}

// ═══════════════════════════════════════════════════════
// ADVANCED FEATURE: Route Recommendations
// ═══════════════════════════════════════════════════════

function updateRouteRecommendations(recs) {
    const listEl = document.getElementById("routeList");
    const statusEl = document.getElementById("routeStatus");
    if (!listEl) return;

    if (!recs || recs.length === 0) {
        listEl.innerHTML = '<div class="route-empty">No recommendations available.</div>';
        statusEl.textContent = "Idle";
        return;
    }

    const hasHigh = recs.some(r => r.priority === "high");
    statusEl.textContent = hasHigh ? "⚡ Active" : "Monitoring";
    statusEl.style.color = hasHigh ? "#ef4444" : "#10b981";
    statusEl.style.background = hasHigh ? "rgba(239, 68, 68, 0.12)" : "rgba(16, 185, 129, 0.12)";

    listEl.innerHTML = recs.map(rec => `
        <div class="route-card priority-${rec.priority}">
            <span class="route-icon">${rec.icon || '🔀'}</span>
            <span class="route-action">${rec.action}</span>
            <span class="route-priority">${rec.priority}</span>
        </div>
    `).join("");
}


// ═══════════════════════════════════════════════════════
// ADVANCED FEATURE: Spatiotemporal Zone Forecast
// ═══════════════════════════════════════════════════════

function updateSpatiotemporal(spatio) {
    const zoneEl = document.getElementById("spatioZone");
    const timeEl = document.getElementById("spatioTime");
    const statusEl = document.getElementById("spatioStatus");
    const barsEl = document.getElementById("trendBars");
    if (!zoneEl || !spatio) return;

    // Update zone display
    zoneEl.textContent = spatio.predicted_next_hot_zone || "—";

    // Update time display
    if (spatio.estimated_time_to_congestion_minutes !== null && spatio.estimated_time_to_congestion_minutes !== undefined) {
        if (spatio.estimated_time_to_congestion_minutes === 0) {
            timeEl.textContent = "NOW";
            timeEl.style.color = "#ef4444";
        } else {
            timeEl.textContent = `${spatio.estimated_time_to_congestion_minutes}m`;
            timeEl.style.color = spatio.estimated_time_to_congestion_minutes < 2 ? "#f59e0b" : "#06b6d4";
        }
    } else {
        timeEl.textContent = "—";
        timeEl.style.color = "";
    }

    // Status badge
    const conf = spatio.confidence || 0;
    statusEl.textContent = conf > 0.6 ? `${(conf * 100).toFixed(0)}% conf.` : "Gathering data...";
    statusEl.style.color = conf > 0.6 ? "#10b981" : "";
    statusEl.style.background = conf > 0.6 ? "rgba(16, 185, 129, 0.12)" : "";

    // Trend bars
    const trends = spatio.trend_summary || {};
    const zones = Object.keys(trends);
    if (zones.length > 0 && barsEl) {
        const maxAbs = Math.max(0.1, ...zones.map(z => Math.abs(trends[z])));
        barsEl.innerHTML = zones.map(z => {
            const val = trends[z];
            const pct = Math.min(100, (Math.abs(val) / maxAbs) * 100);
            const cls = val > 0.05 ? "rising" : val < -0.05 ? "falling" : "stable";
            const valCls = val > 0 ? "positive" : val < 0 ? "negative" : "neutral";
            return `
                <div class="trend-bar-item">
                    <span class="trend-bar-label">${z}</span>
                    <div class="trend-bar-track">
                        <div class="trend-bar-fill ${cls}" style="width: ${Math.max(8, pct)}%"></div>
                    </div>
                    <span class="trend-bar-value ${valCls}">${val > 0 ? '+' : ''}${val.toFixed(2)}</span>
                </div>
            `;
        }).join("");
    }
}


// ═══════════════════════════════════════════════════════
// ADVANCED FEATURE: Explainable AI Reasoning
// ═══════════════════════════════════════════════════════

function updateExplainableAI(xai) {
    const factorsEl = document.getElementById("xaiFactors");
    const summaryEl = document.getElementById("xaiSummary");
    const thresholdsEl = document.getElementById("xaiThresholds");
    if (!factorsEl || !xai || !xai.factors) return;

    // Summary
    summaryEl.textContent = xai.summary || "Analysis in progress...";

    // Factor cards
    factorsEl.innerHTML = xai.factors.map(f => `
        <div class="xai-factor-card impact-ring-${f.impact}">
            <span class="xai-factor-icon">${f.icon || '📊'}</span>
            <div class="xai-factor-body">
                <div class="xai-factor-name">
                    ${f.factor.replace('_', ' ')}
                    <span class="xai-impact-badge impact-${f.impact}">${f.impact}</span>
                </div>
                <div class="xai-factor-detail">${f.detail}</div>
            </div>
        </div>
    `).join("");

    // Threshold pills
    if (xai.threshold_status && thresholdsEl) {
        const ts = xai.threshold_status;
        thresholdsEl.innerHTML = `
            <div class="xai-threshold-pill">
                <span class="threshold-dot ${ts.density_exceeded ? 'exceeded' : 'ok'}"></span>
                Density threshold (${ts.density_threshold}): ${ts.density_exceeded ? 'EXCEEDED' : 'OK'}
            </div>
            <div class="xai-threshold-pill">
                <span class="threshold-dot ${ts.speed_below ? 'exceeded' : 'ok'}"></span>
                Speed threshold (${ts.speed_threshold} px/s): ${ts.speed_below ? 'BELOW' : 'OK'}
            </div>
        `;
    }
}


// ═══════════════════════════════════════════════════════
// v4.0 FEATURE: Anomaly / Panic Detection Banner
// ═══════════════════════════════════════════════════════

function updateAnomalyBanner(anomaly) {
    const banner = document.getElementById("anomalyBanner");
    if (!banner) return;

    if (!anomaly || !anomaly.anomaly_detected) {
        banner.style.display = "none";
        return;
    }

    banner.style.display = "block";
    banner.className = `anomaly-banner severity-${anomaly.anomaly_severity}`;

    document.getElementById("anomalyIcon").textContent = anomaly.anomaly_icon || "🚨";

    const typeLabels = {
        "panic_rush": "PANIC / RUSH EVENT",
        "chaotic_movement": "CHAOTIC CROWD MOVEMENT",
        "reverse_flow": "REVERSE CROWD FLOW",
    };
    document.getElementById("anomalyType").textContent =
        typeLabels[anomaly.anomaly_type] || anomaly.anomaly_type.toUpperCase();

    document.getElementById("anomalyReason").textContent = anomaly.anomaly_reason || "";

    const confEl = document.getElementById("anomalyConfidence");
    confEl.textContent = `${(anomaly.anomaly_confidence * 100).toFixed(0)}%`;
    confEl.style.color = anomaly.anomaly_severity === "critical" ? "#ef4444" : "#f59e0b";
}


// ═══════════════════════════════════════════════════════
// v4.0 FEATURE: Real-World Metrics Display
// ═══════════════════════════════════════════════════════

function updateRealworldMetrics(rw) {
    const speedEl = document.getElementById("speedRealworld");
    const densityEl = document.getElementById("densityRealworld");
    if (!speedEl || !densityEl) return;

    if (!rw || !rw.calibration_enabled) {
        speedEl.classList.remove("visible");
        densityEl.classList.remove("visible");
        return;
    }

    // Speed: show m/s + context
    speedEl.innerHTML = `📊 ${rw.speed_m_s} m/s (${rw.speed_km_h} km/h) — ${rw.speed_context}`;
    speedEl.classList.add("visible");

    // Density: show people/m² + LOS grade
    const los = rw.level_of_service;
    densityEl.innerHTML = `📊 ${rw.density_per_sqm} ppl/m² — ${rw.density_context} <span class="los-badge los-${los}">LOS ${los}</span>`;
    densityEl.classList.add("visible");
}


// ═══════════════════════════════════════════════════════
// v4.0 FEATURE: Deployment Configuration Display
// ═══════════════════════════════════════════════════════

function updateDeployConfig(data) {
    const togglesEl = document.getElementById("deployToggles");
    const badgeEl = document.getElementById("deployModeBadge");
    if (!togglesEl || !data) return;

    badgeEl.textContent = data.active_modes || "Standard Mode";

    const config = data.config || {};
    const toggles = config.toggles || [];

    togglesEl.innerHTML = toggles.map(t => `
        <div class="deploy-toggle-card ${t.enabled ? 'active' : ''}" data-key="${t.key}" onclick="toggleDeployment('${t.key}', ${!t.enabled})">
            <span class="deploy-toggle-icon">${t.icon}</span>
            <div class="deploy-toggle-info">
                <div class="deploy-toggle-label">${t.label}</div>
                <div class="deploy-toggle-desc">${t.description}</div>
            </div>
            <div class="deploy-toggle-switch"></div>
        </div>
    `).join("");
}

async function toggleDeployment(key, enabled) {
    try {
        const response = await fetch(`${API_BASE}/config/toggle`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key, enabled }),
        });
        const data = await response.json();
        if (data.status === "ok") {
            updateDeployConfig(data);
        }
    } catch (err) { /* ignore */ }
}


// ═══════════════════════════════════════════════════════
// POLLING — Advanced + Spatiotemporal + Config endpoints
// ═══════════════════════════════════════════════════════

async function pollAdvanced() {
    try {
        const response = await fetch(`${API_BASE}/advanced`);
        const data = await response.json();
        if (data.status === "ok") {
            updateRouteRecommendations(data.route_recommendations);
            updateExplainableAI(data.risk_explanation);
            updateAnomalyBanner(data.anomaly);
            updateRealworldMetrics(data.realworld_metrics);
        }
    } catch (err) { /* ignore */ }
}

async function pollSpatiotemporal() {
    try {
        const response = await fetch(`${API_BASE}/spatiotemporal`);
        const data = await response.json();
        if (data.status === "ok") {
            updateSpatiotemporal(data.spatiotemporal);
        }
    } catch (err) { /* ignore */ }
}

async function pollConfig() {
    try {
        const response = await fetch(`${API_BASE}/config`);
        const data = await response.json();
        if (data.status === "ok") {
            updateDeployConfig(data);
        }
    } catch (err) { /* ignore */ }
}


async function testPredict() {
    const density = parseFloat(document.getElementById("testDensity").value);
    const speed = parseFloat(document.getElementById("testSpeed").value);
    if (isNaN(density) || isNaN(speed)) { alert("Please enter valid numbers."); return; }

    const btn = document.getElementById("testBtn");
    btn.textContent = "Predicting...";
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ density, speed }),
        });
        const data = await response.json();
        const riskInfo = RISK_MAP[data.risk_level] || RISK_MAP["Low"];
        const resultDiv = document.getElementById("testResult");
        resultDiv.innerHTML = `
            <div class="result-risk" style="color: ${riskInfo.color}">
                ${riskInfo.icon} Risk: ${data.risk_level} — ${(data.confidence * 100).toFixed(0)}% confidence
            </div>
            <div class="result-details">
                Density: ${data.density} ppl/Mpx  •  Speed: ${data.speed} px/s<br>
                ${data.reason}
            </div>
        `;
        resultDiv.classList.add("visible");

        // Also update advanced panels from the predict response
        if (data.route_recommendations) updateRouteRecommendations(data.route_recommendations);
        if (data.risk_explanation) updateExplainableAI(data.risk_explanation);
        if (data.spatiotemporal) updateSpatiotemporal(data.spatiotemporal);
        if (data.anomaly) updateAnomalyBanner(data.anomaly);
        if (data.realworld_metrics) updateRealworldMetrics(data.realworld_metrics);
    } catch (err) {
        const resultDiv = document.getElementById("testResult");
        resultDiv.innerHTML = `<div style="color: #ef4444;">❌ Could not connect to API.</div>`;
        resultDiv.classList.add("visible");
    }
    btn.textContent = "Predict";
    btn.disabled = false;
}

function updateClock() {
    const now = new Date();
    document.getElementById("clock").textContent = now.toLocaleTimeString("en-US", {
        hour12: true, hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initChart();
    updateClock();
    setInterval(updateClock, 1000);
    setInterval(pollLatest, POLL_INTERVAL);
    setInterval(pollForecast, FORECAST_INTERVAL);
    setInterval(pollAdvanced, ADVANCED_INTERVAL);
    setInterval(pollSpatiotemporal, ADVANCED_INTERVAL);
    setInterval(pollConfig, CONFIG_INTERVAL);
    pollLatest();
    pollForecast();
    pollAdvanced();
    pollSpatiotemporal();
    pollConfig();
});

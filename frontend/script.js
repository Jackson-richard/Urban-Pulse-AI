const API_BASE = window.location.origin;
const POLL_INTERVAL = 2000;
const FORECAST_INTERVAL = 5000;

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
    pollLatest();
    pollForecast();
});

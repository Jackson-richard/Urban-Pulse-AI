import streamlit as st
import requests
import time
import pandas as pd
import plotly.graph_objects as go
import subprocess
import os

# Configurations
API_URL = "http://localhost:8000"
st.set_page_config(page_title="Urban Pulse AI Dashboard", page_icon="🏙️", layout="wide")

# Custom CSS for advanced panels
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .alert-banner { 
        background-color: #ff4b4b; 
        color: white; 
        padding: 20px; 
        text-align: center; 
        border-radius: 10px; 
        font-size: 24px; 
        font-weight: bold; 
        margin-bottom: 20px; 
        animation: blinker 1.5s linear infinite; 
    }
    @keyframes blinker { 50% { opacity: 0.5; } }

    /* Route recommendation cards */
    .route-card {
        background: linear-gradient(135deg, rgba(30,30,50,0.9), rgba(20,20,40,0.95));
        border-radius: 10px; padding: 14px 18px; margin-bottom: 8px;
        border-left: 4px solid #06b6d4; color: #e2e8f0;
        font-size: 15px; display: flex; align-items: center; gap: 12px;
    }
    .route-card.high { border-left-color: #ef4444; }
    .route-card.medium { border-left-color: #f59e0b; }
    .route-card.low { border-left-color: #10b981; }
    .route-card .icon { font-size: 22px; }
    .route-card .priority-badge {
        font-size: 10px; text-transform: uppercase; letter-spacing: 1px;
        padding: 2px 8px; border-radius: 6px; font-weight: 700;
        margin-left: auto; white-space: nowrap;
    }
    .route-card.high .priority-badge { background: rgba(239,68,68,0.2); color: #ef4444; }
    .route-card.medium .priority-badge { background: rgba(245,158,11,0.2); color: #f59e0b; }
    .route-card.low .priority-badge { background: rgba(16,185,129,0.2); color: #10b981; }

    /* XAI factor cards */
    .xai-card {
        background: rgba(20,20,40,0.85); border-radius: 8px; padding: 12px 16px;
        margin-bottom: 6px; border-left: 3px solid #8b5cf6; color: #cbd5e1; font-size: 14px;
    }
    .xai-card.impact-high { border-left-color: #ef4444; }
    .xai-card.impact-medium { border-left-color: #f59e0b; }
    .xai-card.impact-low { border-left-color: #10b981; }
    .xai-card .factor-name {
        font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px;
        color: #64748b; margin-bottom: 4px;
    }
    .xai-card .factor-detail { color: #e2e8f0; font-weight: 500; }

    /* Threshold pills */
    .threshold-pill {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 600;
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
        margin-right: 8px; margin-top: 6px;
    }
    .threshold-dot {
        width: 8px; height: 8px; border-radius: 50%; display: inline-block;
    }
    .threshold-dot.exceeded { background: #ef4444; box-shadow: 0 0 6px #ef4444; }
    .threshold-dot.ok { background: #10b981; box-shadow: 0 0 6px #10b981; }

    /* Spatio hero display */
    .spatio-hero {
        text-align: center; padding: 16px;
        background: linear-gradient(135deg, rgba(30,30,60,0.9), rgba(20,20,45,0.95));
        border-radius: 12px; margin-bottom: 8px;
    }
    .spatio-zone-big {
        font-size: 42px; font-weight: 800; letter-spacing: -1px;
        background: linear-gradient(135deg, #f59e0b, #ef4444);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .spatio-time-big {
        font-size: 32px; font-weight: 800; color: #06b6d4;
    }

    /* v4.0: Anomaly Alert */
    .anomaly-alert {
        padding: 16px 22px; border-radius: 10px; margin-bottom: 12px;
        font-weight: 600; font-size: 15px;
        display: flex; align-items: center; gap: 14px;
    }
    .anomaly-critical {
        background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(220,38,38,0.10));
        border: 1px solid rgba(239,68,68,0.35); color: #fca5a5;
    }
    .anomaly-warning {
        background: linear-gradient(135deg, rgba(245,158,11,0.12), rgba(234,88,12,0.08));
        border: 1px solid rgba(245,158,11,0.30); color: #fde68a;
    }
    .anomaly-alert .anomaly-conf {
        margin-left: auto; font-size: 22px; font-weight: 800;
    }

    /* v4.0: Deploy toggle */
    .deploy-card {
        background: rgba(20,20,40,0.7); border-radius: 8px; padding: 10px 14px;
        margin-bottom: 6px; border-left: 3px solid #64748b; color: #94a3b8; font-size: 13px;
    }
    .deploy-card.active { border-left-color: #10b981; color: #e2e8f0; }
    .deploy-card .deploy-label { font-weight: 600; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

st.title("🏙️ Urban Pulse AI - Live Dashboard")

# --- FILE UPLOAD & ANALYTICS TRIGGER ---
st.sidebar.header("📁 Video Upload")
st.sidebar.markdown("Upload a standard video (MP4/AVI) to run real-time OpenCV tracking on it.")
uploaded_file = st.sidebar.file_uploader("Upload video", type=["mp4", "avi", "mov"])

if uploaded_file is not None:
    os.makedirs("data", exist_ok=True)
    video_path = os.path.join("data", "custom_uploaded_video.mp4")
    with open(video_path, "wb") as f:
        f.write(uploaded_file.read())
    st.sidebar.success("✅ Video uploaded successfully!")
    
    if st.sidebar.button("▶️ Start Processing Video"):
        subprocess.run(["powershell", "-Command", "Get-WmiObject Win32_Process -Filter \\\"CommandLine LIKE '%analytics.py%'\\\" | ForEach-Object { $_.Terminate() }"])
        time.sleep(1)
        subprocess.Popen(["python", "backend/analytics.py", "--source", video_path])
        st.sidebar.success("Analytics Engine Started! Please wait a moment for the AI to process frames.")


def fetch_data(endpoint):
    try:
        response = requests.get(f"{API_URL}/{endpoint}", timeout=1)
        if response.status_code == 200:
            return response.json()
    except Exception:
        return None

latest_data = fetch_data("latest")
forecast_data = fetch_data("forecast")
zones_data = fetch_data("zones")
history_data = fetch_data("history")
advanced_data = fetch_data("advanced")
spatiotemporal_data = fetch_data("spatiotemporal")
config_data = fetch_data("config")


SIREN_HTML = """
<audio autoplay loop>
    <source src="https://assets.mixkit.co/active_storage/sfx/995/995-preview.mp3" type="audio/mpeg">
</audio>
"""

# --- 5 MINUTE ALERT LOGIC ---
if "high_risk_start_time" not in st.session_state:
    st.session_state.high_risk_start_time = None

if latest_data and latest_data.get("status") != "no_data" and latest_data.get("risk_level") == "High":
    if st.session_state.high_risk_start_time is None:
        st.session_state.high_risk_start_time = time.time()
else:
    st.session_state.high_risk_start_time = None

if st.session_state.high_risk_start_time is not None:
    st.markdown(SIREN_HTML, unsafe_allow_html=True)

    duration_seconds = time.time() - st.session_state.high_risk_start_time
    if duration_seconds >= 300:
        st.markdown('<div class="alert-banner">🚨 CRITICAL ALERT: High Congestion Detected for over 5 Minutes! 🚨<br>Recommend Dispatching Crowd Control immediately!</div>', unsafe_allow_html=True)
    elif duration_seconds >= 1:
        mins = int(duration_seconds // 60)
        secs = int(duration_seconds % 60)
        st.warning(f"⚠️ **Warning:** Continuous High Risk detected for {mins}m {secs}s. Critical alert activates at 5m 0s.")


if advanced_data and advanced_data.get("status") == "ok":
    anomaly = advanced_data.get("anomaly", {})
    if anomaly.get("anomaly_detected"):
        severity = anomaly.get("anomaly_severity", "warning")
        css_class = "anomaly-critical" if severity == "critical" else "anomaly-warning"
        icon = anomaly.get("anomaly_icon", "🚨")
        atype = anomaly.get("anomaly_type", "").replace("_", " ").upper()
        reason = anomaly.get("anomaly_reason", "")
        conf = anomaly.get("anomaly_confidence", 0)
        st.markdown(
            f'<div class="anomaly-alert {css_class}">'
            f'<span style="font-size:28px;">{icon}</span>'
            f'<div><strong>{atype}</strong><br><span style="font-size:13px;opacity:0.8;">{reason}</span></div>'
            f'<span class="anomaly-conf">{conf:.0%}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# --- RENDER DATA ---
if not latest_data or latest_data.get("status") == "no_data":
    st.info("Waiting for data. Upload a video on the left sidebar and click 'Start Processing Video' to begin tracking people.")
else:
    st.subheader("Real-time Analytics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Crowd Density", f"{latest_data['density']:.2f}", f"{latest_data['trend']:+.2f}", delta_color="inverse")
    with col2:
        st.metric("Average Speed", f"{latest_data['speed']:.2f} px/s")
    with col3:
        st.metric("Flow Direction", latest_data["flow_direction"])
    with col4:
        st.metric("Risk Level", latest_data["risk_level"])

    # ── v4.0: Real-World Metrics (if calibration enabled) ──
    rw = latest_data.get("realworld_metrics") or (advanced_data.get("realworld_metrics") if advanced_data else None)
    if rw and rw.get("calibration_enabled"):
        rw_col1, rw_col2 = st.columns(2)
        with rw_col1:
            st.metric("Speed (Real)", f"{rw['speed_m_s']} m/s", f"{rw['speed_context']}")
        with rw_col2:
            st.metric("Density (Real)", f"{rw['density_per_sqm']} ppl/m²", f"LOS {rw['level_of_service']} — {rw['density_context']}")

    st.info(f"**Analysis:** {latest_data['reason']} *(Confidence: {latest_data['confidence']:.0%})*")
   
    col_z, col_f = st.columns(2)
    
    with col_z:
        st.subheader("🗺️ Zone Heatmap")
        if zones_data and "zones" in zones_data:
            zones = zones_data["zones"]
            st.write(f"**Hottest Zone:** {zones_data.get('hottest_zone', 'N/A')} | **Total Tracked:** {zones_data.get('total_people', 0)}")
            
            z1, z2 = st.columns(2)
            with z1:
                st.success(f"**Zone A1:** {zones.get('A1', 0)} people")
                st.success(f"**Zone B1:** {zones.get('B1', 0)} people")
            with z2:
                st.success(f"**Zone A2:** {zones.get('A2', 0)} people")
                st.success(f"**Zone B2:** {zones.get('B2', 0)} people")
        else:
            st.write("No zone data available.")

    with col_f:
        st.subheader("🔮 XGBoost Forecast")
        if forecast_data and forecast_data.get("status") == "ok":
            f1, f2 = st.columns(2)
            with f1:
                st.metric("Predicted Density", f"{forecast_data['predicted_density']:.2f}")
                st.metric("Predicted Risk", forecast_data['predicted_risk'])
            with f2:
                st.metric("Forecast Confidence", f"{forecast_data['risk_confidence']:.0%}")
                st.write(f"*Based on {forecast_data['based_on_snapshots']} recent snapshots.*")
        else:
            msg = forecast_data.get("message", "Waiting for enough snapshots...") if forecast_data else "Waiting for forecast data..."
            st.write(msg)

    st.markdown("---")
    col_route, col_spatio = st.columns(2)

    with col_route:
        st.subheader("🛤️ Route Recommendations")
        if advanced_data and advanced_data.get("status") == "ok":
            recs = advanced_data.get("route_recommendations", [])
            if recs:
                for rec in recs:
                    priority = rec.get("priority", "low")
                    icon = rec.get("icon", "🔀")
                    action = rec.get("action", "")
                    st.markdown(
                        f'<div class="route-card {priority}">'
                        f'<span class="icon">{icon}</span>'
                        f'<span>{action}</span>'
                        f'<span class="priority-badge">{priority.upper()}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.write("✅ No interventions needed — crowd flow is normal.")
        else:
            st.write("Waiting for analytics data to generate recommendations...")

    with col_spatio:
        st.subheader("⏱️ Next Congestion Forecast")
        if spatiotemporal_data and spatiotemporal_data.get("status") == "ok":
            spatio = spatiotemporal_data.get("spatiotemporal", {})
            predicted_zone = spatio.get("predicted_next_hot_zone", "N/A")
            eta = spatio.get("estimated_time_to_congestion_minutes")
            confidence = spatio.get("confidence", 0)
            trend_summary = spatio.get("trend_summary", {})

            s1, s2 = st.columns(2)
            with s1:
                st.markdown(
                    f'<div class="spatio-hero">'
                    f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#94a3b8;margin-bottom:6px;">Predicted Next Hot Zone</div>'
                    f'<div class="spatio-zone-big">{predicted_zone}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with s2:
                if eta is not None:
                    time_display = "NOW" if eta == 0 else f"{eta}m"
                    time_color = "#ef4444" if eta == 0 else ("#f59e0b" if eta < 2 else "#06b6d4")
                else:
                    time_display = "—"
                    time_color = "#94a3b8"
                st.markdown(
                    f'<div class="spatio-hero">'
                    f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#94a3b8;margin-bottom:6px;">Est. Time to Congestion</div>'
                    f'<div class="spatio-time-big" style="color:{time_color}">{time_display}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            if trend_summary:
                st.write("**Zone Trends:**")
                trend_cols = st.columns(len(trend_summary))
                for i, (zone_name, trend_val) in enumerate(trend_summary.items()):
                    with trend_cols[i]:
                        delta_color = "inverse" if trend_val > 0 else "normal"
                        st.metric(zone_name, f"{trend_val:+.2f}", delta=f"{trend_val:+.2f}", delta_color=delta_color)

            st.caption(f"Confidence: {confidence:.0%}")
        else:
            st.write("Waiting for enough zone history to forecast...")

    st.markdown("---")
    st.subheader("🧠 Explainable AI Reasoning")
    if advanced_data and advanced_data.get("status") == "ok":
        xai = advanced_data.get("risk_explanation", {})
        factors = xai.get("factors", [])
        summary = xai.get("summary", "")
        thresholds = xai.get("threshold_status", {})

        if summary:
            st.info(f"**AI Summary:** {summary}")

        if factors:
            factor_cols = st.columns(min(len(factors), 3))
            for i, factor in enumerate(factors):
                with factor_cols[i % min(len(factors), 3)]:
                    impact = factor.get("impact", "low")
                    icon = factor.get("icon", "📊")
                    name = factor.get("factor", "").replace("_", " ").title()
                    detail = factor.get("detail", "")
                    st.markdown(
                        f'<div class="xai-card impact-{impact}">'
                        f'<div class="factor-name">{icon} {name} '
                        f'<span style="font-size:10px;padding:1px 6px;border-radius:4px;'
                        f'background:rgba(255,255,255,0.08);margin-left:6px;">{impact.upper()}</span>'
                        f'</div>'
                        f'<div class="factor-detail">{detail}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        if thresholds:
            density_exceeded = thresholds.get("density_exceeded", False)
            speed_below = thresholds.get("speed_below", False)
            density_thresh = thresholds.get("density_threshold", 7.0)
            speed_thresh = thresholds.get("speed_threshold", 30.0)

            st.markdown(
                f'<div style="margin-top:8px;">'
                f'<span class="threshold-pill">'
                f'<span class="threshold-dot {"exceeded" if density_exceeded else "ok"}"></span>'
                f'Density ({density_thresh}): {"EXCEEDED" if density_exceeded else "OK"}'
                f'</span>'
                f'<span class="threshold-pill">'
                f'<span class="threshold-dot {"exceeded" if speed_below else "ok"}"></span>'
                f'Speed ({speed_thresh} px/s): {"BELOW" if speed_below else "OK"}'
                f'</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.write("Waiting for analytics data to generate risk explanation...")

    st.markdown("---")

    st.subheader("📈 Live Trend (Last 100 Predictions)")
    if history_data and "data" in history_data and history_data["data"]:
        df = pd.DataFrame(history_data["data"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=df["density"], name="Density", line=dict(color='blue', width=2)))
        fig.add_trace(go.Scatter(y=df["speed"] / 10, name="Speed (÷10)", line=dict(color='orange', width=2)))
        fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        fig.update_xaxes(showgrid=True, gridcolor='rgba(200,200,200,0.2)')
        fig.update_yaxes(showgrid=True, gridcolor='rgba(200,200,200,0.2)')
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    st.subheader("⚙️ Deployment Configuration")
    if config_data and config_data.get("status") == "ok":
        active_modes = config_data.get("active_modes", "Standard Mode")
        st.caption(f"**Active Mode:** {active_modes}")
        config = config_data.get("config", {})
        toggles = config.get("toggles", [])
        if toggles:
            toggle_cols = st.columns(len(toggles))
            for i, t in enumerate(toggles):
                with toggle_cols[i]:
                    status = "🟢 ON" if t["enabled"] else "⚫ OFF"
                    css_class = "active" if t["enabled"] else ""
                    st.markdown(
                        f'<div class="deploy-card {css_class}">'
                        f'<div class="deploy-label">{t["icon"]} {t["label"]} {status}</div>'
                        f'<div style="font-size:12px;margin-top:4px;opacity:0.7;">{t["description"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
    else:
        st.write("Waiting for deployment config...")

time.sleep(2)
st.rerun()

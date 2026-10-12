"""PathGuard-AI Live In-Car & Assessment Dashboard (Bharat Edition).

Streamlit + Pydeck dashboard showing real-time camera overlays,
video upload analysis, 3D H3 spatial grids, Supabase cloud sync,
road type classifications, and statutory eMARG notices.
"""
import streamlit as st
import pydeck as pdk
import cv2
import numpy as np
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
import os
import sys
import tempfile

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from pathguard.config import get_config  
from pathguard.vision import EnhancedVisionPipeline
from pathguard.spatial import H3Engine
from pathguard.notices import estimate_repair_cost
from pathguard.gps_relay import SimulatedGPS
from pathguard.database import DatabaseEngine

st.set_page_config(
    page_title='PathGuard-AI (Bharat Edition)',
    layout='wide',
    page_icon='🛺',
    initial_sidebar_state='expanded'
)

# Custom CSS for Bharat/Saffron theme and styling
st.markdown("""
    <style>
    .severity-badge {
        padding: 4px 8px;
        border-radius: 4px;
        color: white;
        font-weight: bold;
    }
    .severity-low { background-color: #138808; } /* India Green */
    .severity-medium { background-color: #FF9933; color: white; } /* India Saffron */
    .severity-high { background-color: #E65100; } /* Dark Orange */
    .severity-critical { background-color: #B71C1C; } /* Deep Red */
    
    .stApp {
        background-color: #0F0F0F;
    }
    h1, h2, h3, h4 {
        color: #FF9933 !important; /* Saffron headers */
    }
    .metric-card {
        background-color: #1A1A1A;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
    }
    .stDataFrame {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# ── Ensure captures directory exists ─────────────────────────────────────────
captures_dir = Path("captures")
captures_dir.mkdir(exist_ok=True)

# ── Session State Initialization ──────────────────────────────────────────────
if 'config' not in st.session_state:
    st.session_state.config = get_config()

if 'vision' not in st.session_state:
    st.session_state.vision = EnhancedVisionPipeline(st.session_state.config)

if 'h3' not in st.session_state:
    h3_cfg = st.session_state.config.get('h3', {})
    st.session_state.h3 = H3Engine(
        corridor_res=h3_cfg.get('corridor_resolution', 11),
        defect_res=h3_cfg.get('defect_resolution', 12),
        kring_k=h3_cfg.get('kring_k', 1)
    )

if 'gps' not in st.session_state:
    st.session_state.gps = SimulatedGPS()

if 'history' not in st.session_state:
    st.session_state.history = []

if 'total_defects' not in st.session_state:
    st.session_state.total_defects = 0

if 'db_records_saved' not in st.session_state:
    st.session_state.db_records_saved = 0

if 'db_records_merged' not in st.session_state:
    st.session_state.db_records_merged = 0

if 'total_cost_inr' not in st.session_state:
    st.session_state.total_cost_inr = 0.0

# ── Database Initialization ───────────────────────────────────────────────────
def init_database():
    try:
        db_cfg = st.session_state.config.get('database', {})
        engine = DatabaseEngine(
            host=db_cfg.get('host'),
            port=db_cfg.get('port', 5432),
            dbname=db_cfg.get('name', 'postgres'),
            user=db_cfg.get('user', 'postgres'),
            password=db_cfg.get('password', ''),
            url=db_cfg.get('url'),
            sslmode=db_cfg.get('sslmode', 'require'),
            supabase_url=db_cfg.get('supabase_url'),
            supabase_key=db_cfg.get('supabase_key'),
        )
        connected = engine.connect()
        return engine, connected
    except Exception as e:
        return None, False

if 'db' not in st.session_state or 'db_connected' not in st.session_state:
    st.session_state.db, st.session_state.db_connected = init_database()

# ── Sidebar Configuration ─────────────────────────────────────────────────────
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/4/41/Flag_of_India.svg", width=65)
st.sidebar.title("PathGuard-AI")
st.sidebar.markdown("**Bharat Infrastructure Assessment Engine**")

# 1. Supabase Cloud Connection Panel
st.sidebar.markdown("---")
st.sidebar.subheader("☁️ Cloud Database (Supabase)")
if st.session_state.db_connected:
    st.sidebar.success("🟢 Supabase Cloud: Connected & Syncing")
else:
    st.sidebar.warning("🟡 Supabase: Local / Demo Mode (Not connected)")

with st.sidebar.expander("🔑 Supabase Credentials Settings", expanded=not st.session_state.db_connected):
    st.markdown("Enter your Supabase database connection details below:")
    input_db_url = st.text_input(
        "Supabase Connection URI",
        value=st.session_state.config.get('database', {}).get('url', ''),
        help="Format: postgresql+psycopg2://postgres.[ref]:[pass]@[host]:[port]/postgres?sslmode=require",
        type="password"
    )
    col_host, col_port = st.columns([0.7, 0.3])
    with col_host:
        input_db_host = st.text_input("Host", value=st.session_state.config.get('database', {}).get('host', ''))
    with col_port:
        input_db_port = st.number_input("Port", value=int(st.session_state.config.get('database', {}).get('port', 5432)))
    
    input_db_user = st.text_input("User", value=st.session_state.config.get('database', {}).get('user', 'postgres'))
    input_db_pass = st.text_input("Password", value=st.session_state.config.get('database', {}).get('password', ''), type="password")

    if st.button("🔄 Connect Supabase"):
        db_cfg = st.session_state.config.setdefault('database', {})
        if input_db_url:
            db_cfg['url'] = input_db_url
        if input_db_host:
            db_cfg['host'] = input_db_host
        db_cfg['port'] = input_db_port
        db_cfg['user'] = input_db_user
        db_cfg['password'] = input_db_pass
        db_cfg['sslmode'] = 'require'
        
        st.session_state.db, st.session_state.db_connected = init_database()
        if st.session_state.db_connected:
            st.success("Successfully connected to Supabase!")
            st.rerun()
        else:
            st.error("Connection failed. Check host, password, or URI.")

# 2. Road Assessment Specifications
st.sidebar.markdown("---")
st.sidebar.subheader("🛣️ Road & DLP Assessment")
road_name = st.sidebar.text_input("Road / Corridor Name", value="NH-48 Delhi-Gurugram Expressway")
road_type = st.sidebar.selectbox(
    "Pavement / Road Type",
    [
        "Flexible Bituminous Asphalt (MoRTH / IRC:37 - 5-Yr DLP)",
        "Rigid Cement Concrete (IRC:58 - 10-Yr DLP)",
        "PMGSY Rural Road (IRC:SP:20 - 5-Yr DLP / eMARG Audit)",
        "Municipal Urban Road (CPWD Standard - 1-Yr DLP)"
    ]
)
contractor_id = st.sidebar.text_input("Contractor ID (eMARG / NHAI)", value="NHAI-2023-45")
sor_rate = st.sidebar.number_input("Schedule of Rates (SOR ₹/m³)", value=3500, step=500)

# 3. Camera Source & Upload Feature
st.sidebar.markdown("---")
st.sidebar.subheader("📹 Video & Input Source")
camera_source = st.sidebar.selectbox("Input Feed", ["Upload Video", "Webcam", "Demo Video"])
uploaded_video = None
if camera_source == "Upload Video":
    uploaded_video = st.sidebar.file_uploader(
        "Upload Dashcam Video (.mp4 / .mov / .avi)",
        type=['mp4', 'mov', 'avi']
    )

sensitivity = st.sidebar.slider("AI Sensitivity Threshold", 0.1, 1.0, 0.4)

# ── Main Layout ───────────────────────────────────────────────────────────────
st.title("🛺 PathGuard-AI: Live Windshield & Infrastructure Assessment")
st.markdown(f"**Assessing:** `{road_name}` &nbsp;|&nbsp; **Classification:** `{road_type}` &nbsp;|&nbsp; **Contractor:** `{contractor_id}`")

col_feed, col_map = st.columns([0.58, 0.42])

with col_feed:
    st.subheader("Live AI Vision Telemetry")
    frame_placeholder = st.empty()
    telemetry_placeholder = st.empty()

with col_map:
    st.subheader("Uber H3 Spatial Hexagon Grid")
    map_placeholder = st.empty()
    gps_info_placeholder = st.empty()

# ── Real-Time Metrics ─────────────────────────────────────────────────────────
st.subheader("📊 Real-Time Road Assessment Telemetry")
m1, m2, m3, m4 = st.columns(4)
metric1 = m1.empty()
metric2 = m2.empty()
metric3 = m3.empty()
metric4 = m4.empty()

# ── Defect History Table & Legal Notice ───────────────────────────────────────
st.subheader("📑 Detected Violations & Cloud Database Log")
table_placeholder = st.empty()

ticket_expander = st.expander("⚖️ Active eMARG Statutory Notice of Liability", expanded=True)
ticket_content = ticket_expander.empty()

# ── Frame Generator for Demo Fallback ─────────────────────────────────────────
def generate_demo_frame(frame_count):
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 115
    y_pos = int(220 + (frame_count % 35) * 7)
    size = int(35 + (frame_count % 35) * 3)
    cv2.ellipse(frame, (320, y_pos), (size, size // 2), 0, 0, 360, (45, 45, 45), -1)
    noise = np.random.randint(0, 25, (480, 640, 3), dtype=np.uint8)
    return cv2.add(frame, noise)

# ── Execution Loop ────────────────────────────────────────────────────────────
def run_assessment_loop(video_file=None):
    cap = None
    temp_file_path = None
    
    if camera_source == "Upload Video":
        if video_file is not None:
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            tfile.write(video_file.read())
            temp_file_path = tfile.name
            cap = cv2.VideoCapture(temp_file_path)
        else:
            st.warning("Please upload a video file using the sidebar first!")
            return
    elif camera_source == "Webcam":
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    frame_count = 0
    start_time = time.time()
    
    while True:
        frame = None
        if cap and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                if camera_source == "Upload Video":
                    st.success("✅ Video processing complete!")
                    break
                frame = generate_demo_frame(frame_count)
        else:
            frame = generate_demo_frame(frame_count)
            time.sleep(0.04)

        frame_count += 1
        fps = frame_count / max(0.001, time.time() - start_time)
        fix = st.session_state.gps.get_latest()

        # Run enhanced vision pipeline
        st.session_state.vision.base_pipeline.conf_threshold = sensitivity
        detections = st.session_state.vision.process_frame(frame)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        current_defects = []
        for det in detections:
            x, y, w, h = det['bbox']
            w_cm = det.get('width_cm', det.get('real_width_cm', 45.0))
            l_cm = det.get('height_cm', det.get('real_height_cm', 45.0))
            d_cm = det.get('depth_cm', 5.5)
            sev = det.get('severity', 'MEDIUM')
            q_score = det.get('q_score', 0.85)
            class_name = det.get('class_name', 'pothole')

            # Calculate cost
            vol_m3, cost_inr = estimate_repair_cost(w_cm, l_cm, d_cm, sor_rate)

            # Spatial resolution via Uber H3
            cell = st.session_state.h3.resolve(fix.latitude, fix.longitude)

            # Severity Color Palette (Bharat Saffron / Red / Green)
            color = (19, 136, 8)  # Green
            if sev == 'HIGH':
                color = (255, 153, 51)  # Saffron
            elif sev == 'CRITICAL':
                color = (183, 28, 28)  # Red

            cv2.rectangle(frame_rgb, (x, y), (x + w, y + h), color, 3)
            label = f"{class_name.upper()} {d_cm:.1f}cm (₹{int(cost_inr)})"
            cv2.putText(frame_rgb, label, (x, max(15, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

            # Save snapshot to captures directory
            snapshot_name = f"defect_{int(time.time())}_{frame_count}.jpg"
            snapshot_path = str(captures_dir / snapshot_name)
            try:
                cv2.imwrite(snapshot_path, frame)
            except Exception:
                snapshot_path = ""

            # Real-time Supabase Database write
            db_status_txt = "Local Only"
            if st.session_state.db_connected and st.session_state.db is not None:
                try:
                    db_res = st.session_state.db.process_detection(
                        h3_cell=cell,
                        detection_data={
                            'width_cm': w_cm,
                            'length_cm': l_cm,
                            'depth_cm': d_cm,
                            'volume_m3': vol_m3,
                            'severity': sev,
                            'q_score': q_score,
                            'class_name': class_name,
                            'image_path': snapshot_path,
                            'road_name': road_name,
                            'road_type': road_type,
                            'contract_id': contractor_id,
                            'imu_az_g': 0.12
                        }
                    )
                    status_val = db_res.get('status', 'SAVED')
                    if status_val == 'CREATED_NEW':
                        st.session_state.db_records_saved += 1
                        db_status_txt = "🟢 Synced (New)"
                    elif status_val == 'MERGED_EXISTING':
                        st.session_state.db_records_merged += 1
                        db_status_txt = "🔵 Merged (Dedup)"
                except Exception as db_err:
                    db_status_txt = f"Err: {str(db_err)[:15]}"

            info = {
                'Time': datetime.now().strftime("%H:%M:%S"),
                'Defect': class_name.upper(),
                'Severity': sev,
                'Depth (cm)': round(d_cm, 1),
                'Volume (m³)': round(vol_m3, 4),
                'Cost (₹)': f"₹{int(cost_inr):,}",
                'H3-Index': cell.res12,
                'Corridor': cell.res11,
                'Road Type': road_type.split('(')[0].strip(),
                'Supabase Sync': db_status_txt,
                'Lat': fix.latitude,
                'Lon': fix.longitude
            }

            if vol_m3 > 0.0005:
                current_defects.append(info)
                st.session_state.total_cost_inr += cost_inr

        frame_placeholder.image(frame_rgb, channels="RGB", use_column_width=True)

        # GPS & Telemetry Card
        speed_est = 42.0 + (frame_count % 8) * 0.5
        telemetry_placeholder.markdown(f"""
        **🛰️ Live Telemetry:** Speed: `{speed_est:.1f} km/h` &nbsp;|&nbsp; Lat: `{fix.latitude:.5f}` &nbsp;|&nbsp; Lon: `{fix.longitude:.5f}` &nbsp;|&nbsp; Processing: `{fps:.1f} FPS`
        """)

        gps_info_placeholder.info(f"""
        **📍 Spatial Coordinates & Pavement Status:**
        - **Corridor Index (H3 Res 11):** `{st.session_state.h3.resolve(fix.latitude, fix.longitude).res11}`
        - **Defect Hexagon (H3 Res 12):** `{st.session_state.h3.resolve(fix.latitude, fix.longitude).res12}`
        - **Pavement Type:** {road_type}
        - **Active Contractor:** {contractor_id}
        """)

        if current_defects:
            st.session_state.history = (current_defects + st.session_state.history)[:30]
            st.session_state.total_defects += len(current_defects)

        # ── Map Rendering ─────────────────────────────────────────────────────
        map_data = pd.DataFrame(st.session_state.history)
        if not map_data.empty:
            view_state = pdk.ViewState(
                latitude=fix.latitude,
                longitude=fix.longitude,
                zoom=16,
                pitch=50
            )
            scatter_layer = pdk.Layer(
                'ScatterplotLayer',
                data=map_data,
                get_position=['Lon', 'Lat'],
                get_fill_color="[255, 153, 51, 220]",
                get_line_color="[255, 255, 255]",
                get_radius=10,
                pickable=True
            )
            deck_map = pdk.Deck(
                layers=[scatter_layer],
                initial_view_state=view_state,
                map_style='mapbox://styles/mapbox/dark-v10'
            )
            map_placeholder.pydeck_chart(deck_map)

        # ── Metrics Update ────────────────────────────────────────────────────
        high_critical_count = sum(1 for d in st.session_state.history if d['Severity'] in ['HIGH', 'CRITICAL'])
        
        metric1.metric("Total Defects Logged", st.session_state.total_defects)
        metric2.metric("Critical Violations", high_critical_count)
        metric3.metric("Supabase Records Synced", f"{st.session_state.db_records_saved} new / {st.session_state.db_records_merged} dedup")
        metric4.metric("Total Liability Cost", f"₹{int(st.session_state.total_cost_inr):,}")

        # ── Table Update ──────────────────────────────────────────────────────
        if not map_data.empty:
            display_df = map_data.drop(columns=['Lat', 'Lon'])
            table_placeholder.dataframe(display_df, use_container_width=True, hide_index=True)

            latest = map_data.iloc[0]
            if latest['Severity'] in ['HIGH', 'CRITICAL']:
                ticket_content.markdown(f"""
                ### ⚖️ STATUTORY LIABILITY NOTICE (Clause 17 - {road_type.split('(')[0].strip()})
                **TO CONTRACTOR:** `{contractor_id}`  
                **CORRIDOR:** `{road_name}`  
                **DEFECT CLASSIFICATION:** `{latest['Defect']}` ({latest['Severity']} SEVERITY)
                
                *   **Occurrence Timestamp:** `{latest['Time']}`
                *   **Uber H3 Spatial Hex:** `{latest['H3-Index']}` (Corridor Sector: `{latest['Corridor']}`)
                *   **Physical Defect Depth:** `{latest['Depth (cm)']} cm`
                *   **Estimated Volume:** `{latest['Volume (m³)']} m³`
                *   **MoRTH SOR Schedule Rate:** `{latest['Cost (₹)']}`
                *   **Supabase Cloud Sync Status:** `{latest['Supabase Sync']}`
                
                **STATUTORY DIRECTIVE:**  
                Rectification must be initiated within **14 Business Days**. Default invokes third-party execution against the contractor's performance guarantee escrow.
                """)

    if cap:
        cap.release()
    if temp_file_path and os.path.exists(temp_file_path):
        try:
            os.remove(temp_file_path)
        except Exception:
            pass

# ── Start Button ──────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
if st.sidebar.button("▶ START AI ASSESSMENT"):
    run_assessment_loop(uploaded_video)
else:
    st.info("👈 Configure your road settings in the sidebar and click **'START AI ASSESSMENT'**.")

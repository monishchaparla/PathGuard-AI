"""PathGuard-AI Live In-Car Dashboard.

Streamlit + Pydeck dashboard showing real-time camera overlays,
3D spatial grids, and ticket management.
"""
import streamlit as st
import pydeck as pdk
import cv2
import numpy as np
import time
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add project root to sys.path to avoid import errors in Streamlit
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from pathguard.config import get_config  
from pathguard.vision import VisionPipeline
from pathguard.spatial import H3Engine
from pathguard.contracts import DLPEngine
from pathguard.notices import estimate_repair_cost, generate_notice_body, compute_cure_deadline
from pathguard.gps_relay import SimulatedGPS

st.set_page_config(page_title='PathGuard-AI', layout='wide', page_icon='🛡️')

# Custom CSS for dark theme and styling
st.markdown("""
    <style>
    .severity-badge {
        padding: 4px 8px;
        border-radius: 4px;
        color: white;
        font-weight: bold;
    }
    .severity-low { background-color: #28a745; }
    .severity-medium { background-color: #ffc107; color: black; }
    .severity-high { background-color: #fd7e14; }
    .severity-critical { background-color: #dc3545; }
    </style>
""", unsafe_allow_html=True)

# Initialize Session State
if 'config' not in st.session_state:
    st.session_state.config = get_config()
if 'vision' not in st.session_state:
    st.session_state.vision = VisionPipeline(st.session_state.config)
if 'h3' not in st.session_state:
    st.session_state.h3 = H3Engine(st.session_state.config)
if 'gps' not in st.session_state:
    st.session_state.gps = SimulatedGPS()
if 'history' not in st.session_state:
    st.session_state.history = []
if 'total_defects' not in st.session_state:
    st.session_state.total_defects = 0

# Sidebar
st.sidebar.title("PathGuard-AI Settings")
camera_source = st.sidebar.selectbox("Camera Source", [0, 1, 2, "Demo Mode"])
gps_mode = st.sidebar.radio("GPS Mode", ["Simulated", "Live"])
db_status = st.sidebar.empty()
db_status.success("Database: Disconnected (Demo)")
sensitivity = st.sidebar.slider("Detection Sensitivity", 0.1, 1.0, 0.5)

st.sidebar.markdown("### Active Contract")
st.sidebar.info("NHAI-2023-45 (Delhi-Gurugram)\nDLP Expiry: 2026-12-31")

# Main Layout
st.title("🛡️ PathGuard-AI: Live In-Car Dashboard")

col1, col2 = st.columns([0.6, 0.4])

with col1:
    st.subheader("Live Feed")
    frame_placeholder = st.empty()
    
with col2:
    st.subheader("Spatial Grid")
    map_placeholder = st.empty()

st.subheader("Recent Detections & Tickets")
metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
m1 = metrics_col1.empty()
m2 = metrics_col2.empty()
m3 = metrics_col3.empty()
m4 = metrics_col4.empty()

table_placeholder = st.empty()
ticket_expander = st.expander("Latest Ticket Preview", expanded=False)
ticket_content = ticket_expander.empty()

def generate_demo_frame():
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 150
    # Simulate a pothole
    cv2.ellipse(frame, (320, 240), (80, 40), 0, 0, 360, (50, 50, 50), -1)
    return frame

# Main Processing Loop
def run_loop():
    cap = None
    if isinstance(camera_source, int):
        cap = cv2.VideoCapture(camera_source)
        
    while True:
        if cap and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                frame = generate_demo_frame()
        else:
            frame = generate_demo_frame()
            time.sleep(0.1) # Simulate framerate
            
        fix = st.session_state.gps.get_latest()
        
        # Process frame
        st.session_state.vision.conf_threshold = sensitivity
        detections = st.session_state.vision.process_frame(frame)
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        current_defects = []
        for det in detections:
            x, y, w, h = det['bbox']
            sev = det.get('severity', 'MEDIUM')
            
            color = (0, 255, 0)
            if sev == 'HIGH': color = (255, 165, 0)
            elif sev == 'CRITICAL': color = (255, 0, 0)
            
            cv2.rectangle(frame_rgb, (x, y), (x+w, y+h), color, 3)
            
            vol = st.session_state.vision.estimate_volume(det['dimensions'])
            h3_idx = st.session_state.h3.get_cell_for_point(fix.latitude, fix.longitude)
            
            info = {
                'Timestamp': datetime.now().strftime("%H:%M:%S"),
                'Type': det['class_name'],
                'Severity': sev,
                'Volume(m3)': round(vol, 3),
                'Lat': fix.latitude,
                'Lon': fix.longitude,
                'H3': h3_idx
            }
            current_defects.append(info)
            
            # Label
            label = f"{det['class_name']} {vol:.2f}m3"
            cv2.putText(frame_rgb, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
        frame_placeholder.image(frame_rgb, channels="RGB", use_column_width=True)
        
        if current_defects:
            st.session_state.history = (current_defects + st.session_state.history)[:20]
            st.session_state.total_defects += len(current_defects)
            
        # Update Map
        map_data = pd.DataFrame(st.session_state.history)
        if not map_data.empty:
            view_state = pdk.ViewState(
                latitude=fix.latitude,
                longitude=fix.longitude,
                zoom=15, pitch=45
            )
            
            scatter_layer = pdk.Layer(
                'ScatterplotLayer',
                data=map_data,
                get_position=['Lon', 'Lat'],
                get_color=[200, 30, 0, 160],
                get_radius=15,
            )
            
            r = pdk.Deck(
                layers=[scatter_layer],
                initial_view_state=view_state,
                map_style='mapbox://styles/mapbox/dark-v10'
            )
            map_placeholder.pydeck_chart(r)
        
        # Update Metrics
        high_sev = sum(1 for d in st.session_state.history if d['Severity'] in ['HIGH', 'CRITICAL'])
        m1.metric("Total Defects", st.session_state.total_defects)
        m2.metric("High Severity", high_sev)
        m3.metric("Tickets Generated", len(st.session_state.history) // 3)
        m4.metric("Network Status", "Connected" if True else "Offline")
        
        # Update Table
        if not map_data.empty:
            table_placeholder.dataframe(map_data, use_container_width=True)
            
            latest = map_data.iloc[0]
            if latest['Severity'] in ['HIGH', 'CRITICAL']:
                ticket_content.markdown(f"""
                **Automated Notice Generated**
                - **Defect:** {latest['Type']} ({latest['Severity']})
                - **Location:** {latest['Lat']:.4f}, {latest['Lon']:.4f}
                - **Contractor:** NHAI-2023-45 
                - **Estimated Cost:** ₹5,000
                """)
        
        time.sleep(0.1)

# Streamlit requires a button or similar to start the infinite loop gracefully
if st.sidebar.button("Start Live Feed"):
    run_loop()
else:
    st.info("Click 'Start Live Feed' in the sidebar to begin.")

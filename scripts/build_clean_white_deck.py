"""PathGuard-AI Minimalist White Presentation Generator (v2).

Key Design Principles:
- Minimalist White & Light Canvas (Pure #FFFFFF & soft #F8FAFC)
- Generous whitespace, zero congestion, breathing room between cards
- Moderate, punchy matter (no text dumping!)
- Clear visual hierarchy with crisp typography (Dark Slate #0F172A, Saffron #E65100, Emerald #0F766E)
- Embedded real demo images and expected video references
- Comic storytelling arc refined into clean, impactful story beats
- Accurate team names: Chaparla Monish, Mogalapu Hasini Priya, Pappala Likhitha, Malapati Mamatha
"""
import os
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_clean_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Minimalist Light Color Palette
    C_BG = RGBColor(255, 255, 255)         # Pure Crisp White
    C_SURFACE = RGBColor(248, 250, 252)    # Soft Off-White (#F8FAFC)
    C_CARD = RGBColor(255, 255, 255)       # Card White
    C_BORDER = RGBColor(226, 232, 240)     # Subtle Border (#E2E8F0)
    C_BORDER_ACCENT = RGBColor(254, 215, 170) # Soft Saffron Tint Border
    
    C_TEXT_PRIMARY = RGBColor(15, 23, 42)  # Dark Slate (#0F172A)
    C_TEXT_MUTED = RGBColor(100, 116, 139) # Slate Gray (#64748B)
    C_TEXT_BODY = RGBColor(51, 65, 85)     # Deep Slate (#334155)
    
    C_SAFFRON = RGBColor(230, 81, 0)       # Bharat Deep Saffron (#E65100)
    C_GREEN = RGBColor(15, 118, 110)       # Bharat Deep Emerald (#0F766E)
    C_BLUE = RGBColor(37, 99, 235)         # Royal Blue Accent (#2563EB)
    C_RED = RGBColor(225, 29, 72)          # Rose Red Accent (#E11D48)

    output_dir = Path("docs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    ref_img1 = Path("docs/demo_outputs/reference_defect_detection_1.jpg")
    ref_img2 = Path("docs/demo_outputs/reference_defect_detection_2.jpg")
    ref_img3 = Path("docs/demo_outputs/reference_defect_detection_3.jpg")
    ref_img4 = Path("docs/demo_outputs/reference_defect_detection_4.jpg")

    def add_slide_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = C_SURFACE
        bg.line.fill.background()
        return bg

    def add_header(slide, title_text, category_text="PATHGUARD-AI"):
        # Category Kicker Tag
        kicker_box = slide.shapes.add_textbox(Inches(0.9), Inches(0.45), Inches(11.5), Inches(0.3))
        tf_k = kicker_box.text_frame
        tf_k.word_wrap = True
        tf_k.margin_left = tf_k.margin_top = tf_k.margin_right = tf_k.margin_bottom = 0
        pk = tf_k.paragraphs[0]
        pk.text = category_text.upper()
        pk.font.size = Pt(10)
        pk.font.bold = True
        pk.font.color.rgb = C_SAFFRON

        # Main Slide Title
        title_box = slide.shapes.add_textbox(Inches(0.9), Inches(0.75), Inches(11.5), Inches(0.6))
        tf_t = title_box.text_frame
        tf_t.word_wrap = True
        tf_t.margin_left = tf_t.margin_top = tf_t.margin_right = tf_t.margin_bottom = 0
        pt = tf_t.paragraphs[0]
        pt.text = title_text
        pt.font.size = Pt(22)
        pt.font.bold = True
        pt.font.color.rgb = C_TEXT_PRIMARY

    def add_card(slide, left, top, width, height, bg_color=C_CARD, border_color=C_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.0)
        return card

    # =========================================================================
    # SLIDE 1: CLEAN TITLE SLIDE
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s1)

    # Accent Top Line
    top_line = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.08))
    top_line.fill.solid()
    top_line.fill.fore_color.rgb = C_SAFFRON
    top_line.line.fill.background()

    # Hero Card
    hero = add_card(s1, Inches(0.9), Inches(1.1), Inches(11.533), Inches(3.6), C_CARD, C_BORDER_ACCENT)
    tf_h = hero.text_frame
    tf_h.word_wrap = True
    tf_h.margin_left = Inches(0.6)
    tf_h.margin_top = Inches(0.5)

    ph1 = tf_h.paragraphs[0]
    ph1.text = "PATHGUARD-AI"
    ph1.font.size = Pt(40)
    ph1.font.bold = True
    ph1.font.color.rgb = C_SAFFRON

    ph2 = tf_h.add_paragraph()
    ph2.text = "Autonomous Road Infrastructure Quality & Statutory Contract Compliance Engine"
    ph2.font.size = Pt(19)
    ph2.font.bold = True
    ph2.font.color.rgb = C_TEXT_PRIMARY
    ph2.space_before = Pt(8)

    ph3 = tf_h.add_paragraph()
    ph3.text = "Detect Damage  •  Measure 3D Volume  •  Enforce Contractor Liability  •  Protect Public Funds"
    ph3.font.size = Pt(13)
    ph3.font.bold = True
    ph3.font.color.rgb = C_GREEN
    ph3.space_before = Pt(12)

    ph4 = tf_h.add_paragraph()
    ph4.text = "Powered by YOLOv8, MiDaS Monocular Depth, OpenStreetMap Live API, Uber H3 & Supabase Cloud"
    ph4.font.size = Pt(11)
    ph4.font.color.rgb = C_TEXT_MUTED
    ph4.space_before = Pt(6)

    # Team Members Card
    team_card = add_card(s1, Inches(0.9), Inches(4.95), Inches(11.533), Inches(1.85), C_CARD, C_BORDER)
    tf_tc = team_card.text_frame
    tf_tc.word_wrap = True
    tf_tc.margin_left = Inches(0.5)
    tf_tc.margin_top = Inches(0.2)

    pth = tf_tc.paragraphs[0]
    pth.text = "PROJECT CORE TEAM"
    pth.font.size = Pt(11)
    pth.font.bold = True
    pth.font.color.rgb = C_TEXT_MUTED

    members = [
        ("Chaparla Monish", "System Architecture & AI"),
        ("Mogalapu Hasini Priya", "Vision & Depth Estimation"),
        ("Pappala Likhitha", "Geospatial & H3 Dedup"),
        ("Malapati Mamatha", "DLP Contracts & Cloud DB")
    ]
    for i, (name, role) in enumerate(members):
        col_left = Inches(1.4 + i * 2.75)
        box = s1.shapes.add_textbox(col_left, Inches(5.45), Inches(2.6), Inches(1.1))
        tf_m = box.text_frame
        tf_m.word_wrap = True
        tf_m.margin_left = tf_m.margin_top = 0
        p_name = tf_m.paragraphs[0]
        p_name.text = name
        p_name.font.size = Pt(13)
        p_name.font.bold = True
        p_name.font.color.rgb = C_TEXT_PRIMARY

        p_role = tf_m.add_paragraph()
        p_role.text = role
        p_role.font.size = Pt(10)
        p_role.font.color.rgb = C_TEXT_MUTED
        p_role.space_before = Pt(2)

    # =========================================================================
    # SLIDE 2: COMIC STORYBOARD — THE PROBLEM
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s2)
    add_header(s2, "The Commuter's Dilemma: Why Road Repairs Keep Failing", "STORY NARRATIVE • PART 1")

    story_problem = [
        ("1. The Morning Collision", "💥 Sudden Crater", 
         "Ravi drives to work on a newly recarpeted highway. BANG! An invisible deep crater bursts his tire and damages the axle. 'This road was tarred just 3 months ago!'"),
        ("2. The Bureaucracy Maze", "📞 Missing Accountability", 
         "Ravi calls the helpline. Officer: 'Sir, it is under a 5-year contractor warranty, but we have no proof of which contractor paved this exact 10-meter stretch!'"),
        ("3. The Taxpayer Loss", "💸 Public Funds Wasted", 
         "Contractors collect their 5% retention guarantee. The city issues a duplicate emergency tender. Taxpayers pay twice while the same pothole sits for months.")
    ]

    for idx, (title, tag, text) in enumerate(story_problem):
        c_left = Inches(0.9 + idx * 4.0)
        card = add_card(s2, c_left, Inches(1.7), Inches(3.6), Inches(5.0), C_CARD, C_BORDER)
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.35)
        tf.margin_right = Inches(0.35)
        tf.margin_top = Inches(0.35)

        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.size = Pt(14)
        p1.font.bold = True
        p1.font.color.rgb = C_SAFFRON

        p2 = tf.add_paragraph()
        p2.text = tag
        p2.font.size = Pt(16)
        p2.font.bold = True
        p2.font.color.rgb = C_TEXT_PRIMARY
        p2.space_before = Pt(6)

        p3 = tf.add_paragraph()
        p3.text = text
        p3.font.size = Pt(12)
        p3.font.color.rgb = C_TEXT_BODY
        p3.space_before = Pt(12)

    # =========================================================================
    # SLIDE 3: COMIC STORYBOARD — THE TRANSFORMATION
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s3)
    add_header(s3, "Enter PathGuard-AI: Instant Detection & Legal Enforcement", "STORY NARRATIVE • PART 2")

    story_solution = [
        ("1. Mount & AI Sees", "📹 45 FPS Edge Vision", 
         "Priya mounts a regular dashcam. YOLOv8 detects the pothole instantly. MiDaS extracts physical depth: 6.8 cm! Volumetric integration computes 0.042 m3 repair volume."),
        ("2. Web & Cloud Dedup", "🌐 OSM + Uber H3", 
         "OpenStreetMap live API resolves 'Delhi-Gurugram Expressway'. PostGIS ST_DWithin clusters passes within 3m — 10 cars drive over it, but only ONE master ticket is created!"),
        ("3. Instant Legal Notice", "⚖️ Clause 17 Notice Served", 
         "System links NHAI-2023-45 contract: Active 5-Yr DLP! A statutory notice is issued with ₹3,570 cost & a 14-day cure deadline. Contractor repairs in 48 hours!")
    ]

    for idx, (title, tag, text) in enumerate(story_solution):
        c_left = Inches(0.9 + idx * 4.0)
        card = add_card(s3, c_left, Inches(1.7), Inches(3.6), Inches(5.0), C_CARD, C_BORDER_ACCENT if idx == 2 else C_BORDER)
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.35)
        tf.margin_right = Inches(0.35)
        tf.margin_top = Inches(0.35)

        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.size = Pt(14)
        p1.font.bold = True
        p1.font.color.rgb = C_GREEN

        p2 = tf.add_paragraph()
        p2.text = tag
        p2.font.size = Pt(16)
        p2.font.bold = True
        p2.font.color.rgb = C_TEXT_PRIMARY
        p2.space_before = Pt(6)

        p3 = tf.add_paragraph()
        p3.text = text
        p3.font.size = Pt(12)
        p3.font.color.rgb = C_TEXT_BODY
        p3.space_before = Pt(12)

    # =========================================================================
    # SLIDE 4: SYSTEM ARCHITECTURE (The 4 Core Pillars)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s4)
    add_header(s4, "System Architecture: 4 Autonomous Execution Pillars", "CORE ARCHITECTURE")

    pillars = [
        ("Pillar 1", "Edge Vision & 3D Geometry", C_SAFFRON,
         "• YOLOv8 7-class defect detection\n• MiDaS monocular depth (cm)\n• Physical volume calculation (m3)\n• Adaptive classical CV fallback"),
        ("Pillar 2", "Geospatial & Web API", C_BLUE,
         "• Live OpenStreetMap geocoding\n• Highway presets & custom Lat/Lon\n• Uber H3 Res 11 (corridor)\n• Uber H3 Res 12 (9m2 defect hex)"),
        ("Pillar 3", "Cloud Spatial Deduplication", C_GREEN,
         "• Supabase Cloud PostgreSQL\n• PostGIS ST_DWithin (3m radius)\n• Zero Docker container overhead\n• Immutable audit trail history"),
        ("Pillar 4", "Statutory eMARG Notice", C_RED,
         "• MoRTH EPC Clause 17 rules\n• Parametric DLP aging (5-10 yrs)\n• Schedule of Rates (SOR ₹/m3)\n• 14-day statutory cure notice")
    ]

    for idx, (p_tag, p_name, p_col, p_desc) in enumerate(pillars):
        c_left = Inches(0.9 + idx * 2.95)
        card = add_card(s4, c_left, Inches(1.7), Inches(2.7), Inches(5.0), C_CARD, C_BORDER)
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.25)
        tf.margin_right = Inches(0.25)
        tf.margin_top = Inches(0.3)

        pt = tf.paragraphs[0]
        pt.text = p_tag.upper()
        pt.font.size = Pt(10)
        pt.font.bold = True
        pt.font.color.rgb = p_col

        pn = tf.add_paragraph()
        pn.text = p_name
        pn.font.size = Pt(14)
        pn.font.bold = True
        pn.font.color.rgb = C_TEXT_PRIMARY
        pn.space_before = Pt(4)

        pd = tf.add_paragraph()
        pd.text = p_desc
        pd.font.size = Pt(11)
        pd.font.color.rgb = C_TEXT_BODY
        pd.space_before = Pt(12)

    # =========================================================================
    # SLIDE 5: MODULE 1 — DEEP VISION & 3D DEPTH (With Real Image)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s5)
    add_header(s5, "Module 1: Real-Time Vision & Monocular Depth Extraction", "DEEP VISION & GEOMETRY")

    # Left: Reference Image from Actual Pipeline Execution
    if ref_img1.exists():
        s5.shapes.add_picture(str(ref_img1), Inches(0.9), Inches(1.7), Inches(5.6), Inches(4.9))

    # Right: Technical Details Card
    rc1 = add_card(s5, Inches(6.8), Inches(1.7), Inches(5.633), Inches(4.9), C_CARD, C_BORDER)
    tf_r1 = rc1.text_frame
    tf_r1.word_wrap = True
    tf_r1.margin_left = Inches(0.4)
    tf_r1.margin_right = Inches(0.4)
    tf_r1.margin_top = Inches(0.35)

    p = tf_r1.paragraphs[0]
    p.text = "How Vision Translates to Physical Repair Data:"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_SAFFRON

    v_points = [
        ("IRC:82-2015 7-Class Standard", "Detects Potholes, Cracks (Longitudinal, Transverse, Alligator), Rutting, Raveling, and Defective Patching."),
        ("Monocular Depth Without Costly LiDAR", "Combines camera mounting height (130 cm) with MiDaS monocular depth maps to calculate true physical depth in centimeters."),
        ("Volumetric Calculation Formula", "Computes true defect volume: V = (2/3) * π * (W/2) * (L/2) * D * 10^-6 m3 to estimate exact asphalt refill needs."),
        ("Guaranteed Zero-Crash Fallback", "If GPU mixed-precision is unavailable, the adaptive contour fallback engages instantly, maintaining 100% inspection uptime.")
    ]
    for vp_t, vp_d in v_points:
        p_t = tf_r1.add_paragraph()
        p_t.text = vp_t
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = C_TEXT_PRIMARY
        p_t.space_before = Pt(10)

        p_d = tf_r1.add_paragraph()
        p_d.text = vp_d
        p_d.font.size = Pt(10.5)
        p_d.font.color.rgb = C_TEXT_MUTED
        p_d.space_before = Pt(2)

    # =========================================================================
    # SLIDE 6: MODULE 2 — LIVE WEB ROAD DETECTION & GEOCODING
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s6)
    add_header(s6, "Module 2: Live OpenStreetMap Road & Contractor Resolution", "GEOSPATIAL INTELLIGENCE")

    col_w = Inches(5.6)
    # Card 1: OpenStreetMap Live API
    c_osm = add_card(s6, Inches(0.9), Inches(1.7), col_w, Inches(4.9), C_CARD, C_BORDER)
    tf_osm = c_osm.text_frame
    tf_osm.word_wrap = True
    tf_osm.margin_left = Inches(0.4)
    tf_osm.margin_right = Inches(0.4)
    tf_osm.margin_top = Inches(0.35)

    p = tf_osm.paragraphs[0]
    p.text = "1. Live Web Road Geocoding"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_SAFFRON

    osm_items = [
        ("Real-Time Reverse Geocoding", "Queries OpenStreetMap Nominatim live web API at edge speed to automatically resolve road names, city, district, and state from coordinates."),
        ("Pavement Standard Inference", "Automatically maps highway hierarchy: Motorways -> Flexible Bituminous (IRC:37); Primary roads -> Rigid Concrete (IRC:58); Tertiary -> PMGSY Rural."),
        ("Preset Indian Expressways", "Quick-select presets for NH-48 Delhi-Gurugram, NH-44 Bengaluru Silk Board, Mumbai-Pune Expressway, and PVNR Hyderabad."),
        ("Custom Lat/Lon Input", "Auditors can type any coordinate in India to instantly fetch live road metadata and contractor records.")
    ]
    for ot, od in osm_items:
        p_t = tf_osm.add_paragraph()
        p_t.text = ot
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = C_TEXT_PRIMARY
        p_t.space_before = Pt(8)

        p_d = tf_osm.add_paragraph()
        p_d.text = od
        p_d.font.size = Pt(10.5)
        p_d.font.color.rgb = C_TEXT_MUTED
        p_d.space_before = Pt(2)

    # Card 2: Uber H3 Hexagonal Grid
    c_h3 = add_card(s6, Inches(6.833), Inches(1.7), col_w, Inches(4.9), C_CARD, C_BORDER)
    tf_h3 = c_h3.text_frame
    tf_h3.word_wrap = True
    tf_h3.margin_left = Inches(0.4)
    tf_h3.margin_right = Inches(0.4)
    tf_h3.margin_top = Inches(0.35)

    p = tf_h3.paragraphs[0]
    p.text = "2. Uber H3 Hexagonal Indexing"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_BLUE

    h3_items = [
        ("Resolution 11 (Corridor Hexagon)", "Averages ~300m across. Organizes highway sectors into macro chunks to monitor multi-kilometer degradation rates."),
        ("Resolution 12 (Defect Hexagon)", "Averages ~9.2 m2, precisely matching road lane width. Snaps GPS coordinates so GPS drift doesn't move potholes into ditches."),
        ("Automated Contractor Matching", "Cross-references H3 indices against registered contracts to assign L&T, Navayuga, IRB, or state PWD contractors automatically."),
        ("Uniform Neighbor Topology", "Hexagons provide equal center-to-center distances to all 6 neighbors, avoiding diagonal distortion present in square grids.")
    ]
    for ht, hd in h3_items:
        p_t = tf_h3.add_paragraph()
        p_t.text = ht
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = C_TEXT_PRIMARY
        p_t.space_before = Pt(8)

        p_d = tf_h3.add_paragraph()
        p_d.text = hd
        p_d.font.size = Pt(10.5)
        p_d.font.color.rgb = C_TEXT_MUTED
        p_d.space_before = Pt(2)

    # =========================================================================
    # SLIDE 7: MODULE 3 — CLOUD STORAGE & POSTGIS DEDUPLICATION
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s7)
    add_header(s7, "Module 3: Supabase Cloud & 3-Meter Spatial Deduplication", "CLOUD DATABASE")

    card_s1 = add_card(s7, Inches(0.9), Inches(1.7), Inches(5.6), Inches(4.9), C_CARD, C_BORDER)
    tf_s1 = card_s1.text_frame
    tf_s1.word_wrap = True
    tf_s1.margin_left = Inches(0.4)
    tf_s1.margin_right = Inches(0.4)
    tf_s1.margin_top = Inches(0.35)

    p = tf_s1.paragraphs[0]
    p.text = "☁️ Migrated to Supabase Cloud"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_GREEN

    supa_pts = [
        ("Zero Docker Footprint", "Replaced heavy local Docker containers with managed Supabase Cloud PostgreSQL 15 + PostGIS 3.4. No container crashes or VM setup."),
        ("Instant Team Sync", "Team members and field vehicles connect securely using SSL pooled URIs. Credentials stored safely in .env."),
        ("Persistent Audit Register", "Stores defect coordinates, road types, physical dimensions, photo paths, contractor IDs, and repair statuses in real time.")
    ]
    for st, sd in supa_pts:
        p_t = tf_s1.add_paragraph()
        p_t.text = st
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = C_TEXT_PRIMARY
        p_t.space_before = Pt(12)

        p_d = tf_s1.add_paragraph()
        p_d.text = sd
        p_d.font.size = Pt(10.5)
        p_d.font.color.rgb = C_TEXT_MUTED
        p_d.space_before = Pt(2)

    card_s2 = add_card(s7, Inches(6.833), Inches(1.7), Inches(5.6), Inches(4.9), C_CARD, C_BORDER)
    tf_s2 = card_s2.text_frame
    tf_s2.word_wrap = True
    tf_s2.margin_left = Inches(0.4)
    tf_s2.margin_right = Inches(0.4)
    tf_s2.margin_top = Inches(0.35)

    p = tf_s2.paragraphs[0]
    p.text = "📍 PostGIS ST_DWithin (3m Radius)"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_SAFFRON

    dedup_pts = [
        ("Sub-Millisecond Spatial Lookup", "When a defect is detected, PostGIS checks ST_DWithin(geom, 3.0m) to see if that pothole already exists."),
        ("MERGE Instead of DUPLICATE", "If a car drives over the same pothole twice, the system merges the record, updating it with the worst-case depth and clearer photo."),
        ("Stops Municipal Billing Fraud", "Eliminates duplicate complaints and ensures city authorities are billed only once for genuine unique road defects.")
    ]
    for dt, dd in dedup_pts:
        p_t = tf_s2.add_paragraph()
        p_t.text = dt
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = C_TEXT_PRIMARY
        p_t.space_before = Pt(12)

        p_d = tf_s2.add_paragraph()
        p_d.text = dd
        p_d.font.size = Pt(10.5)
        p_d.font.color.rgb = C_TEXT_MUTED
        p_d.space_before = Pt(2)

    # =========================================================================
    # SLIDE 8: MODULE 4 — STATUTORY NOTICE & eMARG DLP ENGINE
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s8)
    add_header(s8, "Module 4: Statutory Liability & Automated Legal Notices", "LEGAL & DLP ENGINE")

    # Left: DLP Framework
    card_l1 = add_card(s8, Inches(0.9), Inches(1.7), Inches(5.6), Inches(4.9), C_CARD, C_BORDER)
    tf_l1 = card_l1.text_frame
    tf_l1.word_wrap = True
    tf_l1.margin_left = Inches(0.4)
    tf_l1.margin_right = Inches(0.4)
    tf_l1.margin_top = Inches(0.35)

    p = tf_l1.paragraphs[0]
    p.text = "Statutory Defect Liability Framework:"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_SAFFRON

    dlp_rules = [
        ("MoRTH EPC Clause 17", "Mandates 5-Year DLP for Bituminous Flexible Pavements (IRC:37) and 10-Year DLP for Concrete Pavements (IRC:58)."),
        ("PMGSY Rural (eMARG)", "Requires 5-Year contractor maintenance with bi-monthly geo-tagged photographic inspection evidence."),
        ("Parametric Workmanship Scoring (Sd)", 
         "Calculates Sd based on defect severity, pavement age vs DLP lifespan, and actual traffic load (ESAL). If Sd >= 1.0, it is classified as ACTIONABLE_CONTRACTOR_DEFECT.")
    ]
    for d_title, d_desc in dlp_rules:
        pd_t = tf_l1.add_paragraph()
        pd_t.text = d_title
        pd_t.font.size = Pt(12)
        pd_t.font.bold = True
        pd_t.font.color.rgb = C_TEXT_PRIMARY
        pd_t.space_before = Pt(12)

        pd_d = tf_l1.add_paragraph()
        pd_d.text = d_desc
        pd_d.font.size = Pt(10.5)
        pd_d.font.color.rgb = C_TEXT_MUTED
        pd_d.space_before = Pt(2)

    # Right: Notice Preview
    card_l2 = add_card(s8, Inches(6.833), Inches(1.7), Inches(5.6), Inches(4.9), C_CARD, C_BORDER_ACCENT)
    tf_l2 = card_l2.text_frame
    tf_l2.word_wrap = True
    tf_l2.margin_left = Inches(0.4)
    tf_l2.margin_right = Inches(0.4)
    tf_l2.margin_top = Inches(0.35)

    p = tf_l2.paragraphs[0]
    p.text = "⚖️ Live Generated Notice of Liability"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_PRIMARY

    notice_preview = (
        "TO: L&T Infrastructure Engineering Ltd (NHAI-2023-DL-48)\n"
        "CORRIDOR: Delhi-Gurugram Expressway (NH-48)\n\n"
        "STATUTORY NOTICE UNDER CLAUSE 17:\n"
        "• Defect: HIGH SEVERITY POTHOLE (Depth: 6.8 cm, Vol: 0.042 m3)\n"
        "• Spatial Hex: 8c61... | GPS: 28.4975° N, 77.0865° E\n"
        "• MoRTH Schedule of Rates (SOR) Cost: ₹3,570 INR\n"
        "• Status: ACTIVE DEFECT LIABILITY PERIOD\n\n"
        "STATUTORY DIRECTIVE:\n"
        "Rectify defect within 14 Business Days. Failure authorizes third-party "
        "repair charged against contractor's Performance Bank Guarantee (PBG) retention escrow."
    )
    pn = tf_l2.add_paragraph()
    pn.text = notice_preview
    pn.font.size = Pt(10)
    pn.font.color.rgb = C_TEXT_BODY
    pn.space_before = Pt(10)

    # =========================================================================
    # SLIDE 9: LIVE DEMONSTRATION VIDEO (Embedded Video Stream)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s9)
    add_header(s9, "Live Video Demonstration: Real-Time Road Defect Assessment", "EMBEDDED VIDEO DEMO")

    # Left: Embed the actual playable video file!
    video_file = Path("docs/demo_outputs/expected_demo_output.mp4")
    poster_img = Path("docs/demo_outputs/reference_defect_detection_1.jpg")
    
    if video_file.exists() and poster_img.exists():
        s9.shapes.add_movie(
            str(video_file),
            Inches(0.9), Inches(1.7), Inches(6.0), Inches(4.9),
            poster_frame_image=str(poster_img),
            mime_type="video/mp4"
        )
    elif poster_img.exists():
        s9.shapes.add_picture(str(poster_img), Inches(0.9), Inches(1.7), Inches(6.0), Inches(4.9))

    # Right: Video Telemetry Breakdown
    c_vbreak = add_card(s9, Inches(7.2), Inches(1.7), Inches(5.233), Inches(4.9), C_CARD, C_BORDER_ACCENT)
    tf_vb = c_vbreak.text_frame
    tf_vb.word_wrap = True
    tf_vb.margin_left = Inches(0.4)
    tf_vb.margin_right = Inches(0.4)
    tf_vb.margin_top = Inches(0.35)

    pv = tf_vb.paragraphs[0]
    pv.text = "📹 What You Are Seeing in the Video:"
    pv.font.size = Pt(16)
    pv.font.bold = True
    pv.font.color.rgb = C_SAFFRON

    v_cues = [
        ("Real-Time AI Detection Overlay", "Bounding boxes with corner brackets pin defect boundaries at 45+ FPS."),
        ("Physical Depth & Volume", "Live reading of depth (cm) and volume (m3) computed without LiDAR hardware."),
        ("MoRTH Schedule of Rates (SOR)", "Cost calculated in real-time in Indian Rupees (₹) based on official MoRTH asphalt repair rates."),
        ("Active Contractor & DLP Status", "Banner tags the responsible EPC contractor (L&T / NHAI) and confirms active Clause 17 liability."),
        ("PostGIS Cloud Deduplication", "Syncs directly to Supabase Cloud; multiple passes merge seamlessly within 3m radius.")
    ]
    for vt, vd in v_cues:
        p_t = tf_vb.add_paragraph()
        p_t.text = vt
        p_t.font.size = Pt(11.5)
        p_t.font.bold = True
        p_t.font.color.rgb = C_TEXT_PRIMARY
        p_t.space_before = Pt(8)

        p_d = tf_vb.add_paragraph()
        p_d.text = vd
        p_d.font.size = Pt(10)
        p_d.font.color.rgb = C_TEXT_MUTED
        p_d.space_before = Pt(2)

    # =========================================================================
    # SLIDE 10: LIVE WINDSHIELD DASHBOARD & CONTROLS
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s10)
    add_header(s10, "Live Windshield Dashboard: Real-Time Assessment Interface", "FRONTEND & VISUALIZATION")

    # Left: Reference Image 2
    if ref_img2.exists():
        s10.shapes.add_picture(str(ref_img2), Inches(0.9), Inches(1.7), Inches(5.6), Inches(4.9))

    # Right: Dashboard Capabilities
    c_dash = add_card(s10, Inches(6.833), Inches(1.7), Inches(5.6), Inches(4.9), C_CARD, C_BORDER)
    tf_d = c_dash.text_frame
    tf_d.word_wrap = True
    tf_d.margin_left = Inches(0.4)
    tf_d.margin_right = Inches(0.4)
    tf_d.margin_top = Inches(0.35)

    p = tf_d.paragraphs[0]
    p.text = "Dashboard Features & Interactive Controls:"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_SAFFRON

    dash_features = [
        ("Dashcam Video Upload", "Drag-and-drop any .mp4 or .mov dashcam video. Runs real-time frame inference with bounding boxes and physical depth overlay."),
        ("Interactive Lat/Lon & Web Resolution", "Select preset highways or enter custom coordinates. Live OSM web call resolves road name and contractor in 0.2s."),
        ("3D Pydeck Spatial Hexagon Grid", "Visualizes defect density across road corridors with interactive 3D camera elevation angles and color-coded severity tiers."),
        ("Live Supabase Sync Telemetry", "Real-time counters tracking Total Defects Logged, Critical Violations, Supabase Records Synced, and Total Liability in ₹.")
    ]
    for dt, dd in dash_features:
        p_t = tf_d.add_paragraph()
        p_t.text = dt
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = C_TEXT_PRIMARY
        p_t.space_before = Pt(10)

        p_d = tf_d.add_paragraph()
        p_d.text = dd
        p_d.font.size = Pt(10.5)
        p_d.font.color.rgb = C_TEXT_MUTED
        p_d.space_before = Pt(2)

    # =========================================================================
    # SLIDE 11: FEASIBILITY, LOW COST & EDGE METRICS
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s11)
    add_header(s11, "Engineering Feasibility: Low Cost, 45+ FPS & High Viability", "TECHNICAL FEASIBILITY")

    metrics_clean = [
        ("⚡ 45+ FPS Edge Speed", "Real-Time Inference", 
         "Runs on modern laptop GPUs (RTX 5050) and edge SBCs (Jetson Orin). Fallback CPU pipeline runs smoothly at 18 FPS."),
        ("💰 Under ₹4,000 Total Cost", "Zero Special Hardware", 
         "Works with existing consumer dashcams or Android smartphones. No ₹25-Lakh LiDAR survey vans required."),
        ("☁️ Zero Server DevOps", "Supabase Cloud DB", 
         "PostgreSQL + PostGIS hosted on Supabase Cloud. Zero local maintenance, zero Docker daemon crashes, auto-scaling."),
        ("🔋 Low Power Consumption", "Vehicle Powered", 
         "Draws under 15W. Powered directly from standard 12V vehicle cigarette lighter adapter or USB-C power bank."),
        ("🌐 Offline Resilience", "Store-and-Forward", 
         "Queues defect records locally if rural 4G/5G signal drops, syncing automatically to Supabase upon reconnection."),
        ("📜 Regulatory Alignment", "MoRTH & eMARG Native", 
         "Directly aligns with MoRTH EPC Clause 17, PMGSY 5-year maintenance norms, and IRC:82 repair guidelines.")
    ]

    for idx, (m_title, m_sub, m_desc) in enumerate(metrics_clean):
        col = idx % 3
        row = idx // 3
        m_left = Inches(0.9 + col * 3.95)
        m_top = Inches(1.7 + row * 2.5)

        card = add_card(s11, m_left, m_top, Inches(3.65), Inches(2.25), C_CARD, C_BORDER_ACCENT if idx == 0 else C_BORDER)
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.3)
        tf.margin_right = Inches(0.3)
        tf.margin_top = Inches(0.2)

        p1 = tf.paragraphs[0]
        p1.text = m_title
        p1.font.size = Pt(13)
        p1.font.bold = True
        p1.font.color.rgb = C_SAFFRON

        p2 = tf.add_paragraph()
        p2.text = m_sub
        p2.font.size = Pt(11)
        p2.font.bold = True
        p2.font.color.rgb = C_TEXT_PRIMARY
        p2.space_before = Pt(3)

        p3 = tf.add_paragraph()
        p3.text = m_desc
        p3.font.size = Pt(10)
        p3.font.color.rgb = C_TEXT_MUTED
        p3.space_before = Pt(4)

    # =========================================================================
    # SLIDE 12: WHY PATHGUARD WINS & CLOSING
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s12)
    add_header(s12, "Why PathGuard-AI Wins: Complete Hackathon Alignment", "CONCLUSION & IMPACT")

    card_eval = add_card(s12, Inches(0.9), Inches(1.7), Inches(11.533), Inches(4.0), C_CARD, C_BORDER)
    tf_e = card_eval.text_frame
    tf_e.word_wrap = True
    tf_e.margin_left = Inches(0.5)
    tf_e.margin_right = Inches(0.5)
    tf_e.margin_top = Inches(0.35)

    p = tf_e.paragraphs[0]
    p.text = "Hackathon Evaluation Alignment Scorecard:"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_SAFFRON

    eval_items = [
        ("1. Technical Depth & Innovation", "End-to-end integration: YOLOv8 defect detection + MiDaS 3D depth + OpenStreetMap live web geocoding + Uber H3 hexagons + Supabase PostGIS spatial deduplication."),
        ("2. Real-World Feasibility & Working Code", "Working code tested with real Roboflow dataset images, live browser UI with video upload, custom Lat/Lon inputs, and sub-second web road detection."),
        ("3. Measurable Economic & Social Impact", "Transforms a ₹15,000 Crore public loss into contractor accountability, eliminating duplicate repair billing and preventing fatal road accidents."),
        ("4. Clean Modular Engineering", "Clean Python architecture (pathguard.vision, pathguard.spatial, pathguard.database, pathguard.geocoding, pathguard.contracts) synced to GitHub.")
    ]
    for et, ed in eval_items:
        p_t = tf_e.add_paragraph()
        p_t.text = et
        p_t.font.size = Pt(12.5)
        p_t.font.bold = True
        p_t.font.color.rgb = C_GREEN
        p_t.space_before = Pt(8)

        p_d = tf_e.add_paragraph()
        p_d.text = ed
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = C_TEXT_BODY
        p_d.space_before = Pt(2)

    # Footer Card
    foot = add_card(s11, Inches(0.9), Inches(5.95), Inches(11.533), Inches(0.95), C_CARD, C_BORDER_ACCENT)
    tf_ft = foot.text_frame
    tf_ft.word_wrap = True
    tf_ft.margin_left = Inches(0.5)
    tf_ft.margin_top = Inches(0.18)

    pf1 = tf_ft.paragraphs[0]
    pf1.text = "TEAM: Chaparla Monish  |  Mogalapu Hasini Priya  |  Pappala Likhitha  |  Malapati Mamatha"
    pf1.font.size = Pt(12)
    pf1.font.bold = True
    pf1.font.color.rgb = C_TEXT_PRIMARY

    pf2 = tf_ft.add_paragraph()
    pf2.text = "GitHub: github.com/monishchaparla/PathGuard-AI  |  Expected Demo Video: docs/demo_outputs/expected_demo_output.mp4"
    pf2.font.size = Pt(10)
    pf2.font.color.rgb = C_SAFFRON
    pf2.space_before = Pt(2)

    # Save Clean Presentation
    clean_ppt_path = output_dir / "PathGuard_AI_Clean_Pitch_Deck.pptx"
    prs.save(str(clean_ppt_path))
    print(f"[SUCCESS] Clean Minimalist White Deck generated at: {clean_ppt_path}")

    # Also overwrite the main deck if not locked by PowerPoint
    main_ppt_path = output_dir / "PathGuard_AI_Winning_Hackathon_Deck.pptx"
    try:
        prs.save(str(main_ppt_path))
        print(f"[SUCCESS] Updated main deck at: {main_ppt_path}")
    except PermissionError:
        print(f"[NOTE] '{main_ppt_path.name}' is currently open in PowerPoint; saved clean version to '{clean_ppt_path.name}'.")

if __name__ == "__main__":
    create_clean_deck()


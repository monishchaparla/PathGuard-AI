CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS road_defects (
    ticket_id TEXT PRIMARY KEY,
    h3_res11 TEXT NOT NULL,
    h3_res12 TEXT NOT NULL,
    geom GEOMETRY(Point, 4326) NOT NULL,
    width_cm REAL NOT NULL,
    length_cm REAL NOT NULL,
    depth_cm REAL NOT NULL,
    volume_m3 REAL NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    best_q_score REAL NOT NULL DEFAULT 0.0,
    best_image_path TEXT,
    camera_angle_deg REAL,
    imu_az_g REAL,
    classification TEXT CHECK (classification IN (
        'ACTIONABLE_CONTRACTOR_DEFECT',
        'EXCLUDED_TRAFFIC_OVERLOAD',
        'EXPIRED_MUNICIPAL_MAINTENANCE',
        'PENDING_CLASSIFICATION'
    )) DEFAULT 'PENDING_CLASSIFICATION',
    contract_id TEXT,
    contractor_name TEXT,
    contractor_email TEXT,
    road_name TEXT,
    dlp_type TEXT,
    dlp_start_date DATE,
    dlp_end_date DATE,
    notice_sent BOOLEAN DEFAULT FALSE,
    notice_sent_date TIMESTAMP,
    cure_deadline DATE,
    estimated_repair_cost_inr REAL,
    retention_locked BOOLEAN DEFAULT FALSE,
    status TEXT DEFAULT 'OPEN' CHECK (status IN ('OPEN','NOTICE_SENT','UNDER_REPAIR','VERIFIED_RECTIFIED','CLOSED')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ticket_history (
    id SERIAL PRIMARY KEY,
    ticket_id TEXT REFERENCES road_defects(ticket_id),
    event_type TEXT NOT NULL,
    q_score REAL,
    image_path TEXT,
    depth_cm REAL,
    width_cm REAL,
    length_cm REAL,
    latitude REAL,
    longitude REAL,
    imu_az_g REAL,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contracts (
    contract_id TEXT PRIMARY KEY,
    road_name TEXT NOT NULL,
    contractor_name TEXT NOT NULL,
    contractor_email TEXT,
    supervising_engineer_email TEXT,
    dlp_type TEXT NOT NULL,
    dlp_start_date DATE NOT NULL,
    dlp_end_date DATE NOT NULL,
    total_contract_value_inr REAL,
    retention_percentage REAL DEFAULT 5.0,
    retention_balance_inr REAL,
    pbg_active BOOLEAN DEFAULT TRUE,
    retention_release_locked BOOLEAN DEFAULT FALSE,
    design_esals REAL,
    actual_esals REAL DEFAULT 0,
    h3_corridor_indexes TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_defects_geom ON road_defects USING GIST(geom);
CREATE INDEX idx_defects_h3_res12 ON road_defects(h3_res12);
CREATE INDEX idx_defects_h3_res11 ON road_defects(h3_res11);
CREATE INDEX idx_defects_status ON road_defects(status);
CREATE INDEX idx_contracts_corridor ON contracts USING GIN(h3_corridor_indexes);
CREATE INDEX idx_history_ticket ON ticket_history(ticket_id);

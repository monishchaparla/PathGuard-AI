"""PostGIS Database Engine with spatial deduplication."""
import logging
import json
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from sqlalchemy import create_engine, text, Column, Text, Float, Boolean, Date, DateTime, ARRAY
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

class RoadDefect(Base):
    __tablename__ = 'road_defects'
    
    ticket_id = Column(Text, primary_key=True)
    h3_res11 = Column(Text, nullable=False, index=True)
    h3_res12 = Column(Text, nullable=False)
    geom = Column(Geometry('POINT', srid=4326), nullable=False, index=True)
    width_cm = Column(Float, nullable=False)
    length_cm = Column(Float, nullable=False)
    depth_cm = Column(Float, nullable=False)
    volume_m3 = Column(Float, nullable=False)
    severity = Column(Text, nullable=False)
    best_q_score = Column(Float, nullable=False)
    best_image_path = Column(Text)
    imu_az_g = Column(Float)
    status = Column(Text, nullable=False, default='OPEN')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class TicketHistory(Base):
    __tablename__ = 'ticket_history'
    
    id = Column(Text, primary_key=True)
    ticket_id = Column(Text, nullable=False, index=True)
    action_type = Column(Text, nullable=False)
    q_score = Column(Float)
    depth_cm = Column(Float)
    image_path = Column(Text)
    detection_data = Column(JSONB)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

class Contract(Base):
    __tablename__ = 'contracts'
    
    contract_id = Column(Text, primary_key=True)
    coverage_area_h3_res11 = Column(ARRAY(Text))
    retention_release_locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabaseEngine:
    def __init__(self, host, port, dbname, user, password):
        self.db_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def connect(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def find_nearby_defect(self, lon: float, lat: float, radius_m: float = 3.0) -> Optional[dict]:
        query = text(\"\"\"
            SELECT ticket_id, best_q_score, depth_cm, width_cm, length_cm, severity
            FROM road_defects
            WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius)
            ORDER BY ST_Distance(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)
            LIMIT 1;
        \"\"\")
        try:
            with self.SessionLocal() as session:
                result = session.execute(query, {"lon": lon, "lat": lat, "radius": radius_m}).fetchone()
                if result:
                    return dict(result._mapping)
                return None
        except Exception as e:
            logger.error(f"Error finding nearby defect: {e}")
            return None

    def merge_existing_ticket(self, ticket_id: str, q_score: float, depth_cm: float, image_path: str, detection_data: dict) -> dict:
        try:
            with self.SessionLocal() as session:
                defect = session.query(RoadDefect).filter(RoadDefect.ticket_id == ticket_id).first()
                if not defect:
                    raise ValueError(f"Ticket {ticket_id} not found")
                
                image_updated = False
                if q_score > defect.best_q_score:
                    defect.best_image_path = image_path
                    defect.best_q_score = q_score
                    image_updated = True
                
                defect.depth_cm = max(defect.depth_cm, depth_cm)
                
                history_entry = TicketHistory(
                    id=f"{ticket_id}_{datetime.utcnow().timestamp()}",
                    ticket_id=ticket_id,
                    action_type='MERGE',
                    q_score=q_score,
                    depth_cm=depth_cm,
                    image_path=image_path,
                    detection_data=detection_data,
                    timestamp=datetime.utcnow()
                )
                session.add(history_entry)
                session.commit()
                return {"status": "MERGED_EXISTING", "ticket_id": ticket_id, "image_updated": image_updated}
        except Exception as e:
            logger.error(f"Error merging ticket {ticket_id}: {e}")
            return {"status": "ERROR", "message": str(e)}

    def create_new_ticket(self, ticket_id: str, h3_res11: str, h3_res12: str, lat: float, lon: float, 
                          width_cm: float, length_cm: float, depth_cm: float, volume_m3: float, 
                          severity: str, q_score: float, image_path: str, imu_az_g: Optional[float] = None) -> dict:
        try:
            with self.SessionLocal() as session:
                new_defect = RoadDefect(
                    ticket_id=ticket_id,
                    h3_res11=h3_res11,
                    h3_res12=h3_res12,
                    geom=f"SRID=4326;POINT({lon} {lat})",
                    width_cm=width_cm,
                    length_cm=length_cm,
                    depth_cm=depth_cm,
                    volume_m3=volume_m3,
                    severity=severity,
                    best_q_score=q_score,
                    best_image_path=image_path,
                    imu_az_g=imu_az_g
                )
                
                history_entry = TicketHistory(
                    id=f"{ticket_id}_{datetime.utcnow().timestamp()}",
                    ticket_id=ticket_id,
                    action_type='CREATE',
                    q_score=q_score,
                    depth_cm=depth_cm,
                    image_path=image_path,
                    detection_data={"initial_creation": True},
                    timestamp=datetime.utcnow()
                )
                
                session.add(new_defect)
                session.add(history_entry)
                session.commit()
                return {"status": "CREATED_NEW", "ticket_id": ticket_id}
        except Exception as e:
            logger.error(f"Error creating new ticket: {e}")
            return {"status": "ERROR", "message": str(e)}

    def process_detection(self, h3_cell: Any, detection_data: dict, is_pentagon: bool = False, pentagon_radius_m: float = 15.0) -> dict:
        radius_m = pentagon_radius_m if is_pentagon else 3.0
        lat = h3_cell.lat
        lon = h3_cell.lon
        
        nearby = self.find_nearby_defect(lon, lat, radius_m)
        
        if nearby:
            return self.merge_existing_ticket(
                ticket_id=nearby['ticket_id'],
                q_score=detection_data.get('q_score', 0.0),
                depth_cm=detection_data.get('depth_cm', 0.0),
                image_path=detection_data.get('image_path', ''),
                detection_data=detection_data
            )
        else:
            ticket_id = f"TKT-H3-{h3_cell.res12}"
            return self.create_new_ticket(
                ticket_id=ticket_id,
                h3_res11=h3_cell.res11,
                h3_res12=h3_cell.res12,
                lat=lat,
                lon=lon,
                width_cm=detection_data.get('width_cm', 0.0),
                length_cm=detection_data.get('length_cm', 0.0),
                depth_cm=detection_data.get('depth_cm', 0.0),
                volume_m3=detection_data.get('volume_m3', 0.0),
                severity=detection_data.get('severity', 'UNKNOWN'),
                q_score=detection_data.get('q_score', 0.0),
                image_path=detection_data.get('image_path', ''),
                imu_az_g=detection_data.get('imu_az_g')
            )

    def find_contract_for_location(self, h3_res11: str) -> Optional[dict]:
        try:
            with self.SessionLocal() as session:
                query = text("SELECT contract_id, retention_release_locked FROM contracts WHERE :cell = ANY(coverage_area_h3_res11) LIMIT 1;")
                result = session.execute(query, {"cell": h3_res11}).fetchone()
                if result:
                    return dict(result._mapping)
                return None
        except Exception as e:
            logger.error(f"Error finding contract for {h3_res11}: {e}")
            return None

    def lock_retention(self, contract_id: str) -> bool:
        try:
            with self.SessionLocal() as session:
                contract = session.query(Contract).filter(Contract.contract_id == contract_id).first()
                if contract:
                    contract.retention_release_locked = True
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error locking retention for {contract_id}: {e}")
            return False

    def get_open_tickets_for_corridor(self, h3_res11: str) -> list[dict]:
        try:
            with self.SessionLocal() as session:
                defects = session.query(RoadDefect).filter(
                    RoadDefect.h3_res11 == h3_res11,
                    RoadDefect.status == 'OPEN'
                ).all()
                return [
                    {
                        "ticket_id": d.ticket_id,
                        "severity": d.severity,
                        "depth_cm": d.depth_cm
                    } for d in defects
                ]
        except Exception as e:
            logger.error(f"Error fetching open tickets for {h3_res11}: {e}")
            return []

    def update_ticket_status(self, ticket_id: str, status: str) -> bool:
        try:
            with self.SessionLocal() as session:
                defect = session.query(RoadDefect).filter(RoadDefect.ticket_id == ticket_id).first()
                if defect:
                    defect.status = status
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error updating status for {ticket_id}: {e}")
            return False

    def get_ticket_with_history(self, ticket_id: str) -> dict:
        try:
            with self.SessionLocal() as session:
                defect = session.query(RoadDefect).filter(RoadDefect.ticket_id == ticket_id).first()
                if not defect:
                    return {}
                
                history = session.query(TicketHistory).filter(TicketHistory.ticket_id == ticket_id).order_by(TicketHistory.timestamp).all()
                
                return {
                    "ticket_id": defect.ticket_id,
                    "h3_res11": defect.h3_res11,
                    "h3_res12": defect.h3_res12,
                    "status": defect.status,
                    "history": [
                        {
                            "action_type": h.action_type,
                            "timestamp": h.timestamp.isoformat(),
                            "q_score": h.q_score
                        } for h in history
                    ]
                }
        except Exception as e:
            logger.error(f"Error fetching ticket {ticket_id}: {e}")
            return {}

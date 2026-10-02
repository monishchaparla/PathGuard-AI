"""Module 4: Statutory Notice Generation & Financial Escrow Gatekeeper."""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
import json

logger = logging.getLogger(__name__)

def estimate_repair_cost(width_cm: float, length_cm: float, depth_cm: float, sor_rate_per_m3: float = 8500.0) -> Tuple[float, float]:
    """Estimate the repair volume and cost based on Schedule of Rates (SOR)."""
    volume_m3 = (width_cm / 100.0) * (length_cm / 100.0) * (depth_cm / 100.0)
    cost_inr = volume_m3 * sor_rate_per_m3
    return volume_m3, cost_inr

def compute_cure_deadline(dispatch_date: date, business_days: int = 14) -> date:
    """Calculate the deadline skipping weekends (Saturday and Sunday)."""
    current_date = dispatch_date
    days_added = 0
    while days_added < business_days:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:  # 0-4 are Monday to Friday
            days_added += 1
    return current_date

def generate_notice_body(contract_id: str, road_name: str, h3_index: str, lat: float, lon: float, 
                         width_cm: float, length_cm: float, depth_cm: float, volume_m3: float, 
                         severity: str, estimated_cost_inr: float, deadline_date: date) -> str:
    """Generate the official legal notice body text."""
    body = f"""OFFICIAL LEGAL NOTICE

Contract ID: {contract_id}
Road Name: {road_name}
Location Index: Uber H3 Res-12 {h3_index} (Lat: {lat}, Lon: {lon})
Defect Dimensions: {width_cm}cm x {length_cm}cm x {depth_cm}cm (Volume: {volume_m3:.4f} m³)
Classification: PATENT WORKMANSHIP FAILURE (Severity: {severity})

Take notice that under Clause 17 of the governing agreement, you are required
to complete full surface restoration within 14 Business Days (Deadline: {deadline_date}).

Failure to rectify will result in immediate execution of repairs via third-party
agency, with the total estimated cost of ₹{estimated_cost_inr:,.2f} deducted
directly from your held Retention Security Deposit."""
    return body

def generate_notice_payload(ticket: Dict[str, Any], contract: Dict[str, Any], defect_dims: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble full email payload dict."""
    try:
        dispatch_date = date.today()
        deadline_date = compute_cure_deadline(dispatch_date)
        
        volume_m3, cost_inr = estimate_repair_cost(
            width_cm=defect_dims.get('width_cm', 0),
            length_cm=defect_dims.get('length_cm', 0),
            depth_cm=defect_dims.get('depth_cm', 0)
        )
        
        body_text = generate_notice_body(
            contract_id=contract.get('contract_id', 'UNKNOWN'),
            road_name=contract.get('road_name', 'UNKNOWN'),
            h3_index=ticket.get('h3_index', 'UNKNOWN'),
            lat=ticket.get('lat', 0.0),
            lon=ticket.get('lon', 0.0),
            width_cm=defect_dims.get('width_cm', 0.0),
            length_cm=defect_dims.get('length_cm', 0.0),
            depth_cm=defect_dims.get('depth_cm', 0.0),
            volume_m3=volume_m3,
            severity=ticket.get('severity', 'UNKNOWN'),
            estimated_cost_inr=cost_inr,
            deadline_date=deadline_date
        )
        
        return {
            'recipient_email': contract.get('contractor_email'),
            'cc_email': contract.get('supervising_engineer_email'),
            'subject': f"URGENT: Defect Rectification Notice - {contract.get('contract_id', 'UNKNOWN')} - {contract.get('road_name', 'UNKNOWN')}",
            'body_text': body_text,
            'cost_inr': cost_inr,
            'deadline_date': deadline_date.isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating notice payload: {e}")
        return {}

class NoticeDispatcher:
    """Handles dispatch of legal notices to contractors."""
    def __init__(self, smtp_server: str = 'smtp.gmail.com', smtp_port: int = 587, 
                 sender_email: Optional[str] = None, sender_password: Optional[str] = None):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password

    def send_notice(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send via smtplib with TLS or mock if not configured."""
        if not self.sender_email or not self.sender_password:
            logger.info("SMTP credentials not provided. Mocking notice send for demo.")
            return {
                "success": True,
                "message": "Mock send successful",
                "payload": payload,
                "mocked": True
            }
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = payload.get('recipient_email', '')
            if payload.get('cc_email'):
                msg['Cc'] = payload.get('cc_email', '')
            msg['Subject'] = payload.get('subject', 'Notice')
            
            msg.attach(MIMEText(payload.get('body_text', ''), 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            recipients = [msg['To']]
            if msg['Cc']:
                recipients.append(msg['Cc'])
                
            server.sendmail(self.sender_email, recipients, msg.as_string())
            server.quit()
            
            return {"success": True, "message": "Email sent successfully", "mocked": False}
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {"success": False, "error": str(e)}

    def generate_and_send(self, ticket_data: Dict[str, Any], contract_data: Dict[str, Any], 
                          defect_dims: Dict[str, Any], db_engine=None) -> Dict[str, Any]:
        """Full pipeline to generate payload, optionally lock retention, and send notice."""
        try:
            payload = generate_notice_payload(ticket_data, contract_data, defect_dims)
            
            if db_engine:
                logger.info(f"Database engine provided. Updating ticket status and locking retention for {payload.get('cost_inr', 0)} INR.")
                # Mocking DB operations for the purpose of the pipeline
                pass
                
            send_result = self.send_notice(payload)
            
            return {
                "status": "success" if send_result.get("success") else "failure",
                "send_result": send_result,
                "payload_generated": payload
            }
        except Exception as e:
            logger.error(f"Error in generate_and_send pipeline: {e}")
            return {"status": "failure", "error": str(e)}

"""Tender Document Ingestion via PyMuPDF (fitz).

Extracts contract metadata, DLP terms, contractor info from local PDF tenders.
"""
import re
import logging
from pathlib import Path
from datetime import date, datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    logging.warning("PyMuPDF not installed. PDF ingestion disabled.")

logger = logging.getLogger(__name__)

@dataclass
class ContractMetadata:
    contract_id: Optional[str] = None
    road_name: Optional[str] = None
    contractor_name: Optional[str] = None
    contractor_email: Optional[str] = None
    supervising_engineer_email: Optional[str] = None
    dlp_type: Optional[str] = None
    completion_date: Optional[date] = None
    dlp_start_date: Optional[date] = None
    dlp_end_date: Optional[date] = None
    total_contract_value_inr: Optional[float] = None
    retention_percentage: Optional[float] = None
    design_esals: Optional[float] = None
    raw_text: str = ""

class TenderParser:
    """Parser for extracting contract data from PDF tenders."""
    
    def __init__(self, tender_dir: str = 'tenders/'):
        self.tender_dir = Path(tender_dir)
        
    def extract_text(self, pdf_path: str) -> str:
        """Extract full text from PDF using fitz."""
        if fitz is None:
            logger.error("PyMuPDF not available.")
            return ""
            
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""

    def parse_contract_id(self, text: str) -> Optional[str]:
        """Regex for contract IDs."""
        patterns = [
            r"CONTRACT\s*[-:]\s*([A-Z0-9\-]+)",
            r"AGREEMENT\s+NO\.?\s*[-:]\s*([A-Z0-9\-]+)",
            r"Contract\s+ID\s*:\s*([A-Z0-9\-]+)"
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def parse_dates(self, text: str) -> Dict[str, Optional[date]]:
        """Extract dates from text."""
        dates = {
            "completion_date": None,
            "dlp_start_date": None,
            "dlp_end_date": None
        }
        
        date_pattern = r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
        
        comp_match = re.search(r"Completion\s+Date\s*[:\-]\s*" + date_pattern, text, re.IGNORECASE)
        if comp_match:
            try:
                date_str = comp_match.group(1).replace('-', '/')
                parts = date_str.split('/')
                if len(parts[2]) == 2:
                    parts[2] = "20" + parts[2]
                dates["completion_date"] = datetime.strptime(f"{parts[0]}/{parts[1]}/{parts[2]}", "%d/%m/%Y").date()
            except ValueError:
                pass
                
        # Simple extraction for demo purposes
        dlp_start = re.search(r"DLP\s+Start\s*[:\-]\s*" + date_pattern, text, re.IGNORECASE)
        if dlp_start:
            try:
                date_str = dlp_start.group(1).replace('-', '/')
                parts = date_str.split('/')
                if len(parts[2]) == 2:
                    parts[2] = "20" + parts[2]
                dates["dlp_start_date"] = datetime.strptime(f"{parts[0]}/{parts[1]}/{parts[2]}", "%d/%m/%Y").date()
            except ValueError:
                pass
                
        return dates

    def parse_dlp_type(self, text: str) -> str:
        """Keyword matching for pavement type."""
        text_lower = text.lower()
        if 'rigid' in text_lower or 'concrete' in text_lower:
            return "concrete_pavement"
        elif 'overlay' in text_lower or 'renewal' in text_lower or '40mm' in text_lower:
            return "overlay_renewal"
        elif 'rural' in text_lower or 'pmgsy' in text_lower:
            return "pmgsy_rural"
        elif 'cpwd' in text_lower or 'civil works' in text_lower:
            return "cpwd_civil_works"
        return "bituminous_pavement"

    def parse_contractor_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extract contractor name and email."""
        info = {
            "name": None,
            "email": None
        }
        name_match = re.search(r"Contractor\s*(?:Name)?\s*[:\-]\s*([A-Za-z\s.,]+)", text, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip()
            # Stop at newline or obvious end
            info["name"] = name.split('\n')[0].strip()
            
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        if email_match:
            info["email"] = email_match.group(0).strip()
            
        return info

    def parse_contract_value(self, text: str) -> Optional[float]:
        """Extract INR amounts."""
        match = re.search(r"(?:INR|₹|Rs\.?)\s*([\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                return None
        return None

    def ingest_pdf(self, pdf_path: str) -> ContractMetadata:
        """Full ingestion pipeline for a single PDF."""
        text = self.extract_text(pdf_path)
        
        dates = self.parse_dates(text)
        contractor = self.parse_contractor_info(text)
        
        return ContractMetadata(
            contract_id=self.parse_contract_id(text),
            contractor_name=contractor.get("name"),
            contractor_email=contractor.get("email"),
            dlp_type=self.parse_dlp_type(text),
            completion_date=dates.get("completion_date"),
            dlp_start_date=dates.get("dlp_start_date"),
            total_contract_value_inr=self.parse_contract_value(text),
            raw_text=text
        )

    def ingest_directory(self) -> List[ContractMetadata]:
        """Process all PDFs in tender_dir."""
        results = []
        if not self.tender_dir.exists() or not self.tender_dir.is_dir():
            logger.warning(f"Tender directory {self.tender_dir} does not exist.")
            return results
            
        for pdf_file in self.tender_dir.glob('*.pdf'):
            try:
                metadata = self.ingest_pdf(str(pdf_file))
                results.append(metadata)
            except Exception as e:
                logger.error(f"Failed to ingest {pdf_file}: {e}")
                
        return results

    def create_sample_tender_text(self) -> str:
        """Generate sample tender text for demo/testing."""
        return '''
        AGREEMENT NO: CONTRACT-2023-A109
        Road Name: NH-44 Extension
        Contractor Name: BuildRight Infrastructure Pvt Ltd
        Email: contact@buildright.in
        Supervising Engineer: engineer@highwaydept.gov.in
        Pavement Type: 40mm Bituminous Concrete Overlay
        Completion Date: 15/06/2023
        DLP Start: 16/06/2023
        Total Value: INR 45,000,000
        Retention: 5%
        Design ESALs: 10.5
        '''

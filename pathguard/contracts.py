"""Module 3: Parametric Contractual Liability & DLP Aging Engine.

Implements MoRTH, eMARG, and CPWD DLP rules with wear-vs-workmanship evaluation.
"""
import logging
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

class DLPType(Enum):
    BITUMINOUS_PAVEMENT = "bituminous_pavement"  # (1825 days)
    CONCRETE_PAVEMENT = "concrete_pavement"  # (3650 days)
    OVERLAY_RENEWAL = "overlay_renewal"  # (1095 days)
    CPWD_CIVIL_WORKS = "cpwd_civil_works"  # (365 days)
    PMGSY_RURAL = "pmgsy_rural"  # (1825 days)

class DefectClassification(Enum):
    ACTIONABLE_CONTRACTOR_DEFECT = "ACTIONABLE_CONTRACTOR_DEFECT"
    EXCLUDED_TRAFFIC_OVERLOAD = "EXCLUDED_TRAFFIC_OVERLOAD"
    EXPIRED_MUNICIPAL_MAINTENANCE = "EXPIRED_MUNICIPAL_MAINTENANCE"
    PENDING_CLASSIFICATION = "PENDING_CLASSIFICATION"

def get_dlp_days(dlp_type: DLPType) -> int:
    """Return the DLP duration in days based on the DLP type."""
    mapping = {
        DLPType.BITUMINOUS_PAVEMENT: 1825,
        DLPType.CONCRETE_PAVEMENT: 3650,
        DLPType.OVERLAY_RENEWAL: 1095,
        DLPType.CPWD_CIVIL_WORKS: 365,
        DLPType.PMGSY_RURAL: 1825,
    }
    return mapping.get(dlp_type, 1825)

def compute_defect_score(severity_score: float, age_months: float, dlp_total_months: float, actual_esals: float, design_esals: float) -> float:
    """Calculate the parametric defect score."""
    if design_esals <= 0:
        esal_ratio = 1.0
    else:
        esal_ratio = actual_esals / design_esals
    
    if dlp_total_months <= 0:
        age_ratio = 1.0
    else:
        age_ratio = max(0.0, min(1.0, age_months / dlp_total_months))
        
    s_d = severity_score * (1.0 - age_ratio) * esal_ratio
    return float(s_d)

def severity_to_score(severity: str) -> float:
    """Convert severity string to numerical score."""
    sev = severity.upper()
    if sev == "LOW":
        return 1.0
    elif sev == "MEDIUM":
        return 2.0
    elif sev == "HIGH":
        return 3.0
    elif sev == "CRITICAL":
        return 5.0
    return 1.0

def classify_defect(severity: str, completion_date: date, inspection_date: date, dlp_type: DLPType, actual_esals: float, design_esals: float, esal_overload_threshold: float = 1.5) -> Tuple[DefectClassification, float]:
    """Classify the defect into one of the classification categories based on the decision tree."""
    try:
        esal_ratio = actual_esals / design_esals if design_esals > 0 else 1.0
        if esal_ratio > esal_overload_threshold:
            return DefectClassification.EXCLUDED_TRAFFIC_OVERLOAD, 0.0
            
        age_days = (inspection_date - completion_date).days
        age_months = age_days / 30.44
        dlp_days = get_dlp_days(dlp_type)
        dlp_total_months = dlp_days / 30.44
        
        if age_months > dlp_total_months:
            return DefectClassification.EXPIRED_MUNICIPAL_MAINTENANCE, 0.0
            
        severity_score = severity_to_score(severity)
        s_d = compute_defect_score(severity_score, age_months, dlp_total_months, actual_esals, design_esals)
        
        if s_d >= 1.0:
            return DefectClassification.ACTIONABLE_CONTRACTOR_DEFECT, s_d
        else:
            return DefectClassification.PENDING_CLASSIFICATION, s_d
            
    except Exception as e:
        logger.error(f"Error classifying defect: {e}")
        return DefectClassification.PENDING_CLASSIFICATION, 0.0

class DLPEngine:
    """Engine for evaluating defect liability based on wear vs workmanship."""
    def __init__(self, esal_overload_threshold: float = 1.5):
        self.esal_overload_threshold = esal_overload_threshold
        
    def evaluate(self, severity: str, contract_info: Dict[str, Any], inspection_date: Optional[date] = None) -> Dict[str, Any]:
        """Full evaluation of defect liability against contract terms."""
        if inspection_date is None:
            inspection_date = date.today()
            
        try:
            completion_date = contract_info.get('completion_date')
            if isinstance(completion_date, str):
                completion_date = datetime.strptime(completion_date, "%Y-%m-%d").date()
                
            dlp_type_str = contract_info.get('dlp_type', 'BITUMINOUS_PAVEMENT')
            if isinstance(dlp_type_str, DLPType):
                dlp_type = dlp_type_str
            else:
                dlp_type = DLPType(dlp_type_str.lower() if hasattr(dlp_type_str, 'lower') else dlp_type_str)
                
            actual_esals = float(contract_info.get('actual_esals', 0.0))
            design_esals = float(contract_info.get('design_esals', 1.0))
            
            classification, score = classify_defect(
                severity, completion_date, inspection_date, dlp_type, 
                actual_esals, design_esals, self.esal_overload_threshold
            )
            
            dlp_days = get_dlp_days(dlp_type)
            age_days = (inspection_date - completion_date).days
            dlp_remaining_days = max(0, dlp_days - age_days)
            
            return {
                "classification": classification.value,
                "defect_score": score,
                "dlp_remaining_days": dlp_remaining_days,
                "dlp_total_days": dlp_days,
                "age_days": age_days,
                "esal_ratio": actual_esals / design_esals if design_esals > 0 else 1.0
            }
            
        except Exception as e:
            logger.error(f"Error during DLP evaluation: {e}")
            return {
                "classification": DefectClassification.PENDING_CLASSIFICATION.value,
                "defect_score": 0.0,
                "error": str(e)
            }

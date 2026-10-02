import h3
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class H3Cell:
    """Represents a resolved H3 cell with metadata."""
    lat: float
    lon: float
    res11: str  # Corridor-level index
    res12: str  # Defect-level index
    is_pentagon: bool
    neighbors_res12: list[str]

class H3Engine:
    """Uber H3 Geospatial Indexing Engine with pentagon fallback handling."""
    
    def __init__(self, corridor_res=11, defect_res=12, kring_k=1):
        self.corridor_res = corridor_res
        self.defect_res = defect_res
        self.kring_k = kring_k
    
    def resolve(self, lat: float, lon: float) -> H3Cell:
        """Convert GPS coordinates to dual-resolution H3 cells.
        
        Resolution 11: ~1,071 m² cells (~24.9m edge) for corridor aggregation
        Resolution 12: ~153 m² cells (~9.4m edge) for individual defect ID
        """
        res11 = h3.latlng_to_cell(lat, lon, self.corridor_res)
        res12 = h3.latlng_to_cell(lat, lon, self.defect_res)
        
        is_pent = h3.is_pentagon(res12)
        
        if is_pent:
            logger.warning(f"Pentagon cell detected at ({lat}, {lon}): {res12}. Using PostGIS fallback.")
            neighbors = []  # Will use PostGIS buffer instead
        else:
            neighbors = list(h3.grid_disk(res12, self.kring_k))
        
        return H3Cell(
            lat=lat, lon=lon,
            res11=res11, res12=res12,
            is_pentagon=is_pent,
            neighbors_res12=neighbors
        )
    
    def generate_ticket_id(self, res12_index: str) -> str:
        """Generate globally unique ticket ID from H3 Res12 index."""
        return f"TKT-H3-{res12_index}"
    
    def get_corridor_cells(self, lat: float, lon: float, k: int = 3) -> list[str]:
        """Get k-ring of Resolution 11 cells for corridor analysis."""
        center = h3.latlng_to_cell(lat, lon, self.corridor_res)
        return list(h3.grid_disk(center, k))
    
    def cell_to_boundary(self, cell: str) -> list[tuple[float, float]]:
        """Get the lat/lng boundary vertices of an H3 cell for map rendering."""
        return h3.cell_to_boundary(cell)
    
    def cell_to_latlng(self, cell: str) -> tuple[float, float]:
        """Get center lat/lng of an H3 cell."""
        return h3.cell_to_latlng(cell)

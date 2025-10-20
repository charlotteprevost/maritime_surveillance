from typing import List, Optional
from pydantic import BaseModel
from enums import GearType, ShipType, NeuralVesselType

class SarFilterSet(BaseModel):
    flag: Optional[List[str]] = None                      # ISO3 codes
    geartype: Optional[List[GearType]] = None             # Gear categories
    shiptype: Optional[List[ShipType]] = None             # Vessel categories
    matched: Optional[bool] = False                       # Default to False
    neural_vessel_type: Optional[NeuralVesselType] = "public-global-sar-presence:latest"  # One of 3 categories
    vessel_id: Optional[str] = None                       # UUID string

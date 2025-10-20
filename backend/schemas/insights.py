from typing import List
from pydantic import BaseModel, Field
from enums import InsightType

class VesselRef(BaseModel):
    datasetId: str = Field(default="public-global-vessel-identity:latest")
    vesselId: str

class InsightsRequest(BaseModel):
    includes: List[InsightType]
    startDate: str = Field(..., pattern=r"\d{4}-\d{2}-\d{2}")
    endDate: str = Field(..., pattern=r"\d{4}-\d{2}-\d{2}")
    vessels: List[VesselRef]

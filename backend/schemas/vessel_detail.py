from typing import List, Optional
from pydantic import BaseModel, Field
from enums import VesselRegistryMatch, RegistryInfoDetail

class VesselDetailQueryParams(BaseModel):
    dataset: str = Field(default="public-global-vessel-identity:latest")
    includes: Optional[List[str]] = None                      # e.g. ["OWNERSHIP", "AUTHORIZATIONS"]
    registries_info_data: Optional[RegistryInfoDetail] = None # NONE | DELTA | ALL
    binary: Optional[bool] = False
    match_fields: Optional[List[VesselRegistryMatch]] = None  # e.g. ["SEVERAL_FIELDS", "NO_MATCH"]


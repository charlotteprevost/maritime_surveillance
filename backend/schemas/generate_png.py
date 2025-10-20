from typing import Optional, Literal
from pydantic import BaseModel, Field
from enums import Interval
from schemas.filters import SarFilterSet

class GeneratePngRequest(BaseModel):
    dataset: Literal["public-global-sar-presence:latest"] = Field(default="public-global-sar-presence:latest", Literal=True)
    interval: Optional[Interval] = Field(default="DAY", Literal=True)
    date_range: Optional[str] = Field(
        default=None,
        pattern=r"\d{4}-\d{2}-\d{2},\d{4}-\d{2}-\d{2}"
    )
    color: Optional[str] = Field(default="#002457", pattern=r"^#(?:[0-9a-fA-F]{3}){1,2}$")
    filters: Optional[SarFilterSet] = Field(default=None)

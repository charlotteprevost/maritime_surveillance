# from flask import current_app
# from pydantic import BaseModel, Field
# from typing import Optional, Literal
# from enums import Interval
# from schemas.filters import SarFilterSet
# from configs.config import SAR_TILE_STYLE

# STYLE_ID = SAR_TILE_STYLE["id"]

# class SarTileHeatmapRequest(BaseModel):
#     z: int
#     x: int
#     y: int
#     format: Optional[str] = "PNG"  # or MVT
#     interval: Optional[Interval] = None
#     date_range: Optional[str] = None
#     style: Literal[STYLE_ID] = Field(default=STYLE_ID, Literal=True)
#     filters: Optional[SarFilterSet] = None
#     datasets: Literal["public-global-sar-presence:latest"] = Field(default="public-global-sar-presence:latest", Literal=True)

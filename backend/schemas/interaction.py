from pydantic import BaseModel
from typing import List, Optional
from schemas.filters import SarFilterSet
from enums import Dataset

class InteractionRequest(BaseModel):
    z: int
    x: int
    y: int
    cells: List[int]
    datasets: List[Dataset]
    date_range: Optional[str] = None
    filters: Optional[SarFilterSet] = None
    limit: Optional[int] = None

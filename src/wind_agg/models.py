from typing import List, Literal
from pydantic import BaseModel, Field, HttpUrl

class ClaimRequest(BaseModel):
    claim_id: str
    loss_type: Literal["wind"]
    images: List[HttpUrl] = Field(min_length=1)
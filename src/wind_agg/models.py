from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, Field, HttpUrl

# -------- request -----------------------------------------------------------
class ClaimRequest(BaseModel):
    claim_id: str
    loss_type: Literal["wind"]
    images: List[HttpUrl] = Field(min_length=1)

# -------- response ----------------------------------------------------------
class SourceImages(BaseModel):
    total: int
    analyzed: int
    discarded_low_quality: int
    clusters: int

class AreaResult(BaseModel):
    area: str
    damage_confirmed: bool = False
    primary_peril: Literal["wind"] = "wind"
    count: int = 0
    avg_severity: float = 0.0
    representative_images: List[HttpUrl] = []
    notes: str | None = None

    # internal helpers (excluded from JSON)
    severities: List[int] = Field(default_factory=list, exclude=True)
    rep_imgs:   List[HttpUrl] = Field(default_factory=list, exclude=True)
    quality_weights: List[float] = Field(default_factory=list, exclude=True)

    def model_post_init(self, __context):
        # flatten rep_imgs into representative_images for output
        if self.rep_imgs and not self.representative_images:
            self.representative_images = [self.rep_imgs[0]]

class ClaimResponse(BaseModel):
    claim_id: str
    source_images: SourceImages
    overall_damage_severity: float
    areas: List[AreaResult]
    data_gaps: List[str]
    confidence: float
    generated_at: str
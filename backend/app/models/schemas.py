from typing import Literal, List, Dict, Any
from pydantic import BaseModel, HttpUrl, Field

Status = Literal["PASS", "WARN", "FAIL", "INFO"]

class Finding(BaseModel):
    id: str
    key: str
    title: str
    status: Status
    risk: Literal["low", "medium", "high"]
    confidence: Literal["low", "medium", "high"]
    evidence: Dict[str, Any] = {}
    recommendation: str

class ScanRequest(BaseModel):
    url: HttpUrl

class Scan(BaseModel):
    id: str
    url: HttpUrl
    score: int = 0
    findings: List[Finding] = Field(default_factory=list)

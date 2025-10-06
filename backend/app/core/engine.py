import asyncio
import uuid
from typing import List
from app.core.http import client_for
from app.models.schemas import Scan, Finding
from app.checks.hsts import HSTSCheck
from app.checks.artifacts import ArtifactsCheck
from app.checks.openapi import OpenAPICheck
from app.checks.cookies_cors import CookieFlagsCheck, CORSCheck
from app.checks.headers import (
    CSPCheck,
    XContentTypeOptionsCheck,
    FrameAncestorsOrXFOCheck,
    ReferrerPolicyCheck,
    PermissionsPolicyCheck,
    CacheControlHTMLCheck,
)

CHECKS = [
    HSTSCheck(),
    CSPCheck(),
    XContentTypeOptionsCheck(),
    FrameAncestorsOrXFOCheck(),
    ReferrerPolicyCheck(),
    PermissionsPolicyCheck(),
    CacheControlHTMLCheck(),
    CookieFlagsCheck(),
    CORSCheck(),
    OpenAPICheck(),
    ArtifactsCheck(),
]


def score_from(findings: List[Finding]) -> int:
    score = 100
    for f in findings:
        if f.status == "FAIL":
            score -= 10
        elif f.status == "WARN":
            score -= 5
    return max(score, 0)


async def run_scan(url: str) -> Scan:
    scan_id = str(uuid.uuid4())
    async with client_for() as client:
        results = await asyncio.gather(*[c.run(client, url) for c in CHECKS])
    return Scan(id=scan_id, url=url, score=score_from(results), findings=results)

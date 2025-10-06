import uuid
from typing import List, Tuple
from urllib.parse import urlsplit, urlunsplit, urljoin

from app.models.schemas import Finding

def _finding(key: str, title: str, status: str, risk: str, confidence: str,
             evidence: dict, recommendation: str) -> Finding:
    return Finding(
        id=str(uuid.uuid4()),
        key=key,
        title=title,
        status=status,          # PASS / WARN / FAIL / INFO
        risk=risk,              # low / medium / high
        confidence=confidence,  # low / medium / high
        evidence=evidence,
        recommendation=recommendation,
    )

COMMON_API_PATHS: List[str] = [
    # OpenAPI/Swagger
    "/openapi.json",
    "/openapi.yaml",
    "/openapi.yml",
    "/api/openapi.json",
    "/api/openapi.yaml",
    "/v3/api-docs",            # Springdoc
    "/v3/api-docs.yaml",
    "/swagger.json",
    "/swagger/v1/swagger.json",
    "/swagger-ui",
    "/swagger-ui.html",
    "/swagger/index.html",
    "/api-docs",
    "/api-docs.json",
    # Redoc
    "/redoc",
    "/docs",                   # FastAPI/Starlette default
    "/docs/swagger.json",      # some setups
]

def _base_origin(url: str) -> str:
    """Return scheme://host[:port]/ (no path/query/frag)"""
    parts = list(urlsplit(url))
    parts[2] = "/"   # path
    parts[3] = ""    # query
    parts[4] = ""    # fragment
    return urlunsplit(parts)

class OpenAPICheck:
    key = "openapi_discovery"
    title = "OpenAPI / Swagger Discovery"
    weight = 6

    async def run(self, client, url: str) -> Finding:
        """
        Safe discovery: HEAD first; if 200/OK or suspicious content-type,
        do a small GET and include the first ~400 chars as evidence.
        """
        base = _base_origin(url)
        hits: List[Tuple[str, int, str, str]] = []  # (path, status, content_type, snippet)
        errors: List[Tuple[str, str]] = []          # (path, error)

        for path in COMMON_API_PATHS:
            target = urljoin(base, path.lstrip("/"))
            try:
                head = await client.head(target)
                status = head.status_code
                ctype = head.headers.get("content-type", "")

                should_get = False
                if status < 400:
                    should_get = True
                elif "json" in ctype.lower() or "yaml" in ctype.lower() or "html" in ctype.lower():
                    # Some servers return non-200 on HEAD; try GET to be sure.
                    should_get = True

                snippet = ""
                if should_get:
                    # GET (non-mutating), limit to a small read
                    getr = await client.get(target, headers={"Accept": "application/json, text/yaml, text/html;q=0.9, */*;q=0.1"})
                    status = getr.status_code
                    ctype = getr.headers.get("content-type", "")
                    # take a tiny preview only
                    content = (getr.text or "")[:400]
                    snippet = content

                # Heuristic: consider a "hit" when 200 and content-type smells like docs/schema,
                # or snippet contains telltale markers.
                marker_hit = any(m in snippet.lower() for m in [
                    '"openapi"', "openapi:", '"swagger"', "swagger:", '"paths"', '"components"'
                ])
                type_hit = any(t in ctype.lower() for t in ["json", "yaml", "yml", "html"])
                if status == 200 and (marker_hit or type_hit):
                    hits.append((target, status, ctype, snippet))
            except Exception as e:
                errors.append((target, repr(e)))
                continue

        if hits:
            # If documentation is reachable unauthenticated, this is usually WARN (info leakage).
            # Raise to FAIL if /v3/api-docs or raw schemas are directly accessible.
            strongest = any(h[0].endswith(("openapi.json", "swagger.json", "v3/api-docs", "api-docs")) for h in hits)
            status = "FAIL" if strongest else "WARN"
            risk = "medium" if strongest else "low"
            evidence = {
                "discovered": [
                    {"url": u, "status": s, "content_type": ct, "snippet": snip}
                    for (u, s, ct, snip) in hits[:3]  # cap evidence items
                ],
                "note": "Showing up to 3 matches."
            }
            rec = (
                "Restrict public access to auto-generated API documentation or schemas. "
                "Serve docs only to authenticated/dev audiences; disable unauthenticated access; "
                "avoid leaking internal endpoints and models."
            )
            return _finding(self.key, self.title, status, risk, "high", evidence, rec)

        # No hits
        if errors:
            return _finding(self.key, self.title, "INFO", "low", "low",
                            {"errors_sample": errors[:2]}, "No OpenAPI/Swagger docs found; some requests errored (likely blocked).")
        return _finding(self.key, self.title, "PASS", "low", "high",
                        {"note": "No public OpenAPI/Swagger endpoints discovered."},
                        "No public API docs detected at common paths.")

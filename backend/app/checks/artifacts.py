import uuid
from typing import List, Tuple
from urllib.parse import urljoin, urlsplit, urlunsplit

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

# Small set of **safe** paths to probe. No recursion.
COMMON_ARTIFACT_PATHS: List[str] = [
    # VCS / secrets
    "/.git/HEAD",
    "/.env",
    "/.htpasswd",
    "/.DS_Store",
    # Status / admin
    "/server-status",
    "/server-info",
    # Backups / listings
    "/backup/",
    "/backups/",
    "/.well-known/security.txt",
    "/.well-known/change-password",
    # Apps / defaults (detect presence only)
    "/phpinfo.php",
    "/wp-login.php",
    "/actuator",
    "/actuator/health",
]

DIR_LISTING_MARKERS = [
    "<title>Index of /",
    "directory listing for",
    "Parent Directory",
    "Last modified",
    "Index of /",
]

PLAINTEXT_SECRET_SNIPPETS = [
    "DATABASE_URL", "AWS_SECRET", "PASSWORD=", "DB_PASSWORD", "secret", "token", "api_key",
]

def _origin_only(url: str) -> str:
    parts = list(urlsplit(url))
    parts[2] = "/"  # path
    parts[3] = ""   # query
    parts[4] = ""   # fragment
    return urlunsplit(parts)

class ArtifactsCheck:
    key = "artifacts"
    title = "Exposed Artifacts / Directory Indexing"
    weight = 8

    async def run(self, client, url: str) -> Finding:
        base = _origin_only(url)
        hits: List[Tuple[str, int, str, str, str]] = []  # (url, status, ctype, category, snippet)
        errors: List[Tuple[str, str]] = []

        for path in COMMON_ARTIFACT_PATHS:
            target = urljoin(base, path.lstrip("/"))
            try:
                head = await client.head(target)
                status = head.status_code
                ctype = head.headers.get("content-type", "")
                snippet = ""
                category = "generic"

                # Decide whether to GET a tiny body for evidence
                should_get = status < 400 or any(x in ctype.lower() for x in ["text", "json", "yaml", "html"])
                if should_get:
                    g = await client.get(
                        target,
                        headers={"Accept": "text/plain, text/html;q=0.9, application/json;q=0.8, */*;q=0.1"},
                    )
                    status = g.status_code
                    ctype = g.headers.get("content-type", ctype)
                    text = (g.text or "")[:600]  # cap snippet
                    snippet = text

                    # classify by path
                    if path.endswith("/"):
                        category = "directory"
                    elif path in ("/.git/HEAD", "/.env", "/.htpasswd", "/.DS_Store"):
                        category = "sensitive_file"
                    elif path in ("/server-status", "/server-info"):
                        category = "status_page"
                    else:
                        category = "generic"

                    # Heuristics: mark as a "hit" only when meaningful
                    is_dir_listing = any(m in text.lower() for m in [m.lower() for m in DIR_LISTING_MARKERS])
                    is_secretish   = any(s.lower() in text.lower() for s in [s.lower() for s in PLAINTEXT_SECRET_SNIPPETS])
                    looks_exposed  = (
                        (category == "sensitive_file" and status == 200 and len(text) > 0)
                        or (category == "directory"     and status == 200 and is_dir_listing)
                        or (category == "status_page"   and status == 200)
                        or (status == 200 and is_secretish)
                    )

                    if looks_exposed:
                        hits.append((target, status, ctype, category, snippet))
                # If HEAD is 403/404 and no GET evidence, skip silently
            except Exception as e:
                errors.append((target, repr(e)))

        if hits:
            # Elevate risk if we saw truly sensitive files or directory indexes
            high_risk = any(cat in ("sensitive_file", "directory") for (_, _, _, cat, _) in hits)
            status = "FAIL" if high_risk else "WARN"
            risk = "medium" if high_risk else "low"
            evidence = {
                "discovered": [
                    {"url": u, "status": s, "content_type": ct, "category": cat, "snippet": snip[:300]}
                    for (u, s, ct, cat, snip) in hits[:3]  # cap evidence items
                ],
                "note": "Showing up to 3 matches. Paths probed are static; no recursion performed."
            }
            rec = (
                "Restrict public access to sensitive files and directory indexes. "
                "Disable auto-indexing, remove backup/temporary files, and block /.git and /.env from web root. "
                "For Apache: Options -Indexes; for Nginx: disable autoindex; remove or move secrets outside document root."
            )
            return _finding(self.key, self.title, status, risk, "high", evidence, rec)

        if errors:
            return _finding(self.key, self.title, "INFO", "low", "low",
                            {"errors_sample": errors[:2]},
                            "No exposed artifacts detected at common paths; some requests errored (may be blocked).")
        return _finding(self.key, self.title, "PASS", "low", "high",
                        {"note": "No common artifacts or indexes found."},
                        "No obvious exposures at common paths. Consider deeper, authorized reviews in dev/stage.")

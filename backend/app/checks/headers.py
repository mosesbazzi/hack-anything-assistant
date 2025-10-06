import uuid
from typing import Optional
from app.models.schemas import Finding

def _finding_base(key: str, title: str, status: str, risk: str, confidence: str,
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

class CSPCheck:
    key = "csp"
    title = "Content-Security-Policy"
    weight = 8
    async def run(self, client, url: str) -> Finding:
        try:
            r = await client.get(url, headers={"Accept": "text/html, */*"})
            csp = r.headers.get("content-security-policy")
            if not csp:
                return _finding_base(self.key, self.title, "FAIL", "medium", "high",
                                     {"observed_header": "(absent)"},
                                     "Add a CSP to reduce XSS/injection. Start with strict default-src, scoped script-src/style-src (nonces/hashes).")
            header = csp.strip()
            if "default-src *" in header or "script-src *" in header:
                return _finding_base(self.key, self.title, "WARN", "low", "high",
                                     {"observed_header": header},
                                     "CSP present but uses wildcards. Replace with 'self', explicit hosts, nonces/hashes.")
            return _finding_base(self.key, self.title, "PASS", "low", "high",
                                 {"observed_header": header},
                                 "CSP present. Periodically tighten directives.")
        except Exception as e:
            return _finding_base(self.key, self.title, "INFO", "low", "low",
                                 {"error": repr(e)}, "Could not verify CSP (network/SSL error).")

class XContentTypeOptionsCheck:
    key = "x_content_type_options"
    title = "X-Content-Type-Options"
    async def run(self, client, url: str) -> Finding:
        try:
            r = await client.get(url)
            xcto = r.headers.get("x-content-type-options")
            if xcto and xcto.lower().strip() == "nosniff":
                return _finding_base(self.key, self.title, "PASS", "low", "high",
                                     {"observed_header": xcto}, "Header correctly set.")
            return _finding_base(self.key, self.title, "FAIL", "low", "high",
                                 {"observed_header": xcto or "(absent)"},
                                 "Add X-Content-Type-Options: nosniff to prevent MIME sniffing.")
        except Exception as e:
            return _finding_base(self.key, self.title, "INFO", "low", "low",
                                 {"error": repr(e)}, "Could not verify X-Content-Type-Options.")

class FrameAncestorsOrXFOCheck:
    key = "framing_protection"
    title = "Framing Protection (frame-ancestors / X-Frame-Options)"
    async def run(self, client, url: str) -> Finding:
        try:
            r = await client.get(url)
            csp = r.headers.get("content-security-policy", "")
            xfo = r.headers.get("x-frame-options")
            if "frame-ancestors" in csp.lower():
                return _finding_base(self.key, self.title, "PASS", "low", "high",
                                     {"CSP": csp}, "Framing controlled via CSP frame-ancestors.")
            if xfo:
                if xfo.lower() in ("deny", "sameorigin"):
                    return _finding_base(self.key, self.title, "PASS", "low", "high",
                                         {"X-Frame-Options": xfo}, "X-Frame-Options set appropriately.")
                return _finding_base(self.key, self.title, "WARN", "low", "high",
                                     {"X-Frame-Options": xfo},
                                     "Prefer SAMEORIGIN or DENY, or use CSP frame-ancestors.")
            return _finding_base(self.key, self.title, "FAIL", "low", "high",
                                 {"observed_headers": {"CSP": csp or "(absent)", "X-Frame-Options": xfo or "(absent)"}},
                                 "Add CSP frame-ancestors (e.g., 'none' or 'self') or X-Frame-Options: SAMEORIGIN/DENY.")
        except Exception as e:
            return _finding_base(self.key, self.title, "INFO", "low", "low",
                                 {"error": repr(e)}, "Could not verify framing protection.")

class ReferrerPolicyCheck:
    key = "referrer_policy"
    title = "Referrer-Policy"
    async def run(self, client, url: str) -> Finding:
        try:
            r = await client.get(url)
            rp = r.headers.get("referrer-policy")
            if not rp:
                return _finding_base(self.key, self.title, "FAIL", "low", "high",
                                     {"observed_header": "(absent)"},
                                     "Add Referrer-Policy (e.g., 'strict-origin-when-cross-origin') to reduce referrer leakage.")
            val = rp.lower().strip()
            good = {"no-referrer", "strict-origin", "strict-origin-when-cross-origin", "same-origin"}
            if val in good:
                return _finding_base(self.key, self.title, "PASS", "low", "high",
                                     {"observed_header": rp}, "Good Referrer-Policy.")
            return _finding_base(self.key, self.title, "WARN", "low", "high",
                                 {"observed_header": rp},
                                 "Consider 'strict-origin-when-cross-origin' for stronger privacy.")
        except Exception as e:
            return _finding_base(self.key, self.title, "INFO", "low", "low",
                                 {"error": repr(e)}, "Could not verify Referrer-Policy.")

class PermissionsPolicyCheck:
    key = "permissions_policy"
    title = "Permissions-Policy"
    async def run(self, client, url: str) -> Finding:
        try:
            r = await client.get(url)
            pp = r.headers.get("permissions-policy") or r.headers.get("feature-policy")
            if not pp:
                return _finding_base(self.key, self.title, "WARN", "low", "medium",
                                     {"observed_header": "(absent)"},
                                     "Add Permissions-Policy to restrict powerful features (camera, mic, geolocation).")
            return _finding_base(self.key, self.title, "PASS", "low", "high",
                                 {"observed_header": pp}, "Permissions-Policy present. Review directives for least privilege.")
        except Exception as e:
            return _finding_base(self.key, self.title, "INFO", "low", "low",
                                 {"error": repr(e)}, "Could not verify Permissions-Policy.")

class CacheControlHTMLCheck:
    key = "cache_control_html"
    title = "Cache-Control for HTML"
    async def run(self, client, url: str) -> Finding:
        try:
            r = await client.get(url, headers={"Accept": "text/html, */*"})
            ct = r.headers.get("content-type", "")
            if "text/html" not in ct.lower():
                return _finding_base(self.key, self.title, "INFO", "low", "high",
                                     {"content_type": ct}, "Non-HTML response; skipping HTML cache checks.")
            cc = r.headers.get("cache-control")
            if not cc:
                return _finding_base(self.key, self.title, "WARN", "low", "high",
                                     {"observed_header": "(absent)"},
                                     "Set Cache-Control for HTML (e.g., 'no-store' for auth pages or 'private, max-age=...' for user pages).")
            if "no-store" in cc.lower() or "private" in cc.lower():
                return _finding_base(self.key, self.title, "PASS", "low", "high",
                                     {"observed_header": cc}, "Cache-Control looks appropriate for HTML.")
            return _finding_base(self.key, self.title, "WARN", "low", "high",
                                 {"observed_header": cc},
                                 "Review Cache-Control; avoid long public caching for HTML containing user content.")
        except Exception as e:
            return _finding_base(self.key, self.title, "INFO", "low", "low",
                                 {"error": repr(e)}, "Could not verify Cache-Control.")

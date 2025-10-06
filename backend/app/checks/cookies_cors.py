import uuid
from typing import List, Tuple
from http.cookies import SimpleCookie
from app.models.schemas import Finding

def _finding_base(key: str, title: str, status: str, risk: str, confidence: str,
                  evidence: dict, recommendation: str) -> Finding:
    return Finding(
        id=str(uuid.uuid4()),
        key=key,
        title=title,
        status=status,          # PASS/WARN/FAIL/INFO
        risk=risk,              # low/medium/high
        confidence=confidence,  # low/medium/high
        evidence=evidence,
        recommendation=recommendation,
    )

# ---------- Cookie Flags ----------
class CookieFlagsCheck:
    key = "cookie_flags"
    title = "Cookie Security Flags (Secure / HttpOnly / SameSite)"

    @staticmethod
    def _parse_set_cookie_headers(values: List[str]) -> List[Tuple[str, dict]]:
        """
        Returns list of (cookie_name, attrs_dict_lowercased)
        """
        parsed = []
        for raw in values:
            try:
                c = SimpleCookie()
                c.load(raw)
                # SimpleCookie only parses the first k=v; attributes on morsel
                for name, morsel in c.items():
                    attrs = { "value": morsel.value }
                    # collect flags from raw string as SimpleCookie loses casing on attrs
                    lower = raw.lower()
                    attrs["secure"] = "secure" in lower
                    attrs["httponly"] = "httponly" in lower
                    # SameSite= (case-insensitive)
                    samesite = None
                    for token in raw.split(";"):
                        token = token.strip()
                        if token.lower().startswith("samesite="):
                            samesite = token.split("=",1)[1].strip()
                            break
                    attrs["samesite"] = samesite
                    parsed.append((name, attrs))
            except Exception:
                # If parsing fails, still include the raw header once
                parsed.append(("(unparsed)", {"raw": raw}))
        return parsed

    async def run(self, client, url: str) -> Finding:
        try:
            r = await client.get(url)  # unauthenticated request
            set_cookie_values = r.headers.get_list("set-cookie") if hasattr(r.headers, "get_list") else r.headers.get_all("set-cookie", [])
            if not set_cookie_values:
                return _finding_base(self.key, self.title, "INFO", "low", "high",
                                     {"note": "No Set-Cookie observed on unauthenticated request."},
                                     "No session cookies were set. Re-test after login flows or authenticated pages in future versions.")

            cookies = self._parse_set_cookie_headers(set_cookie_values)
            fails = []
            warns = []
            details = {}
            for name, attrs in cookies:
                details[name] = attrs
                # Only judge likely session cookies (heuristic)
                looks_session = any(k in name.lower() for k in ["sess", "auth", "token", "sid"])
                if not looks_session:
                    # You can still encourage flags on all cookies, but weigh less
                    if not attrs.get("secure"):
                        warns.append(f"{name}: missing Secure")
                    if not attrs.get("httponly"):
                        warns.append(f"{name}: missing HttpOnly")
                    if attrs.get("samesite") is None:
                        warns.append(f"{name}: missing SameSite")
                    continue

                if not attrs.get("secure"):
                    fails.append(f"{name}: missing Secure")
                if not attrs.get("httponly"):
                    fails.append(f"{name}: missing HttpOnly")
                ss = attrs.get("samesite")
                if ss is None:
                    warns.append(f"{name}: missing SameSite")
                elif ss.lower() == "none" and not attrs.get("secure"):
                    fails.append(f"{name}: SameSite=None without Secure")

            if fails:
                return _finding_base(self.key, self.title, "FAIL", "medium", "high",
                                     {"cookies": details, "issues": fails + warns},
                                     "Set session cookies with Secure and HttpOnly; include SameSite (Lax/Strict). "
                                     "If SameSite=None is required for cross-site usage, Secure is mandatory.")
            if warns:
                return _finding_base(self.key, self.title, "WARN", "low", "high",
                                     {"cookies": details, "issues": warns},
                                     "Harden cookies: add Secure, HttpOnly, and an appropriate SameSite value.")
            return _finding_base(self.key, self.title, "PASS", "low", "high",
                                 {"cookies": details}, "Cookie flags look appropriate.")
        except Exception as e:
            return _finding_base(self.key, self.title, "INFO", "low", "low",
                                 {"error": repr(e)}, "Could not verify cookie flags due to a network/SSL error.")

# ---------- CORS ----------
class CORSCheck:
    key = "cors"
    title = "CORS Configuration (Access-Control-Allow-*)"

    async def run(self, client, url: str) -> Finding:
        """
        Passive CORS sanity based on response headers.
        We flag the risky combination: ACAO='*' with ACAC=true,
        and generally warn on wildcard origins.
        """
        try:
            r = await client.get(url)
            hdrs = {k.lower(): v for k, v in r.headers.items()}
            acao = hdrs.get("access-control-allow-origin")
            acac = hdrs.get("access-control-allow-credentials")
            vary = hdrs.get("vary")

            # No CORS headers at all -> INFO (not necessarily a problem)
            if not acao and not acac:
                return _finding_base(self.key, self.title, "INFO", "low", "high",
                                     {"observed_headers": {"access-control-allow-origin": acao, "access-control-allow-credentials": acac, "vary": vary}},
                                     "No CORS headers observed on this route. That’s fine unless the endpoint is intended for cross-site AJAX.")
            # Bad combo: wildcard origin + credentials
            if (acao == "*") and (acac and acac.lower() == "true"):
                return _finding_base(self.key, self.title, "FAIL", "medium", "high",
                                     {"observed_headers": {"access-control-allow-origin": acao, "access-control-allow-credentials": acac, "vary": vary}},
                                     "Risky CORS: Access-Control-Allow-Origin: * with credentials allowed. Set a specific origin and ensure Vary: Origin is present.")
            # Warn on wildcard origin generally
            if acao == "*":
                return _finding_base(self.key, self.title, "WARN", "low", "high",
                                     {"observed_headers": {"access-control-allow-origin": acao, "access-control-allow-credentials": acac, "vary": vary}},
                                     "CORS allows any origin. Prefer a specific allowlist; add Vary: Origin when origin reflection is used.")
            # If credentials are true but origin is not specific (e.g., null or missing)
            if acac and acac.lower() == "true" and (not acao or acao in ("null", "")):
                return _finding_base(self.key, self.title, "WARN", "low", "high",
                                     {"observed_headers": {"access-control-allow-origin": acao, "access-control-allow-credentials": acac, "vary": vary}},
                                     "Credentials allowed but Access-Control-Allow-Origin is missing/unsafe. Use an explicit origin and Vary: Origin.")
            # Looks okay
            return _finding_base(self.key, self.title, "PASS", "low", "high",
                                 {"observed_headers": {"access-control-allow-origin": acao, "access-control-allow-credentials": acac, "vary": vary}},
                                 "CORS on this route looks reasonable. Validate preflight/other routes in deeper scans.")
        except Exception as e:
            return _finding_base(self.key, self.title, "INFO", "low", "low",
                                 {"error": repr(e)}, "Could not verify CORS due to a network/SSL error.")

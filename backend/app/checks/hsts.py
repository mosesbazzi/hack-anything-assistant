import uuid
from urllib.parse import urlsplit
from app.models.schemas import Finding

class HSTSCheck:
    key = "hsts"
    title = "HTTP Strict-Transport-Security (HSTS)"
    weight = 8

    def _finding(self, status, risk, confidence, evidence, recommendation) -> Finding:
        return Finding(
            id=str(uuid.uuid4()),
            key=self.key,
            title=self.title,
            status=status,
            risk=risk,
            confidence=confidence,
            evidence=evidence,
            recommendation=recommendation,
        )

    async def run(self, client, url: str) -> Finding:
        scheme = urlsplit(url).scheme.lower()
        if scheme != "https":
            return self._finding(
                "WARN", "medium", "high",
                {"note": "Requested over HTTP; HSTS applies to HTTPS sites."},
                "Serve the site over HTTPS and enable HSTS with a sufficient max-age. "
                "Recommended: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload",
            )

        try:
            resp = await client.get(url, headers={"Accept": "text/html, */*"})
            hsts = resp.headers.get("strict-transport-security")
            if not hsts:
                return self._finding(
                    "FAIL", "medium", "high",
                    {"request_url": str(resp.url), "status_code": str(resp.status_code), "observed_header": "(absent)"},
                    "Add HSTS. Example:\nStrict-Transport-Security: max-age=31536000; includeSubDomains; preload",
                )

            header = hsts.strip()
            evidence = {"observed_header": header}

            # parse max-age
            max_age = 0
            for part in header.split(";"):
                p = part.strip().lower()
                if p.startswith("max-age="):
                    try:
                        max_age = int(p.split("=", 1)[1])
                    except Exception:
                        pass

            if max_age < 15552000:  # < 180d
                return self._finding(
                    "WARN", "low", "high", evidence,
                    "Increase HSTS max-age to at least 15552000 (180d), ideally 31536000 (1y); add includeSubDomains and consider preload."
                )

            has_sub = "includesubdomains" in header.lower()
            has_preload = "preload" in header.lower()
            if has_sub and has_preload:
                return self._finding(
                    "PASS", "low", "high", evidence,
                    "HSTS is properly configured with long max-age, includeSubDomains, and preload."
                )
            else:
                return self._finding(
                    "PASS", "low", "high", evidence,
                    "HSTS present with sufficient max-age. Consider includeSubDomains and preload (if eligible)."
                )
        except Exception as e:
            return self._finding(
                "INFO", "low", "low",
                {"error": repr(e)},
                "Could not verify HSTS due to a network/SSL error. Re-run later or check connectivity.",
            )

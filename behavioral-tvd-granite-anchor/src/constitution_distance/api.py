"""Small HTTPS client; no API key is persisted or included in errors."""
import json
import hashlib
from datetime import datetime, timezone
import random
import time
import urllib.error
import urllib.request


class APIError(RuntimeError):
    def __init__(self, status=None, retryable=False, retry_after=0):
        super().__init__(f"HTTP {status}" if status else "Network failure (billing outcome unknown)")
        self.status, self.retryable, self.retry_after = status, retryable, retry_after


class API:
    def __init__(self, base_url, key=None, timeout=120, attempts=5):
        if not base_url.startswith("https://"):
            raise ValueError("HTTPS is required")
        self.base_url = base_url.rstrip("/")
        self.key, self.timeout, self.attempts = key, timeout, attempts

    def request(self, path, payload=None):
        headers = {"Accept": "application/json", "User-Agent": "constitution-distance/0.1"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        if payload is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base_url + path, headers=headers,
            data=None if payload is None else json.dumps(payload).encode())
        for attempt in range(self.attempts):
            try:
                started=datetime.now(timezone.utc)
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    result = json.load(response)
                    result["_http_status"] = response.status
                    allowed={'date','server','cf-ray','x-request-id','x-openrouter-request-id','x-openrouter-generation-id'}
                    result['_http_headers']={k.lower():v for k,v in response.headers.items() if k.lower() in allowed}
                    result['_transport']={'started_at':started.isoformat(),
                        'finished_at':datetime.now(timezone.utc).isoformat(),
                        'request_body_sha256':hashlib.sha256(request.data).hexdigest() if request.data is not None else None}
                    return result
            except urllib.error.HTTPError as exc:
                retryable = exc.code in (429, 500, 502, 503, 504)
                if not retryable or attempt + 1 == self.attempts:
                    try:
                        retry_after = min(30, max(0, float(exc.headers.get("Retry-After", "0"))))
                    except ValueError:
                        retry_after = 0
                    raise APIError(exc.code, retryable, retry_after) from None
                try:
                    delay = min(60, max(0, float(exc.headers.get("Retry-After", "0"))))
                except ValueError:
                    delay = 0
            except (urllib.error.URLError, TimeoutError):
                if attempt + 1 == self.attempts:
                    raise APIError(retryable=True) from None
                delay = 0
            time.sleep(max(delay, min(30, 2 ** attempt) + random.random()))
        raise RuntimeError("Request attempts exhausted")

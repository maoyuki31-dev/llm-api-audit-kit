"""Dependency-free client for an explicitly configured Chat Completions endpoint."""
import json
import math
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class ChatClient:
    def __init__(self, url, api_key, model, timeout=60):
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("API_URL must be a complete HTTP(S) Chat Completions URL")
        if not api_key or not model:
            raise ValueError("API_KEY and MODEL must be configured")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("TIMEOUT must be a positive finite number")
        self.url, self.api_key, self.model, self.timeout = url, api_key, model, timeout

    @classmethod
    def from_env(cls, prefix="LLM_"):
        names = [prefix + suffix for suffix in ("API_URL", "API_KEY", "MODEL")]
        if any(not os.environ.get(name) for name in names):
            raise ValueError("Set environment variables: " + ", ".join(names))
        return cls(*(os.environ[name] for name in names),
                   timeout=float(os.environ.get(prefix + "TIMEOUT", "60")))

    def complete(self, prompt, *, system=None, logprobs=False):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages,
                   "temperature": 0, "max_tokens": 2048}
        if logprobs:
            payload["logprobs"] = True
        request = Request(self.url, data=json.dumps(payload).encode("utf-8"),
                          headers={"Authorization": "Bearer " + self.api_key,
                                   "Content-Type": "application/json"}, method="POST")
        start = time.monotonic()
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.load(response)
        except HTTPError as exc:
            raise RuntimeError(f"API HTTP error {exc.code}") from None
        except (URLError, TimeoutError, OSError):
            raise RuntimeError("API connection failed or timed out") from None
        except (ValueError, UnicodeError):
            raise RuntimeError("API response is not valid JSON") from None
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError()
            finish = choice.get("finish_reason")
            if finish in {"length", "content_filter"}:
                raise RuntimeError("API response was truncated or filtered")
            usage = data.get("usage") or {}
            total = usage.get("total_tokens")
            if total is not None and (type(total) is not int or total < 0):
                raise ValueError()
            token_info = (choice.get("logprobs") or {}).get("content") or []
            first_token = token_info[0].get("token") if token_info else None
        except (KeyError, IndexError, TypeError, AttributeError, ValueError):
            raise RuntimeError("API response has an unsupported schema or empty answer") from None
        return {"content": content, "first_token": first_token, "usage": usage,
                "total_tokens": total, "finish_reason": finish,
                "latency_ms": round((time.monotonic() - start) * 1000)}

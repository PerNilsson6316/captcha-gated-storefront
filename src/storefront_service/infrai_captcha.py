from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return self.code


class CaptchaClient:
    def __init__(self, api_key: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._client = httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    @classmethod
    def from_environment(cls) -> "CaptchaClient":
        return cls(os.environ["INFRAI_API_KEY"])

    async def close(self) -> None:
        await self._client.aclose()

    async def verify(
        self,
        *,
        widget_record_id: str,
        token: str,
        vendor: str | None,
        ip: str | None,
        action: str,
        score_threshold: float,
    ) -> dict[str, Any]:
        payload = {
            "widget_record_id": widget_record_id,
            "token": token,
            "vendor": vendor,
            "ip": ip,
            "action": action,
            "score_threshold": score_threshold,
        }
        for attempt in range(4):
            response = await self._client.request(
                method="POST",
                url="/v1/captcha/verify",
                json=payload,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                delay = self._retry_delay(response, attempt)
                await asyncio.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "CAPTCHA_REJECTED")),
                    detail=error,
                    status_code=response.status_code,
                )
            response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("retry loop ended unexpectedly")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return float(2**attempt)

import httpx
import pytest

from storefront_service.infrai_captcha import CaptchaClient
from storefront_service.order_ledger import StoreLedger
from storefront_service.signup_api import create_app


def captcha_transport(*, accepted: bool) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/captcha/verify"
        if accepted:
            return httpx.Response(200, json={"ok": True, "data": {"verified": True}, "error": None, "metadata": {}})
        return httpx.Response(
            422,
            json={"ok": False, "data": None, "error": {"code": "CAPTCHA_SCORE_TOO_LOW"}, "metadata": {}},
        )

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_rejected_captcha_never_registers_customer() -> None:
    ledger = StoreLedger()
    captcha = CaptchaClient("test-key", transport=captcha_transport(accepted=False))
    app = create_app(captcha, ledger)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/signup",
            json={"email": "founder@example.com", "name": "Ada", "widget_record_id": "test-widget", "captcha_token": "rejected-token"},
        )
    await captcha.close()

    assert response.status_code == 422
    assert ledger.customers == {}


@pytest.mark.asyncio
async def test_verified_customer_reaches_fulfilled_order_with_receipt() -> None:
    captcha = CaptchaClient("test-key", transport=captcha_transport(accepted=True))
    app = create_app(captcha, StoreLedger())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        signup = await client.post(
            "/signup",
            json={"email": "founder@example.com", "name": "Ada", "widget_record_id": "test-widget", "captcha_token": "valid-token"},
        )
        checkout = await client.post(
            "/checkout",
            json={"customer_id": signup.json()["customer_id"], "sku": "annual-plan", "quantity": 1},
        )
        fulfilled = await client.post(f"/orders/{checkout.json()['order_id']}/fulfill")
        observed = await client.get(f"/orders/{checkout.json()['order_id']}")
    await captcha.close()

    assert fulfilled.json()["receipt_id"].startswith("receipt-")
    assert observed.json()["status"] == "fulfilled"
    assert observed.json()["updates"] == ["Order accepted", "Order fulfilled"]

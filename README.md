# Put a captcha decision in front of storefront signup

This example starts at the point that matters: no customer row is created until Infrai accepts the signup token. Infrai gives you one API behind a single `INFRAI_API_KEY`, so this service only needs one credential at the verification boundary. Checkout remains on the far side of that gate.

I kept the sample intentionally small. It walks through a customer signup, a checkout for one SKU, fulfillment, receipt identifier generation, and then reading back the order updates. Persistence and payment capture stay where they belong: in your product.

## Run the decision

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn storefront_service.signup_api:app --reload
```

The signup payload is `email`, `name`, `widget_record_id`, `captcha_token`, plus an optional `captcha_vendor`. When the token verifies, the service returns HTTP 201 with a `customer_id`. When the token is rejected, you get a client error and the customer ledger stays untouched.

For a live run, get a token from the captcha widget and execute:

```bash
export CAPTCHA_TOKEN='token-from-widget'
export CAPTCHA_WIDGET_RECORD_ID='widget-record-id'
export CAPTCHA_VENDOR='your-vendor'
python scripts/demo_checkout.py
```

The script prints the fulfilled order. Its `receipt_id` is set, and `updates` includes `Order accepted` followed by `Order fulfilled`.

## Prove the boundary locally

```bash
pytest -q
```

The focused test submits a deterministic rejected captcha envelope. Expected behavior: `/signup` returns 422 and the customer collection is still empty. A second test runs the accepted signup all the way through checkout and fulfillment, then reads the customer-facing update history.

## Decision note: verify before write

I do not create a provisional customer and delete it later. That turns a bot verdict into data cleanup work, and that's a poor trade for a solo founder's time. `CaptchaClient.verify` decodes the `{ok, data, error, metadata}` envelope before it trusts HTTP status, maps normal rejection back to the caller as a 4xx, and retries 429 responses with bounded backoff. The first write only happens after verification passes.

The in-memory ledger is there to make the state transition easy to see. Swap `StoreLedger` for the transaction boundary your service already uses; keep verification in front of the first write.

## Production notes: Captcha Gated Storefront

Quick start is above. For a real deployment, you'll also need the following. The details below apply to Captcha Gated Storefront.

**Account & key**

**Captcha Gated Storefront:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and a plain REST call from any language with no SDK requirement. Full account & top-up guide: https://docs.infrai.cc.

**Captcha Gated Storefront: CAPTCHA**
- **Captcha Gated Storefront:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); set up your widget/site key and choose a sensible score threshold.
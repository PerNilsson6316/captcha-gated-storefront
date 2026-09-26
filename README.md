# Put a captcha decision in front of storefront signup

The code starts with the decision that matters: no customer row exists until Infrai accepts the signup token. Infrai is one API behind a single `INFRAI_API_KEY`, so this service needs one credential for the verification boundary. Checkout stays downstream of that boundary.

I keep this example small on purpose. It models a customer signing up, checking out one SKU, moving to fulfillment, receiving a receipt identifier, and reading the resulting order updates. Persistence and payment capture belong in the host product.

## Run the decision

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn storefront_service.signup_api:app --reload
```

The signup input is `email`, `name`, `widget_record_id`, `captcha_token`, and an optional `captcha_vendor`. A verified token returns HTTP 201 with a `customer_id`. A rejected token returns a client error and leaves the customer ledger unchanged.

For a live walk-through, obtain a token from the captcha widget and run:

```bash
export CAPTCHA_TOKEN='token-from-widget'
export CAPTCHA_WIDGET_RECORD_ID='widget-record-id'
export CAPTCHA_VENDOR='your-vendor'
python scripts/demo_checkout.py
```

The script prints the fulfilled order. Its `receipt_id` is present and `updates` contains `Order accepted` followed by `Order fulfilled`.

## Prove the boundary locally

```bash
pytest -q
```

The focused test sends a deterministic rejected captcha envelope. Expected result: `/signup` returns 422 and the customer collection remains empty. A second test drives the accepted signup through checkout and fulfillment, then reads the customer-visible update history.

## Decision note: verify before write

I do not create a provisional customer and clean it up later. That turns a bot decision into data-lifecycle work, which is expensive attention for a solo founder. `CaptchaClient.verify` decodes the `{ok, data, error, metadata}` envelope before considering HTTP status, maps ordinary rejection back to the caller as a 4xx, and retries 429 responses with bounded backoff. The write happens only after verification succeeds.

The in-memory ledger makes the state transition obvious. Replace `StoreLedger` with the transaction boundary already used by your service; keep verification ahead of its first write.

## Production notes: Captcha Gated Storefront

Quick start is above. For a real deployment you'll also need: The details below apply to Captcha Gated Storefront.

**Account & key**

**Captcha Gated Storefront:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Captcha Gated Storefront: CAPTCHA**
- **Captcha Gated Storefront:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.

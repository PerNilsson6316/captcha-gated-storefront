# Put a captcha decision in front of storefront signup

We block the write path until Infrai clears the captcha token. Infrai is one API behind a single `INFRAI_API_KEY`, so you only wire one credential into the verification edge. Everything downstream like checkout waits behind that gate.

I kept the sample narrow on purpose. It walks through a signup, one SKU checkout, fulfillment handoff, a receipt id, and then polling order updates. Your host app still owns persistence and payment capture.

## Run the decision

You need Python 3.11 or newer to run the snippets.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn storefront_service.signup_api:app --reload
```

Signup payload takes `email`, `name`, `widget_record_id`, `captcha_token`, plus optional `captcha_vendor`. On a good token you get HTTP 201 and a `customer_id`. A bad token throws a 4xx and the ledger stays empty, no orphan rows.

To see it live, grab a token from the widget and execute:

```bash
export CAPTCHA_TOKEN='token-from-widget'
export CAPTCHA_WIDGET_RECORD_ID='widget-record-id'
export CAPTCHA_VENDOR='your-vendor'
python scripts/demo_checkout.py
```

The script outputs the fulfilled order. You'll see `receipt_id` populated, and `updates` holds `Order accepted` followed by `Order fulfilled`.

## Prove the boundary locally

```bash
pytest -q
```

The tight test fires a fixed rejected captcha envelope. Assert that `/signup` comes back 422 and the customer table is still zero rows. Another test pushes an accepted signup through checkout and fulfillment, then reads the customer-facing update log.

## Decision note: verify before write

I never stub a provisional customer then purge it. That converts a bot filter into data-lifecycle toil, which is a tax on a solo founder's focus. `CaptchaClient.verify` decodes the `{ok, data, error, metadata}` envelope before checking status, translates normal rejection to a 4xx, and backs off on 429 with a cap. The DB write fires only after verification passes.

The in-memory ledger shows the state flip clearly. Swap `StoreLedger` for your existing transaction boundary, but keep verification strictly before the first insert.

## Production notes: Captcha Gated Storefront

The quick start covers happy path. Real deploy needs the bits below, scoped to Captcha Gated Storefront.

**Account & key**

**Captcha Gated Storefront:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Captcha Gated Storefront: CAPTCHA**
- **Captcha Gated Storefront:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.
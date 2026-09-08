import json
import os

import httpx


def main() -> None:
    base_url = os.environ.get("STOREFRONT_URL", "http://127.0.0.1:8000")
    with httpx.Client(base_url=base_url) as client:
        signup = client.request(
            method="POST",
            url="/signup",
            json={
                "email": "founder@example.com",
                "name": "Ada",
                "widget_record_id": os.environ["CAPTCHA_WIDGET_RECORD_ID"],
                "captcha_token": os.environ["CAPTCHA_TOKEN"],
                "captcha_vendor": os.environ.get("CAPTCHA_VENDOR"),
            },
        )
        signup.raise_for_status()
        checkout = client.request(
            method="POST",
            url="/checkout",
            json={"customer_id": signup.json()["customer_id"], "sku": "annual-plan", "quantity": 1},
        )
        checkout.raise_for_status()
        fulfilled = client.request(method="POST", url=f"/orders/{checkout.json()['order_id']}/fulfill")
        fulfilled.raise_for_status()
        print(json.dumps(fulfilled.json(), indent=2))


if __name__ == "__main__":
    main()
